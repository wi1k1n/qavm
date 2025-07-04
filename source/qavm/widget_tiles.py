from pathlib import Path

from PyQt6.QtWidgets import (
	QWidget, QScrollArea, QVBoxLayout, 
)
from PyQt6.QtGui import (
    QCursor,
)
from PyQt6.QtCore import (
	Qt,
)

from qavm.qavmapi import (
	BaseDescriptor, BaseTileBuilder,
)
from qavm.utils_gui import FlowLayout


class TilesWidget(QWidget):
    def __init__(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget):
        super().__init__(parent)

        self.descs = descs
        self.tileBuilder = tileBuilder

        tiles = self._createTiles(descs, tileBuilder, parent)
        flWidget = self._createFlowLayoutWithFromWidgets(tiles)
        scrollWidget = self._wrapWidgetInScrollArea(flWidget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scrollWidget)

    def _createTiles(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget) -> list[QWidget]:
        tiles = []

        def showContextMenu(desc):
            if menu := tileBuilder.GetContextMenu(desc):
                menu.exec(QCursor.pos())

        for desc in descs:
            tileWidget = tileBuilder.CreateTileWidget(desc, parent)
            tileWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tileWidget.customContextMenuRequested.connect(lambda pos, d=desc: showContextMenu(d))
            tiles.append(tileWidget)

        return tiles

    def _createFlowLayoutWithFromWidgets(self, widgets: list[QWidget]) -> QWidget:
        flWidget = QWidget(self)
        flowLayout = FlowLayout(flWidget, margin=5, hspacing=5, vspacing=5)
        flowLayout.setSpacing(0)

        for widget in widgets:
            widget.setFixedWidth(widget.sizeHint().width())
            flowLayout.addWidget(widget)

        return flWidget

    def _wrapWidgetInScrollArea(self, widget: QWidget) -> QScrollArea:
        scrollWidget = QScrollArea(self)
        scrollWidget.setWidgetResizable(True)
        scrollWidget.setWidget(widget)
        return scrollWidget