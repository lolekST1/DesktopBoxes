"""Uruchamianie elementów (pliki, foldery, skróty, adresy URL)."""
import os
import subprocess

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def launch(path: str) -> bool:
    """Otwiera element domyślnym programem. Zwraca True przy powodzeniu."""
    if not path:
        return False
    # Aplikacje powłoki / UWP (shell:AppsFolder\<AUMID>) – uruchom przez Eksplorator.
    if path.lower().startswith("shell:"):
        try:
            subprocess.Popen(["explorer.exe", path], creationflags=0x08000000)
            return True
        except OSError:
            return False
    # Adresy URL i protokoły (http, mailto, ...)
    if "://" in path[:12] or path.lower().startswith(("http:", "https:", "mailto:")):
        return QDesktopServices.openUrl(QUrl(path))
    try:
        # os.startfile obsługuje .lnk, .exe, foldery i skojarzenia plików.
        os.startfile(path)  # type: ignore[attr-defined]  # tylko Windows
        return True
    except AttributeError:
        # Zapas dla systemów innych niż Windows.
        subprocess.Popen(["xdg-open", path])
        return True
    except OSError:
        return False


def open_containing_folder(path: str) -> None:
    """Otwiera Eksplorator z zaznaczonym elementem."""
    if "://" in path[:12]:
        return
    norm = os.path.normpath(path)
    if os.path.exists(norm):
        subprocess.Popen(["explorer", "/select,", norm])
    else:
        folder = os.path.dirname(norm)
        if os.path.isdir(folder):
            os.startfile(folder)  # type: ignore[attr-defined]
