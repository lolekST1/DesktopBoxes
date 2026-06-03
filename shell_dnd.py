"""Obsługa przeciągania elementów z powłoki Windows (menu Start, w tym aplikacje UWP).

Eksplorator przy przeciąganiu z menu Start przekazuje albo zwykłe ścieżki plików
(klasyczne aplikacje – skróty .lnk), albo binarny format „Shell IDList Array"
zawierający PIDL-e (m.in. dla aplikacji ze Sklepu/UWP, które nie mają ścieżki na
dysku, tylko AppUserModelID). Ten moduł rozkodowuje oba przypadki i potrafi pobrać
ikonę dla elementu powłoki (np. shell:AppsFolder\\<AUMID>).
"""
import os
import struct
import ctypes
from ctypes import wintypes

from PySide6.QtGui import QIcon, QImage, QPixmap

# Format MIME, pod którym Qt udostępnia windowsowy „Shell IDList Array" (CFSTR_SHELLIDLIST).
SHELL_IDLIST_FMT = 'application/x-qt-windows-mime;value="Shell IDList Array"'

HAVE_SHELL = False
try:
    shell32 = ctypes.windll.shell32
    ole32 = ctypes.windll.ole32
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    HAVE_SHELL = True
except Exception:  # pragma: no cover - tylko Windows
    shell32 = ole32 = user32 = gdi32 = None

# Wartości SIGDN (sposób zapisu nazwy elementu powłoki)
SIGDN_NORMALDISPLAY = 0x00000000
SIGDN_PARENTRELATIVEPARSING = 0x80018001
SIGDN_DESKTOPABSOLUTEPARSING = 0x80028000
SIGDN_FILESYSPATH = 0x80058007

SHGFI_ICON = 0x00000100
SHGFI_LARGEICON = 0x00000000
SHGFI_PIDL = 0x00000008
DI_NORMAL = 0x0003


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [
        ("hIcon", ctypes.c_void_p),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName", wintypes.WCHAR * 80),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
        ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def _setup_signatures():
    shell32.ILCombine.restype = ctypes.c_void_p
    shell32.ILCombine.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    shell32.ILFree.restype = None
    shell32.ILFree.argtypes = [ctypes.c_void_p]
    shell32.SHGetNameFromIDList.restype = ctypes.c_long
    shell32.SHGetNameFromIDList.argtypes = [
        ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(wintypes.LPWSTR)]
    shell32.SHParseDisplayName.restype = ctypes.c_long
    shell32.SHParseDisplayName.argtypes = [
        wintypes.LPCWSTR, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p), wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG)]
    shell32.SHGetFileInfoW.restype = ctypes.c_void_p
    shell32.SHGetFileInfoW.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(SHFILEINFOW),
        wintypes.UINT, wintypes.UINT]
    ole32.CoTaskMemFree.restype = None
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    for fn, res, args in [
        (user32.GetDC, ctypes.c_void_p, [ctypes.c_void_p]),
        (user32.ReleaseDC, ctypes.c_int, [ctypes.c_void_p, ctypes.c_void_p]),
        (user32.DestroyIcon, ctypes.c_int, [ctypes.c_void_p]),
        (gdi32.CreateCompatibleDC, ctypes.c_void_p, [ctypes.c_void_p]),
        (gdi32.SelectObject, ctypes.c_void_p, [ctypes.c_void_p, ctypes.c_void_p]),
        (gdi32.DeleteObject, ctypes.c_int, [ctypes.c_void_p]),
        (gdi32.DeleteDC, ctypes.c_int, [ctypes.c_void_p]),
    ]:
        fn.restype = res
        fn.argtypes = args
    user32.DrawIconEx.restype = ctypes.c_int
    user32.DrawIconEx.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p,
        ctypes.c_int, ctypes.c_int, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
    gdi32.CreateDIBSection.restype = ctypes.c_void_p
    gdi32.CreateDIBSection.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, wintypes.DWORD]


if HAVE_SHELL:
    try:
        _setup_signatures()
    except Exception:
        HAVE_SHELL = False


# ---- nazwy elementów powłoki --------------------------------------------
def _name_of(pidl, sigdn):
    ptr = wintypes.LPWSTR()
    hr = shell32.SHGetNameFromIDList(pidl, sigdn, ctypes.byref(ptr))
    if hr != 0 or not ptr.value:
        return None
    val = ptr.value
    ole32.CoTaskMemFree(ctypes.cast(ptr, ctypes.c_void_p))
    return val


