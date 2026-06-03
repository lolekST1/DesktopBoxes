# DesktopBoxes

Lekki menedżer ikon na pulpicie w stylu **iTop Easy Desktop** — organizuje skróty
i pliki w półprzezroczyste „boxy" leżące na pulpicie. Napisany w Pythonie + PySide6 (Qt).

![status](https://img.shields.io/badge/platforma-Windows-blue)

## Funkcje

- 🗂️ **Boxy** — półprzezroczyste, bezramkowe okna-pojemniki na pulpicie.
- 🖱️ **Przeciągnij i upuść** pliki / foldery / skróty (`.lnk`) z Eksploratora wprost do boxa.
- 🪟 **Przeciąganie z menu Start** — także aplikacji ze Sklepu (UWP); ich identyfikator
  (AppUserModelID) jest odczytywany z danych powłoki Windows.
- 🧩 **„Dodaj aplikację z menu Start…"** (przycisk ⚙ w boxie) — okno z wyszukiwarką i listą
  **wszystkich** zainstalowanych aplikacji (klasycznych i UWP). To pewny sposób na dodanie
  aplikacji, których Windows nie pozwala przeciągnąć — np. **przypiętych na pasku zadań**.
- ▶️ **Dwuklik** uruchamia element domyślnym programem (obsługa `.lnk`, `.exe`, folderów, plików, aplikacji UWP).
- 🎨 **Personalizacja** — nazwa boxa, kolor, przezroczystość, rozmiar ikon.
- 📐 **Przeciąganie i zmiana rozmiaru** — chwyć pasek tytułu, by przesunąć; uchwyt w prawym
  dolnym rogu zmienia rozmiar.
- 🔀 **Zmiana kolejności** ikon wewnątrz boxa metodą przeciągnij-upuść.
- 💾 **Automatyczny zapis** układu (`%APPDATA%\DesktopBoxes\config.json`).
- 🧰 **Ikona w zasobniku** — nowy box, pokaż/ukryj wszystkie, autostart, zakończ.
- 🚀 **Autostart** z systemem (jednym kliknięciem, klucz rejestru `HKCU\...\Run`).

## Wymagania

- Windows 10 / 11
- Python 3.10+ (`py --version`)
- PySide6

## Instalacja

```powershell
cd C:\Users\HP\DesktopBoxes
py -m pip install -r requirements.txt
```

## Gotowy plik .exe

Najprościej: pobierz `DesktopBoxes.exe` z zakładki **[Releases](../../releases)** i uruchom —
nie wymaga instalacji Pythona ani żadnych bibliotek.

## Uruchomienie ze źródeł

- **Normalnie (bez konsoli):** dwuklik na `DesktopBoxes.vbs`
- **Z konsolą (diagnostyka):** dwuklik na `run.bat` lub `py main.py`

## Budowanie własnego .exe

```powershell
py -m pip install pyinstaller
py -m PyInstaller --noconfirm --onefile --windowed --name DesktopBoxes `
   --hidden-import app_picker --hidden-import apps --hidden-import shell_dnd main.py
```

Gotowy plik powstanie w `dist\DesktopBoxes.exe`.

Aplikacja działa w tle — ikona w **zasobniku systemowym** (obok zegara).
Kliknięcie ikony pokazuje/ukrywa boxy; prawy klik otwiera menu.

## Jak używać

| Akcja | Sposób |
|-------|--------|
| Dodać element | przeciągnij plik/skrót z Eksploratora **lub aplikację z menu Start** do boxa |
| Dodać aplikację z paska zadań / Start (też UWP) | ⚙ → „Dodaj aplikację z menu Start…" |
| Uruchomić element | dwuklik na ikonie |
| Menu elementu (otwórz / pokaż w Eksploratorze / zmień nazwę / usuń) | prawy klik na ikonie |
| Przesunąć box | przeciągnij pasek tytułu |
| Zmienić rozmiar boxa | uchwyt w prawym dolnym rogu |
| Ustawienia boxa | przycisk ⚙ na pasku tytułu |
| Nowy / pokaż-ukryj / autostart / zakończ | menu ikony w zasobniku |

> Usunięcie elementu z boxa **nie** kasuje pliku ani skrótu na dysku.

## Struktura projektu

```
DesktopBoxes/
├─ main.py          # aplikacja, menedżer boxów, ikona zasobnika
├─ box_window.py    # pojedynczy box (okno) + jego menu i rysowanie
├─ item_view.py     # siatka ikon, drag&drop, menu elementu
├─ shell_dnd.py     # rozkodowanie drag z menu Start (PIDL/UWP) + ikony powłoki
├─ apps.py          # lista aplikacji z menu Start (Get-StartApps)
├─ app_picker.py    # okno wyboru aplikacji z wyszukiwarką
├─ icon_util.py     # pobieranie ikon z powłoki Windows
├─ launcher.py      # uruchamianie elementów / otwieranie folderu
├─ autostart.py     # wpis autostartu w rejestrze
├─ storage.py       # zapis/odczyt config.json
├─ DesktopBoxes.vbs # uruchomienie bez konsoli
├─ run.bat          # uruchomienie z konsolą
└─ requirements.txt
```

## Uwagi techniczne

- Boxy mają flagę „zawsze na spodzie" (`WindowStaysOnBottomHint`) i nie pojawiają się
  na pasku zadań (`Qt.Tool`) — zachowują się jak widżety pulpitu.
- Konfiguracja zapisywana jest atomowo (plik tymczasowy + zamiana), co chroni przed
  uszkodzeniem przy nagłym zamknięciu.
