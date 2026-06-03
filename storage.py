"""Wczytywanie i zapisywanie konfiguracji DesktopBoxes."""
import json
import os
from pathlib import Path

APP_NAME = "DesktopBoxes"


def data_dir() -> Path:
    """Katalog na dane aplikacji (%APPDATA%\\DesktopBoxes)."""
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return data_dir() / "config.json"


def default_config() -> dict:
    return {
        "boxes": [],
        "settings": {"boxes_visible": True},
    }


def load_config() -> dict:
    p = config_path()
    if p.exists():
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
            cfg.setdefault("boxes", [])
            cfg.setdefault("settings", {"boxes_visible": True})
            return cfg
        except Exception:
            # Uszkodzony plik – zachowaj kopię i zacznij od nowa.
            try:
                p.rename(p.with_suffix(".json.bak"))
            except Exception:
                pass
    return default_config()


def save_config(cfg: dict) -> None:
    tmp = config_path().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, config_path())