def _entry_for_pidl(pidl) -> dict | None:
    """Zamienia pełny PIDL na wpis {name, path}.

    Element z systemu plików (skrót, plik, folder) → ścieżka na dysku.
    Aplikacja z AppsFolder (UWP/Sklep, bez ścieżki) → shell:AppsFolder\\<AUMID>.

    Pełną ścieżkę daje SIGDN_DESKTOPABSOLUTEPARSING (SIGDN_FILESYSPATH potrafi
    zwrócić samą nazwę pliku). Jeśli ta ścieżka istnieje na dysku → plik;
    w przeciwnym razie traktujemy element jako aplikację identyfikowaną AUMID.
    """
    abs_parse = _name_of(pidl, SIGDN_DESKTOPABSOLUTEPARSING)
    if abs_parse and os.path.exists(abs_parse):
        return {"name": _file_label(abs_parse), "path": os.path.normpath(abs_parse)}
    aumid = _name_of(pidl, SIGDN_PARENTRELATIVEPARSING)
    if aumid:
        disp = _name_of(pidl, SIGDN_NORMALDISPLAY)
        return {"name": disp or aumid, "path": "shell:AppsFolder\\" + aumid}
    fs = _name_of(pidl, SIGDN_FILESYSPATH)
    if fs and os.path.exists(fs):
        return {"name": _file_label(fs), "path": os.path.normpath(fs)}
    return None


def _parse_shell_idlist(data: bytes) -> list:
    """Rozkodowuje strukturę CIDA (Shell IDList Array) na listę wpisów."""
    if len(data) < 8:
        return []
    cidl = struct.unpack_from("<I", data, 0)[0]
    if cidl == 0 or len(data) < 4 * (cidl + 2):
        return []
    offsets = struct.unpack_from("<%dI" % (cidl + 1), data, 4)
    buf = ctypes.create_string_buffer(data, len(data))
    base = ctypes.cast(buf, ctypes.c_void_p).value
    parent = base + offsets[0]
    out = []
    for i in range(1, cidl + 1):
        child = base + offsets[i]
        full = shell32.ILCombine(parent, child)
        if not full:
            continue
        try:
            entry = _entry_for_pidl(full)
            if entry:
                out.append(entry)
        finally:
            shell32.ILFree(full)
    return out


def _file_label(path: str) -> str:
    base = os.path.basename(path.rstrip("/\\")) or path
    stem, ext = os.path.splitext(base)
    if ext.lower() in (".lnk", ".url", ".exe"):
        return stem
    return base


def resolve_drop(mime) -> list:
    """Zwraca listę wpisów {name, path} z danych przeciągania (pliki + powłoka)."""
    entries = []
    for url in mime.urls():
        local = url.toLocalFile()
        if local:
            entries.append({"name": _file_label(local), "path": os.path.normpath(local)})
        elif url.toString():
            s = url.toString()
            entries.append({"name": s, "path": s})
    if entries:
        return entries
    if HAVE_SHELL and mime.hasFormat(SHELL_IDLIST_FMT):
        try:
            data = bytes(mime.data(SHELL_IDLIST_FMT))
            entries = _parse_shell_idlist(data)
        except Exception:
            entries = []
    return entries


# ---- ikony dla elementów powłoki ----------------------------------------
def _hicon_to_pixmap(hicon, size: int):
    hdc_screen = user32.GetDC(None)
    hdc = gdi32.CreateCompatibleDC(hdc_screen)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = size
    bmi.bmiHeader.biHeight = -size  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0  # BI_RGB
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    pm = None
    try:
        if not hbmp or not bits.value:
            return None
        old = gdi32.SelectObject(hdc, hbmp)
        user32.DrawIconEx(hdc, 0, 0, hicon, size, size, 0, None, DI_NORMAL)
        n = size * size * 4
        raw = bytearray((ctypes.c_ubyte * n).from_address(bits.value))
        if not any(raw[3::4]):  # ikona bez kanału alfa – odtwórz z maski
            for i in range(0, n, 4):
                if raw[i] or raw[i + 1] or raw[i + 2]:
                    raw[i + 3] = 255
        img = QImage(bytes(raw), size, size, QImage.Format_ARGB32).copy()
        pm = QPixmap.fromImage(img)
        gdi32.SelectObject(hdc, old)
    finally:
        if hbmp:
            gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc)
        user32.ReleaseDC(None, hdc_screen)
    return pm


def shell_icon(parsing_name: str, size: int = 64) -> QIcon | None:
    """Pobiera ikonę dla elementu powłoki podanego nazwą parsowalną
    (np. 'shell:AppsFolder\\<AUMID>'). Zwraca None, gdy się nie uda."""
    if not HAVE_SHELL or not parsing_name:
        return None
    pidl = ctypes.c_void_p()
    sfgao = wintypes.ULONG(0)
    hr = shell32.SHParseDisplayName(parsing_name, None, ctypes.byref(pidl), 0,
                                    ctypes.byref(sfgao))
    if hr != 0 or not pidl.value:
        return None
    sfi = SHFILEINFOW()
    try:
        res = shell32.SHGetFileInfoW(pidl, 0, ctypes.byref(sfi),
                                     ctypes.sizeof(sfi),
                                     SHGFI_PIDL | SHGFI_ICON | SHGFI_LARGEICON)
        if not res or not sfi.hIcon:
            return None
        pm = _hicon_to_pixmap(sfi.hIcon, size)
        user32.DestroyIcon(sfi.hIcon)
        return QIcon(pm) if pm and not pm.isNull() else None
    finally:
        ole32.CoTaskMemFree(pidl)
