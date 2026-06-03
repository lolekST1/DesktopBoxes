"""Okno wyboru aplikacji z menu Start / paska zadań (z wyszukiwarką)."""
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QAbstractItemView, QApplication,
)

import apps
from icon_util import icon_for_path

PATH_ROLE = Qt.UserRole + 1


class AppPickerDialog(QDialog):
    """Pozwala wybrać jedną lub więcej aplikacji do dodania do boxa."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj aplikację z menu Start")
        self.resize(420, 520)
        self._selected = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Wyszukaj i zaznacz aplikacje (Ctrl/Shift = wiele):"))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Filtruj po nazwie…")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setIconSize(QSize(28, 28))
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        layout.addWidget(self.list, 1)

        btns = QHBoxLayout()
        self.count_label = QLabel("")
        btns.addWidget(self.count_label, 1)
        ok = QPushButton("Dodaj")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Anuluj")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

        # Wypełnij listę po pokazaniu okna (pobranie aplikacji bywa wolne).
        QTimer.singleShot(0, self._populate)

    def _populate(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for app in apps.list_start_apps():
                item = QListWidgetItem(icon_for_path(app["path"]), app["name"])
                item.setData(PATH_ROLE, app["path"])
                item.setToolTip(app["path"])
                self.list.addItem(item)
        finally:
            QApplication.restoreOverrideCursor()
        self.count_label.setText(f"{self.list.count()} aplikacji")
        self.search.setFocus()

    def _filter(self, text):
        text = text.strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setHidden(text not in it.text().lower())

    def accept(self):
        self._selected = [
            {"name": it.text(), "path": it.data(PATH_ROLE)}
            for it in self.list.selectedItems()
        ]
        super().accept()

    def selected_apps(self) -> list:
        return self._selected
