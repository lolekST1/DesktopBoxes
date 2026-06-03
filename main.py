"""DesktopBoxes – menedżer ikon na pulpicie (półprzezroczyste boxy-launchery).

Uruchomienie:  pythonw main.py   (bez okna konsoli)
               python  main.py   (z konsolą – do diagnostyki)
"""
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox,
)

import storage
import autostart
from box_window import BoxWindow

APP_VERSION = "1.0"


class DesktopBoxesApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("DesktopBoxes")

        self.cfg = storage.load_config()
        self.boxes: list[BoxWindow] = []
        self.boxes_visible = self.cfg["settings"].get("boxes_visible", True)

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(300)
        self._save_timer.timeout.connect(self._save_now)

        self._build_tray()
        self._load_boxes()

        if not self.boxes:
            self._create_welcome_box()

    # ---- ikona zasobnika -------------------------------------------------
    def _app_icon(self) -> QIcon:
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2D6BB5"))
        p.drawRoundedRect(6, 6, 24, 24, 6, 6)
        p.setBrush(QColor("#2E8B57"))
        p.drawRoundedRect(34, 6, 24, 24, 6, 6)
        p.setBrush(QColor("#D68910"))
        p.drawRoundedRect(6, 34, 24, 24, 6, 6)
        p.setBrush(QColor("#9C4DCC"))
        p.drawRoundedRect(34, 34, 24, 24, 6, 6)
        p.end()
        return QIcon(pm)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self._app_icon())
        self.tray.setToolTip("DesktopBoxes")

        menu = QMenu()
        menu.addAction("➕ Nowy box", self.add_box)
        self.toggle_action = menu.addAction("👁 Pokaż / ukryj boxy", self.toggle_visibility)

        menu.addAction("🔼 Przywróć boxy na wierzch", self.raise_boxes)
        menu.addSeparator()

        self.autostart_action = QAction("🚀 Uruchamiaj przy starcie systemu", menu)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(autostart.is_enabled())
        self.autostart_action.toggled.connect(self._on_autostart_toggled)
        menu.addAction(self.autostart_action)

        menu.addAction("ℹ️ O programie", self._about)
        menu.addSeparator()
        menu.addAction("❌ Zakończ", self.quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # pojedyncze kliknięcie
            self.toggle_visibility()

    # ---- zarządzanie boxami ---------------------------------------------
    def _load_boxes(self):
        for data in self.cfg.get("boxes", []):
            self._add_box_widget(data, show=self.boxes_visible)

    def _add_box_widget(self, data, show=True) -> BoxWindow:
        box = BoxWindow(data)
        box.changed.connect(self.schedule_save)
        box.delete_requested.connect(self.delete_box)
        self.boxes.append(box)
        if show:
            box.show()
        return box

    def add_box(self):
        # nowy box w pobliżu kursora / środka ekranu
        screen = self.app.primaryScreen().availableGeometry()
        x = screen.left() + 160 + (len(self.boxes) % 5) * 36
        y = screen.top() + 120 + (len(self.boxes) % 5) * 36
        data = {"title": f"Box {len(self.boxes) + 1}",
                "geometry": [x, y, 280, 320]}
        box = self._add_box_widget(data, show=True)
        self.boxes_visible = True
        box.raise_()
        box.activateWindow()
        self.schedule_save()

    def delete_box(self, box: BoxWindow):
        if box in self.boxes:
            self.boxes.remove(box)
        box.hide()
        box.deleteLater()
        self.schedule_save()

    def toggle_visibility(self):
        self.boxes_visible = not self.boxes_visible
        for box in self.boxes:
            box.setVisible(self.boxes_visible)
        self.schedule_save()

    def raise_boxes(self):
        self.boxes_visible = True
        for box in self.boxes:
            box.show()
            box.raise_()
        self.schedule_save()

    # ---- autostart -------------------------------------------------------
    def _on_autostart_toggled(self, enabled):
        ok = autostart.set_enabled(enabled)
        if not ok:
            QMessageBox.warning(None, "DesktopBoxes",
                                "Nie udało się zmienić ustawienia autostartu.")
            self.autostart_action.setChecked(autostart.is_enabled())

    # ---- zapis -----------------------------------------------------------
    def schedule_save(self):
        self._save_timer.start()

    def _save_now(self):
        self.cfg["boxes"] = [b.to_dict() for b in self.boxes]
        self.cfg["settings"]["boxes_visible"] = self.boxes_visible
        storage.save_config(self.cfg)

    # ---- pozostałe -------------------------------------------------------
    def _create_welcome_box(self):
        screen = self.app.primaryScreen().availableGeometry()
        data = {
            "title": "Start – przeciągnij tu ikony",
            "geometry": [screen.left() + 120, screen.top() + 120, 300, 340],
            "color": "#2D6BB5",
        }
        self._add_box_widget(data, show=True)

    def _about(self):
        QMessageBox.information(
            None, "O programie",
            f"<b>DesktopBoxes</b> {APP_VERSION}<br><br>"
            "Organizuj ikony pulpitu w półprzezroczyste boxy.<br><br>"
            "• Przeciągnij pliki/skróty z Eksploratora do boxa<br>"
            "• Dwuklik uruchamia element<br>"
            "• Pasek tytułu – przeciąganie boxa, ⚙ – ustawienia<br>"
            "• Prawy klik na ikonie – menu elementu<br>"
            "• Kliknięcie ikony w zasobniku – pokaż/ukryj boxy",
        )

    def quit(self):
        self._save_now()
        self.tray.hide()
        self.app.quit()

    def run(self):
        sys.exit(self.app.exec())


def main():
    app = DesktopBoxesApp()
    app.run()


if __name__ == "__main__":
    main()
