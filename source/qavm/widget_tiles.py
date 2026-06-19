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
from qavm.qavmapi.gui import TagBubblesFlowWidget
from qavm.manager_plugin import SoftwareHandler
from qavm.utils_gui import FlowLayout
from qavm.utils_widgets import PopulateContextMenuTagsAndNotes, AssignTagUIDToDescriptor, TAG_MIME_TYPE

if TYPE_CHECKING:
	from qavm.window_main import MainWindow
	from qavm.manager_tags import BaseTagImpl
	
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

		self.setAcceptDrops(True)  # accept tag bubbles dragged from the Tags palette

		tiles = self._createTiles(descs)
		flWidget = self._createFlowLayoutWithFromWidgets(tiles)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(scrollWidget)

	def dragEnterEvent(self, event):
		if event.mimeData().hasFormat(TAG_MIME_TYPE):
			event.acceptProposedAction()
		else:
			event.ignore()

	def dragMoveEvent(self, event):
		if event.mimeData().hasFormat(TAG_MIME_TYPE):
			event.acceptProposedAction()
		else:
			event.ignore()

	def dropEvent(self, event):
		if not event.mimeData().hasFormat(TAG_MIME_TYPE):
			event.ignore()
			return
		tagUID: str = bytes(event.mimeData().data(TAG_MIME_TYPE).data()).decode('utf-8')
		desc: BaseDescriptor | None = self._findDescriptorForChild(self.childAt(event.position().toPoint()))
		if desc is None:
			event.ignore()
			return
		AssignTagUIDToDescriptor(desc, tagUID)
		event.acceptProposedAction()

	def _findDescriptorForChild(self, widget: QWidget | None) -> BaseDescriptor | None:
		w = widget
		while w is not None and w is not self:
			descUID = w.property("descriptor_uid")
			if descUID:
				return next((d for d in self.descs if d.GetUID() == descUID), None)
			w = w.parentWidget()
		return None

	def _showContextMenu(self, desc: BaseDescriptor):
		if menu := self.tileBuilder.GetContextMenu(desc):
			tagUnderCursor: 'BaseTagImpl | None' = self._tagUnderCursor()
			PopulateContextMenuTagsAndNotes(menu, desc, self.mainWindow, self, self.swHandler.pluginID, self.swHandler.GetID(), self.viewUID, tagUnderCursor)
			menu.exec(QCursor.pos())

	def _tagUnderCursor(self) -> 'BaseTagImpl | None':
		""" Returns the tag whose bubble is under the cursor (where the context menu was invoked), or None. """
		globalPos = QCursor.pos()
		w: QWidget | None = self.childAt(self.mapFromGlobal(globalPos))
		while w is not None and w is not self:
			if isinstance(w, TagBubblesFlowWidget):
				return w.GetTagAt(w.mapFromGlobal(globalPos))
			w = w.parentWidget()
		return None

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
			# Connect to the bound method (a QObject slot) rather than a partial so Qt auto-disconnects
			# this connection when the widget is destroyed (e.g. on workspace switch). Otherwise the
			# descriptor outlives the widget and keeps firing into a deleted widget/mainWindow.
			desc.descDataUpdated.connect(self._onDescDataUpdated)
			tiles.append(tileWidget)

		return tiles
	
	def _onDescDataUpdated(self):
		desc = self.sender()
		if not isinstance(desc, BaseDescriptor):
			return
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