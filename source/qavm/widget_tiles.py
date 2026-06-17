from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
	QMainWindow, QMenu, QWidget, QScrollArea, QVBoxLayout, 
)
from PyQt6.QtGui import (
	QAction,
	QCursor,
)
from PyQt6.QtCore import (
	Qt,
)

from qavm.qavmapi import (
	BaseDescriptor, BaseTileBuilder,
)
from qavm.manager_plugin import SoftwareHandler
from qavm.utils_gui import FlowLayout
from qavm.utils_widgets import PopulateContextMenuTagsAndNotes

if TYPE_CHECKING:
	from qavm.window_main import MainWindow
	
import qavm.logs as logs
logger = logs.logger

class TilesWidget(QWidget):
	def __init__(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, swHandler: SoftwareHandler, viewUID: str, parent: QWidget):
		super().__init__(parent)

		self.descs = descs
		self.tileBuilder = tileBuilder
		self.swHandler: SoftwareHandler = swHandler
		self.viewUID: str = viewUID
		self.mainWindow: 'MainWindow' = parent

		self.flowLayout: FlowLayout | None = None

		tiles = self._createTiles(descs)
		flWidget = self._createFlowLayoutWithFromWidgets(tiles)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(scrollWidget)

	def _showContextMenu(self, desc: BaseDescriptor):
		if menu := self.tileBuilder.GetContextMenu(desc):
			PopulateContextMenuTagsAndNotes(menu, desc, self.mainWindow, self, self.swHandler.pluginID, self.swHandler.GetID(), self.viewUID)
			menu.exec(QCursor.pos())

	def _setupTileWidget(self, desc: BaseDescriptor, tileWidget: QWidget) -> QWidget:
		tileWidget.setProperty("descriptor_uid", desc.GetUID())  # Store descriptor UID in widget property for later reference
		tileWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		tileWidget.customContextMenuRequested.connect(lambda pos, d=desc: self._showContextMenu(d))
		return tileWidget

	def _createTiles(self, descs: list[BaseDescriptor]) -> list[QWidget]:
		tiles = []

		for desc in descs:
			tileWidget = self.tileBuilder.CreateTileWidget(desc, self.mainWindow)
			self._setupTileWidget(desc, tileWidget)
			desc.descDataUpdated.connect(partial(self._onDescDataUpdated, desc))
			tiles.append(tileWidget)

		return tiles
	
	def _onDescDataUpdated(self, desc: BaseDescriptor):
		updatedWidget = self.tileBuilder.CreateTileWidget(desc, self.mainWindow)
		if updatedWidget:
			self._replaceTileWidget(desc, updatedWidget)
	
	def _replaceTileWidget(self, desc: BaseDescriptor, newWidget: QWidget):
		if self.flowLayout is None:
			return

		descUID = desc.GetUID()
		for index in range(self.flowLayout.count()):
			item = self.flowLayout.itemAt(index)
			if item is None:
				continue
			oldWidget = item.widget()
			if oldWidget is None or oldWidget.property("descriptor_uid") != descUID:
				continue

			# Found the matching tile: remove the old one and insert the new one at the same position
			self.flowLayout.takeAt(index)
			oldWidget.setParent(None)
			oldWidget.deleteLater()

			self._setupTileWidget(desc, newWidget)
			newWidget.setFixedWidth(newWidget.sizeHint().width())
			self.flowLayout.insertWidget(index, newWidget)
			return

		logger.warning(f"No tile widget found for descriptor {descUID} to replace")

	def _createFlowLayoutWithFromWidgets(self, widgets: list[QWidget]) -> QWidget:
		flWidget = QWidget(self)
		flowLayout = FlowLayout(flWidget, margin=5, hspacing=5, vspacing=5)
		flowLayout.setSpacing(0)

		for widget in widgets:
			widget.setFixedWidth(widget.sizeHint().width())
			flowLayout.addWidget(widget)

		self.flowLayout = flowLayout
		return flWidget

	def _wrapWidgetInScrollArea(self, widget: QWidget) -> QScrollArea:
		scrollWidget = QScrollArea(self)
		scrollWidget.setWidgetResizable(True)
		scrollWidget.setWidget(widget)
		return scrollWidget