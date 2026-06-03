"""Pojedynczy box – półprzezroczyste okno-launcher na pulpicie."""
import uuid

from PySide6.QtCore import Qt, QTimer, QPoint, QRect, Signal
from PySide6.QtGui import QColor, QPainter, QFont, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QSizeGrip,
    QInputDialog, QMenu, QColorDialog, QMessageBox,
)

import launcher
from item_view import ItemView, PATH_ROLE

TITLE_BAR_HEIGHT = 30
PALETTE = ["#2D6BB5", "#2E8B57", "#9C4DCC", "#C0392B", "#D68910", "#16A085", "#34495E"]


class BoxWindow(QWidget):
    changed = Signal()           # stan boxa się zmienił – zapisz konfigurację
    delete_requested = Signal(object)

    def __init__(self, data: dict = None, parent=None):
        super().__init__(parent)
        data = data or {}
        self.box_id = data.get("id") or uuid.uuid4().hex[:8]
        self.title = data.get("title", "Nowy box")
        self.color = data.get("color", PALETTE[0])
        self.bg_opacity = float(data.get("opacity", 0.82))
        self.icon_size = int(data.get("icon_size", 48))

        self.setWindowTitle(self.title)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(160, 120)

        self._drag_offset = None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self.changed.emit)

        self._build_ui()
        self._apply_styles()

        geo = data.get("geometry")
        if geo and len(geo) == 4:
            self.setGeometry(QRect(*geo))
        else:
            self.resize(280, 320)
            self.move(120, 120)

        for it in data.get("items", []):
            self.view.add_item(it.get("name", "?"), it.get("path", ""))

    # ---- budowa UI -------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 6)
        root.setSpacing(4)

        # pasek tytułu
        bar = QHBoxLayout()
        bar.setContentsMargins(6, 0, 2, 0)
        self.title_label = QLabel(self.title)
        f = QFont()
        f.setBold(True)
        self.title_label.setFont(f)
        self.title_label.setStyleSheet("color: white;")
        bar.addWidget(self.title_label, 1)

        self.menu_btn = QToolButton()
        self.menu_btn.setText("⚙")
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.setPopupMode(QToolButton.InstantPopup)
        self.menu_btn.setMenu(self._build_menu())
        bar.addWidget(self.menu_btn)
        self._bar_widget = QWidget()
        self._bar_widget.setFixedHeight(TITLE_BAR_HEIGHT)
        self._bar_widget.setLayout(bar)
        self._bar_widget.installEventFilter(self)
        root.addWidget(self._bar_widget)

        # siatka ikon
        self.view = ItemView(self.icon_size)
        self.view.entries_dropped.connect(self._on_entries_dropped)
        self.view.order_changed.connect(self._schedule_save)
        self.view.launch_requested.connect(self._on_launch)
        self.view.remove_requested.connect(self._on_remove_item)
        self.view.rename_requested.connect(self._on_rename_item)
        root.addWidget(self.view, 1)

        # uchwyt zmiany rozmiaru
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch(1)
        self._grip = QSizeGrip(self)
        grip_row.addWidget(self._grip, 0, Qt.AlignBottom | Qt.AlignRight)
        root.addLayout(grip_row)

    def _build_menu(self) -> QMenu:
        m = QMenu(self)
        m.addAction("➕ Dodaj aplikację z menu Start…", self._add_apps)
        m.addSeparator()
        m.addAction("Zmień nazwę boxa…", self._rename_box)
        color_menu = m.addMenu("Kolor")
        for c in PALETTE:
            act = QAction(c, self)
            act.triggered.connect(lambda _=False, col=c: self._set_color(col))
            color_menu.addAction(act)
        color_menu.addSeparator()
        color_menu.addAction("Inny kolor…", self._pick_custom_color)

        op_menu = m.addMenu("Przezroczystość")
        for label, val in [("Pełna (95%)", 0.95), ("Lekka (82%)", 0.82),
                           ("Średnia (65%)", 0.65), ("Duża (45%)", 0.45)]:
            op_menu.addAction(label, lambda v=val: self._set_opacity(v))

        size_menu = m.addMenu("Rozmiar ikon")
        for label, val in [("Małe (32)", 32), ("Średnie (48)", 48),
                           ("Duże (64)", 64), ("Bardzo duże (96)", 96)]:
            size_menu.addAction(label, lambda v=val: self._set_icon_size(v))

        m.addSeparator()
        m.addAction("Usuń box", self._confirm_delete)
        return m

    # ---- styl i rysowanie ------------------------------------------------
    def _apply_styles(self):
        self.view.setStyleSheet(
            """
            QListWidget { background: transparent; border: none; color: white; }
            QListWidget::item { color: white; border-radius: 6px; padding: 2px; }
            QListWidget::item:selected { background: rgba(255,255,255,55); }
            QListWidget::item:hover { background: rgba(255,255,255,30); }
            QToolTip { color: #fff; background: #333; border: 1px solid #555; }
            """
        )
        self.menu_btn.setStyleSheet(
            """
            QToolButton { color: white; border: none; font-size: 14px;
                          padding: 2px 6px; border-radius: 4px; }
            QToolButton:hover { background: rgba(255,255,255,40); }
            QToolButton::menu-indicator { image: none; }
            """
        )
        self.update()

    def paintEvent(self, event):
        radius = 14
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)

        # tło boxa
        body = QColor(20, 24, 32)
        body.setAlphaF(self.bg_opacity)
        p.setBrush(body)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(rect, radius, radius)

        # pasek nagłówka – zaokrąglony u góry, prosty u dołu
        header = QColor(self.color)
        header.setAlphaF(min(1.0, self.bg_opacity + 0.13))
        head_h = TITLE_BAR_HEIGHT + 6
        p.setBrush(header)
        p.setClipRect(QRect(rect.left(), rect.top(), rect.width() + 1, head_h))
        p.drawRoundedRect(rect.left(), rect.top(), rect.width(),
                          head_h + radius, radius, radius)
        p.end()

    # ---- przenoszenie okna (przez pasek tytułu) --------------------------
    def eventFilter(self, obj, event):
        if obj is self._bar_widget:
            et = event.type()
            if et == event.Type.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if et == event.Type.MouseMove and self._drag_offset is not None:
                self.move(event.globalPosition().toPoint() - self._drag_offset)
                return True
            if et == event.Type.MouseButtonRelease:
                self._drag_offset = None
                self._schedule_save()
                return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_save()

    # ---- akcje elementów -------------------------------------------------
    def _on_entries_dropped(self, entries):
        for e in entries:
            self.view.add_item(e.get("name") or e.get("path", "?"), e.get("path", ""))
        self._schedule_save()

    def _add_apps(self):
        from app_picker import AppPickerDialog

        dlg = AppPickerDialog(self)
        if dlg.exec() and dlg.selected_apps():
            for app in dlg.selected_apps():
                self.view.add_item(app["name"], app["path"])
            self._schedule_save()

    def _on_launch(self, path):
        if not launcher.launch(path):
            QMessageBox.warning(self, "DesktopBoxes",
                                f"Nie udało się otworzyć:\n{path}")

    def _on_remove_item(self, item):
        self.view.takeItem(self.view.row(item))
        self._schedule_save()

    def _on_rename_item(self, item):
        text, ok = QInputDialog.getText(self, "Zmień nazwę", "Nowa nazwa:",
                                        text=item.text())
        if ok and text.strip():
            item.setText(text.strip())
            self._schedule_save()

    # ---- akcje boxa ------------------------------------------------------
    def _rename_box(self):
        text, ok = QInputDialog.getText(self, "Zmień nazwę boxa", "Nazwa:",
                                        text=self.title)
        if ok and text.strip():
            self.title = text.strip()
            self.title_label.setText(self.title)
            self.setWindowTitle(self.title)
            self._schedule_save()

    def _set_color(self, color):
        self.color = color
        self.update()
        self._schedule_save()

    def _pick_custom_color(self):
        col = QColorDialog.getColor(QColor(self.color), self, "Wybierz kolor")
        if col.isValid():
            self._set_color(col.name())

    def _set_opacity(self, value):
        self.bg_opacity = value
        self.update()
        self._schedule_save()

    def _set_icon_size(self, value):
        self.icon_size = value
        self.view.set_icon_size(value)
        self._schedule_save()

    def _confirm_delete(self):
        res = QMessageBox.question(
            self, "Usuń box",
            f"Usunąć box „{self.title}”?\n(Skróty na dysku nie zostaną usunięte.)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.delete_requested.emit(self)

    # ---- zapis -----------------------------------------------------------
    def _schedule_save(self):
        self._save_timer.start()

    def to_dict(self) -> dict:
        g = self.geometry()
        return {
            "id": self.box_id,
            "title": self.title,
            "color": self.color,
            "opacity": self.bg_opacity,
            "icon_size": self.icon_size,
            "geometry": [g.x(), g.y(), g.width(), g.height()],
            "items": self.view.items_data(),
        }
