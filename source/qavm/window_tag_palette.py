from __future__ import annotations
from enum import IntEnum
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtWidgets import (
	QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
	QScrollArea, QMessageBox,
)

from qavm.manager_tags import TagsManager, BaseTagImpl, TagScope
from qavm.manager_plugin import PluginManager, UID
from qavm.utils_gui import FlowLayout
from qavm.utils_widgets import TagBubbleWidget, TAG_MIME_TYPE
from qavm.window_tag_editor import TagEditorDialog, EMPTY_OPTION_LABEL

if TYPE_CHECKING:
	from qavm.window_main import MainWindow

import qavm.logs as logs
logger = logs.logger


class ScopePreset(IntEnum):
	ALL = 0
	ACTIVE_PLUGIN = 1
	ACTIVE_SOFTWARE = 2
	CUSTOM = 3


def _viewMatches(scopeView: str, filterView: str) -> bool:
	""" Returns True if a scope's viewUID is compatible with the selected view filter. """
	if not scopeView or not filterView:
		return True
	if UID.IsDataPathWildcard(scopeView):
		return UID.MatchDataPath(scopeView, filterView)
	if UID.IsDataPathWildcard(filterView):
		return UID.MatchDataPath(filterView, scopeView)
	return scopeView == filterView


def _tagMatchesFilter(tag: BaseTagImpl, pluginFilter: str, softwareFilter: str, viewFilter: str) -> bool:
	""" Permissive palette filter: a non-empty filter dimension constrains, an empty one is a wildcard.
	A tag with no scopes is global and always shown. """
	scopes: list[TagScope] = tag.GetScopes()
	if not scopes:
		return True
	for scope in scopes:
		if pluginFilter and scope.pluginID and scope.pluginID != pluginFilter:
			continue
		if softwareFilter and scope.softwareID and scope.softwareID != softwareFilter:
			continue
		if viewFilter and not _viewMatches(scope.viewUID, viewFilter):
			continue
		return True
	return False


class _TagFlowContainer(QWidget):
	""" Holds the tag bubbles in a FlowLayout and accepts drops of tag bubbles to reorder them. """
	reorderRequested = pyqtSignal(str, int)  # (draggedTagUID, targetIndex)

	def __init__(self, parent: QWidget | None = None):
		super().__init__(parent)
		self.flowLayout: FlowLayout = FlowLayout(self, margin=6, hspacing=6, vspacing=6)
		self.setAcceptDrops(True)

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
		draggedUID: str = bytes(event.mimeData().data(TAG_MIME_TYPE).data()).decode('utf-8')
		targetIndex: int = self._computeDropIndex(event.position().toPoint())
		self.reorderRequested.emit(draggedUID, targetIndex)
		event.acceptProposedAction()

	def _computeDropIndex(self, pos: QPoint) -> int:
		""" Computes the insertion index in reading order based on the drop position. """
		index: int = 0
		for i in range(self.flowLayout.count()):
			item = self.flowLayout.itemAt(i)
			if item is None:
				continue
			widget = item.widget()
			if widget is None:
				continue
			geo = widget.geometry()
			center = geo.center()
			# 'before' if on an earlier row, or same row and left of center
			if center.y() < pos.y() - geo.height() / 2:
				index = i + 1
			elif abs(center.y() - pos.y()) <= geo.height() and center.x() < pos.x():
				index = i + 1
		return index


