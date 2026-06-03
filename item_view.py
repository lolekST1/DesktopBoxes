"""Siatka ikon wewnątrz boxa: drag&drop z Eksploratora, zmiana kolejności, menu."""
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QListView, QAbstractItemView

import launcher
import shell_dnd
from icon_util import icon_for_path

PATH_ROLE = Qt.UserRole + 1


class ItemView(QListWidget):
    """Lista elementów w trybie ikon."""

    entries_dropped = Signal(list)      # list[{name, path}] – upuszczone z zewnątrz
    order_changed = Signal()            # zmieniono kolejność elementów
    launch_requested = Signal(str)      # ścieżka do uruchomienia
    remove_requested = Signal(object)   # QListWidgetItem do usunięcia
    rename_requested = Signal(object)   # QListWidgetItem do zmiany nazwy

    def __init__(self, icon_size: int = 48, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.IconMode)
        self.setMovement(QListView.Snap)
        self.setResizeMode(QListView.Adjust)
        self.setFlow(QListView.LeftToRight)
        self.setWrapping(True)
        self.setUniformItemSizes(True)
        self.setSpacing(8)
        self.setWordWrap(True)
        self.setTextElideMode(Qt.ElideRight)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.setFrameShape(QListWidget.NoFrame)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.set_icon_size(icon_size)
        self.itemDoubleClicked.connect(self._on_double_click)

    def set_icon_size(self, size: int):
        self._icon_size = size
        self.setIconSize(QSize(size, size))
        grid_w = size + 36
        grid_h = size + 38
        self.setGridSize(QSize(grid_w, grid_h))
        for i in range(self.count()):
            self.item(i).setSizeHint(QSize(grid_w, grid_h))

    # ---- elementy --------------------------------------------------------
    def add_item(self, name: str, path: str):
        item = QListWidgetItem(icon_for_path(path), name)
        item.setData(PATH_ROLE, path)
        item.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
        item.setToolTip(path)
        item.setSizeHint(self.gridSize())
        self.addItem(item)
        return item

    def items_data(self) -> list:
        return [
            {"name": self.item(i).text(), "path": self.item(i).data(PATH_ROLE)}
            for i in range(self.count())
        ]

    # ---- drag & drop -----------------------------------------------------
    @staticmethod
    def _is_external(mime) -> bool:
        return mime.hasUrls() or mime.hasFormat(shell_dnd.SHELL_IDLIST_FMT)

    def dragEnterEvent(self, event):
        if self._is_external(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._is_external(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if self._is_external(event.mimeData()):
            entries = shell_dnd.resolve_drop(event.mimeData())
            if entries:
                self.entries_dropped.emit(entries)
                event.acceptProposedAction()
                return
        super().dropEvent(event)
        self.order_changed.emit()

    # ---- interakcja ------------------------------------------------------
    def _on_double_click(self, item: QListWidgetItem):
        path = item.data(PATH_ROLE)
        if path:
            self.launch_requested.emit(path)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu

        item = self.itemAt(event.pos())
        menu = QMenu(self)
        if item is not None:
            path = item.data(PATH_ROLE)
            menu.addAction("Otwórz", lambda: self.launch_requested.emit(path))
            menu.addAction(
                "Pokaż w Eksploratorze",
                lambda: launcher.open_containing_folder(path),
            )
            menu.addSeparator()
            menu.addAction("Zmień nazwę…", lambda: self.rename_requested.emit(item))
            menu.addAction("Usuń z boxa", lambda: self.remove_requested.emit(item))
            menu.exec(event.globalPos())
