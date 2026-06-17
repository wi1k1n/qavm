from functools import partial
from pathlib import Path

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

from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorDataImpl

from qavm.manager_tags import Tag
from qavm.qavmapi import (
	BaseDescriptor, BaseTileBuilder,
)
from qavm.utils_gui import FlowLayout

import qavm.logs as logs
logger = logs.logger

class TilesWidget(QWidget):
	def __init__(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget):
		super().__init__(parent)

		self.descs = descs
		self.tileBuilder = tileBuilder
		self.mainWindow: QMainWindow = parent

		self.flowLayout: FlowLayout | None = None

		tiles = self._createTiles(descs)
		flWidget = self._createFlowLayoutWithFromWidgets(tiles)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.addWidget(scrollWidget)

	def _showContextMenu(self, desc: BaseDescriptor):
		if menu := self.tileBuilder.GetContextMenu(desc):
			##############################
			def assignTag(tag: Tag):
				logger.info(f"Assigning tag {tag.GetName()} to descriptor {desc.GetUID()}")
				self.mainWindow.tagsManager.AssignTag(desc, tag)
				desc.descDataUpdated.emit()
			def removeTag(desc: BaseDescriptor, tag: Tag):
				logger.info(f"Removing tag {tag.GetName()} from descriptor {desc.GetUID()}")
				self.mainWindow.tagsManager.RemoveTag(desc, tag)
				desc.descDataUpdated.emit()
				
			descData: DescriptorDataImpl = self.mainWindow.descDataManager.GetDescriptorData(desc)
			descTagsUIDs: list[str] = descData.tags
			
			addTagSubMenu = None
			if tags := self.mainWindow.tagsManager.GetTags().values():
				addTagSubMenu: QMenu = QMenu("Assign Tag", self)
				for tag in tags:
					if tag.GetUID() in descTagsUIDs:
						continue
					action = QAction(tag.GetName(), self, triggered=partial(assignTag, tag))
					addTagSubMenu.addAction(action)
				

			removeTagsSubMenu = None
			if descTags := [self.mainWindow.tagsManager.GetTag(tagUID) for tagUID in descTagsUIDs if self.mainWindow.tagsManager.GetTag(tagUID)]:
				removeTagsSubMenu: QMenu = QMenu("Remove Tag", self)
				for tag in descTags:
					action = QAction(tag.GetName(), self, triggered=partial(removeTag, desc, tag))
					removeTagsSubMenu.addAction(action)

			if addTagSubMenu or removeTagsSubMenu:	
				menu.addSeparator()
			if addTagSubMenu:
				menu.addMenu(addTagSubMenu)
			if removeTagsSubMenu:
				menu.addMenu(removeTagsSubMenu)

			menu.addSeparator()
			menu.addAction(QAction("Edit Note", self, triggered=partial(self.mainWindow._showNoteEditorDialog, desc)))
			##############################
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