class TagsPaletteWidget(QWidget):
	""" Palette listing available tags as colorful bubbles, with management and scope filtering. """
	def __init__(self, mainWindow: 'MainWindow', parent: QWidget | None = None) -> None:
		super().__init__(parent)

		app = QApplication.instance()
		self.tagsManager: TagsManager = app.GetTagsManager()
		self.pluginManager: PluginManager = app.GetPluginManager()
		self.mainWindow: 'MainWindow' = mainWindow

		self.setWindowTitle("Tags")

		self._pluginOptions, self._softwareOptions, self._viewOptions = self._collectScopeOptions()

		mainLayout = QVBoxLayout(self)
		mainLayout.setContentsMargins(6, 6, 6, 6)

		mainLayout.addLayout(self._buildFilterBar())

		self.container: _TagFlowContainer = _TagFlowContainer()
		self.container.reorderRequested.connect(self._onReorderRequested)

		scrollArea = QScrollArea()
		scrollArea.setWidgetResizable(True)
		scrollArea.setWidget(self.container)
		mainLayout.addWidget(scrollArea, 1)

		self._applyPreset(ScopePreset.ACTIVE_SOFTWARE)
		self.RefreshTags()

	# region Setup
	def _buildFilterBar(self) -> QVBoxLayout:
		layout = QVBoxLayout()

		topRow = QHBoxLayout()
		topRow.addWidget(QLabel("Filter:"))
		self.presetCombo: QComboBox = QComboBox()
		self.presetCombo.addItem("All", ScopePreset.ALL)
		self.presetCombo.addItem("Active Plugin(s)", ScopePreset.ACTIVE_PLUGIN)
		self.presetCombo.addItem("Active Software(s)", ScopePreset.ACTIVE_SOFTWARE)
		self.presetCombo.addItem("Custom", ScopePreset.CUSTOM)
		self.presetCombo.currentIndexChanged.connect(self._onPresetChanged)
		topRow.addWidget(self.presetCombo, 1)

		self.addTagButton: QPushButton = QPushButton("+ Add Tag")
		self.addTagButton.clicked.connect(self._onAddTag)
		topRow.addWidget(self.addTagButton)
		layout.addLayout(topRow)

		dropdownRow = QHBoxLayout()
		self.pluginCombo: QComboBox = self._makeFilterCombo(self._pluginOptions)
		self.softwareCombo: QComboBox = self._makeFilterCombo(self._softwareOptions)
		self.viewCombo: QComboBox = self._makeFilterCombo(self._viewOptions)
		dropdownRow.addWidget(QLabel("Plugin:"))
		dropdownRow.addWidget(self.pluginCombo, 1)
		dropdownRow.addWidget(QLabel("Software:"))
		dropdownRow.addWidget(self.softwareCombo, 1)
		dropdownRow.addWidget(QLabel("View:"))
		dropdownRow.addWidget(self.viewCombo, 1)
		layout.addLayout(dropdownRow)

		return layout

	def _makeFilterCombo(self, options: list[str]) -> QComboBox:
		combo = QComboBox()
		combo.addItem(EMPTY_OPTION_LABEL, '')
		for opt in options:
			if opt:
				combo.addItem(opt, opt)
		combo.currentIndexChanged.connect(self._onDropdownChanged)
		return combo

	def _collectScopeOptions(self) -> tuple[list[str], list[str], list[str]]:
		pluginOptions: set[str] = set()
		softwareOptions: set[str] = set()
		viewOptions: set[str] = set()
		for pluginID, softwareID, swHandler in self.pluginManager.GetSoftwareHandlers():
			pluginOptions.add(pluginID)
			softwareOptions.add(softwareID)
			for dataPath in swHandler.GetTileBuilderClasses().keys():
				viewOptions.add(dataPath)
			for dataPath in swHandler.GetTableBuilderClasses().keys():
				viewOptions.add(dataPath)
			for dataPath in swHandler.GetCustomViewClasses().keys():
				viewOptions.add(dataPath)
		viewOptions.update({'views/tiles/*', 'views/table/*', 'views/custom/*'})
		return sorted(pluginOptions), sorted(softwareOptions), sorted(viewOptions)
	# endregion

	# region Active context
	def _getActiveContext(self) -> tuple[str, str]:
		""" Returns (pluginID, softwareID) of the currently active view tab, or ('', '') if unavailable. """
		try:
			tabsWidget = getattr(self.mainWindow, 'tabsWidget', None)
			if tabsWidget is None:
				return '', ''
			current = tabsWidget.currentWidget()
			swHandler = getattr(current, 'swHandler', None)
			if swHandler is None:
				return '', ''
			return swHandler.pluginID, swHandler.GetID()
		except Exception as e:
			logger.warning(f"Failed to resolve active tag context: {e}")
			return '', ''

	def _setCombo(self, combo: QComboBox, value: str):
		idx = combo.findData(value)
		if idx < 0:
			idx = 0  # fall back to '<all>'
		combo.blockSignals(True)
		combo.setCurrentIndex(idx)
		combo.blockSignals(False)

	def _applyPreset(self, preset: ScopePreset):
		self.presetCombo.blockSignals(True)
		self.presetCombo.setCurrentIndex(self.presetCombo.findData(preset))
		self.presetCombo.blockSignals(False)

		pluginID, softwareID = self._getActiveContext()
		if preset == ScopePreset.ALL:
			self._setCombo(self.pluginCombo, '')
			self._setCombo(self.softwareCombo, '')
			self._setCombo(self.viewCombo, '')
		elif preset == ScopePreset.ACTIVE_PLUGIN:
			self._setCombo(self.pluginCombo, pluginID)
			self._setCombo(self.softwareCombo, '')
			self._setCombo(self.viewCombo, '')
		elif preset == ScopePreset.ACTIVE_SOFTWARE:
			self._setCombo(self.pluginCombo, pluginID)
			self._setCombo(self.softwareCombo, softwareID)
			self._setCombo(self.viewCombo, '')
		# CUSTOM: leave dropdowns as-is
	# endregion

	# region Events
	def _onPresetChanged(self):
		preset: ScopePreset = self.presetCombo.currentData()
		if preset != ScopePreset.CUSTOM:
			self._applyPreset(preset)
		self.RefreshTags()

	def _onDropdownChanged(self):
		# Manually changing a dropdown switches the preset selector to Custom.
		self.presetCombo.blockSignals(True)
		self.presetCombo.setCurrentIndex(self.presetCombo.findData(ScopePreset.CUSTOM))
		self.presetCombo.blockSignals(False)
		self.RefreshTags()

	def _onAddTag(self):
		dialog = TagEditorDialog(None, self)
		if dialog.exec():
			self.RefreshTags()

	def _onEditTag(self, tag: BaseTagImpl):
		dialog = TagEditorDialog(tag, self)
		if dialog.exec():
			self.RefreshTags()

	def _onDeleteTag(self, tag: BaseTagImpl):
		reply = QMessageBox.question(
			self, "Delete Tag",
			f"Delete tag '{tag.GetName()}'?\nIt will be removed from all items it is assigned to.",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		if reply == QMessageBox.StandardButton.Yes:
			self.tagsManager.DeleteTag(tag)
			self.RefreshTags()

	def _onReorderRequested(self, draggedUID: str, targetIndex: int):
		orderedUIDs: list[str] = [tag.GetUID() for tag in self.tagsManager.GetTagsOrdered()]
		if draggedUID not in orderedUIDs:
			return
		currentIndex: int = orderedUIDs.index(draggedUID)
		orderedUIDs.pop(currentIndex)
		# Adjust target index if removal shifted it
		if currentIndex < targetIndex:
			targetIndex -= 1
		targetIndex = max(0, min(targetIndex, len(orderedUIDs)))
		orderedUIDs.insert(targetIndex, draggedUID)
		self.tagsManager.ReorderTags(orderedUIDs)
		self.RefreshTags()
	# endregion

	def OnActiveContextChanged(self):
		""" Reapplies the active-context-based preset (if selected) and refreshes the displayed tags. """
		preset: ScopePreset = self.presetCombo.currentData()
		if preset != ScopePreset.CUSTOM:
			self._applyPreset(preset)
		self.RefreshTags()

	def RefreshTags(self):
		# Clear existing bubbles
		flow = self.container.flowLayout
		while flow.count():
			item = flow.takeAt(0)
			if item is None:
				continue
			w = item.widget()
			if w is not None:
				w.setParent(None)
				w.deleteLater()

		pluginFilter: str = self.pluginCombo.currentData() or ''
		softwareFilter: str = self.softwareCombo.currentData() or ''
		viewFilter: str = self.viewCombo.currentData() or ''

		for tag in self.tagsManager.GetTagsOrdered():
			if not _tagMatchesFilter(tag, pluginFilter, softwareFilter, viewFilter):
				continue
			bubble = TagBubbleWidget(tag)
			bubble.editRequested.connect(self._onEditTag)
			bubble.deleteRequested.connect(self._onDeleteTag)
			bubble.setFixedWidth(bubble.sizeHint().width())
			flow.addWidget(bubble)
