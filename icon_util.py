"""Pobieranie ikon plików/skrótów z powłoki Windows."""
from PySide6.QtCore import QFileInfo, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap, QColor, QFont
from PySide6.QtWidgets import QFileIconProvider

import shell_dnd

_provider = QFileIconProvider()


def icon_for_path(path: str) -> QIcon:
    """Zwraca ikonę skojarzoną z plikiem/folderem/skrótem/aplikacją powłoki.

    Dla nieistniejących ścieżek (np. usunięty cel) zwraca ikonę zastępczą.
    """
    if path and path.lower().startswith("shell:"):
        icon = shell_dnd.shell_icon(path)
        return icon if icon is not None else _placeholder_icon(path)
    info = QFileInfo(path)
    if info.exists():
        icon = _provider.icon(info)
        if not icon.isNull():
            return icon
    return _placeholder_icon(path)


def _placeholder_icon(path: str) -> QIcon:
    """Prosta wygenerowana ikona z pierwszą literą nazwy."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(120, 120, 130))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(8, 8, 48, 48, 10, 10)
    p.setPen(QColor(255, 255, 255))
    f = QFont()
    f.setPointSize(22)
    f.setBold(True)
    p.setFont(f)
    name = (path.rstrip("/\\").split("\\")[-1].split("/")[-1] or "?")
    p.drawText(pm.rect(), Qt.AlignCenter, name[:1].upper())
    p.end()
    return QIcon(pm)
