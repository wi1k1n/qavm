from __future__ import annotations
import uuid
from enum import IntEnum
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QMimeData
from PyQt6.QtWidgets import (
	QApplication, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
	QScrollArea, QMessageBox, QDialog, QTreeWidget, QTreeWidgetItem, QDialogButtonBox,
)
from PyQt6.QtGui import QAction, QColor, QDrag, QPainter, QPixmap, QMouseEvent

from qavm.qavmapi import BaseDescriptor
from qavm.manager_tags import TagsManager, BaseTagImpl, TagScope
from qavm.manager_descriptor_data import DescriptorDataManager
from qavm.manager_plugin import PluginManager, UID
from qavm.qavmapi.gui import GetThemeData, HoverFadeTooltipMixin, PlainTextToTooltipHtml, PickContrastingTextColor
from qavm.utils_gui import BubbleWidget, FlowLayout
from qavm.utils_widgets import TAG_MIME_TYPE
from qavm.window_tag_editor import TagEditorDialog, OpenTagEditorDialog, EMPTY_OPTION_LABEL

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

class TagBubbleWidget(HoverFadeTooltipMixin, BubbleWidget):
	""" A colorful bubble representing a tag. Supports drag (to assign), hover tooltip and a context menu. """
	editRequested = pyqtSignal(object)    # emits BaseTagImpl
	deleteRequested = pyqtSignal(object)  # emits BaseTagImpl
	
	BUBBLE_ROUNDING: float = 17.0
	BUBBLE_MARGIN: int = 11
	TOOLTIP_DELAY_MS: int = 500

	def __init__(self, tag: BaseTagImpl, draggable: bool = True, contextMenuEnabled: bool = True, parent: QWidget | None = None):
		bgColor: QColor | None = QColor(tag.GetColor()) if tag.GetColor() else None
		super().__init__(tag.GetName(), bgColor=bgColor, rounding=self.BUBBLE_ROUNDING, margin=self.BUBBLE_MARGIN)
		if parent is not None:
			self.setParent(parent)

		self.tag: BaseTagImpl = tag
		self._draggable: bool = draggable
		self._contextMenuEnabled: bool = contextMenuEnabled
		self._dragStartPos: QPoint | None = None

		textColor: QColor = PickContrastingTextColor(bgColor)
		self.setStyleSheet(f'color: {textColor.name()};')

		self._ctrlHeldOnPress: bool = False
		self._shiftHeldOnPress: bool = False

		self._InitHoverTooltip(persistentTooltip=True)

	def GetTag(self) -> BaseTagImpl:
		return self.tag

	def _CollectTagUsages(self) -> list[tuple[str, str, list[BaseDescriptor]]]:
		""" Returns [(pluginName, softwareName, [descriptors])] for every loaded descriptor that has this tag assigned. """
		app = QApplication.instance()
		descDataManager: DescriptorDataManager = app.GetDescriptorDataManager()
		pluginManager: PluginManager = app.GetPluginManager()
		tagUID: str = self.tag.GetUID()
		results: list[tuple[str, str, list[BaseDescriptor]]] = []
		for swHandler, descsMap in app.softwareDescriptors.items():
			plugin = pluginManager.GetPlugin(swHandler.pluginID)
			pluginName: str = plugin.GetName() if plugin else swHandler.pluginID
			softwareName: str = swHandler.GetName()
			matched: list[BaseDescriptor] = []
			for descs in descsMap.values():
				for desc in descs:
					if tagUID in descDataManager.GetDescriptorData(desc).tags:
						matched.append(desc)
			if matched:
				results.append((pluginName, softwareName, matched))
		return results

	def _CountTagUsages(self) -> int:
		""" Returns the total number of loaded descriptors that have this tag assigned. """
		return sum(len(descs) for _, _, descs in self._CollectTagUsages())

	# region Drag
	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			self._dragStartPos = event.pos()
			self._ctrlHeldOnPress = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
			self._shiftHeldOnPress = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
		super().mousePressEvent(event)

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			# Shift+click (released without having started a drag) → prompt to delete
			if self._shiftHeldOnPress and self._dragStartPos is not None:
				self._CancelTooltip()
				self.deleteRequested.emit(self.tag)
			# Ctrl+click (released without having started a drag) → open editor
			elif self._ctrlHeldOnPress and self._dragStartPos is not None:
				self.editRequested.emit(self.tag)
			self._dragStartPos = None
			self._ctrlHeldOnPress = False
			self._shiftHeldOnPress = False
		super().mouseReleaseEvent(event)

	def mouseDoubleClickEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			self._CancelTooltip()
			self._dragStartPos = None
			self._ctrlHeldOnPress = False
			self._shiftHeldOnPress = False
			self.editRequested.emit(self.tag)
			event.accept()
			return
		super().mouseDoubleClickEvent(event)

	def mouseMoveEvent(self, event):
		if not self._draggable or self._dragStartPos is None:
			return super().mouseMoveEvent(event)
		if not (event.buttons() & Qt.MouseButton.LeftButton):
			return super().mouseMoveEvent(event)
		if (event.pos() - self._dragStartPos).manhattanLength() < QApplication.startDragDistance():
			return super().mouseMoveEvent(event)
		
		

		# Drag threshold exceeded - commit to dragging; prevent editRequested on release.
		self._dragStartPos = None
		self._ctrlHeldOnPress = False
		self._shiftHeldOnPress = False

		self._CancelTooltip()

		drag: QDrag = QDrag(self)
		mimeData: QMimeData = QMimeData()
		mimeData.setData(TAG_MIME_TYPE, self.tag.GetUID().encode('utf-8'))
		drag.setMimeData(mimeData)
		drag.setPixmap(self.grab())
		drag.setHotSpot(event.pos())
		# MoveAction = reorder (grip-lines cursor); CopyAction = clone (Qt's built-in + cursor when Ctrl held)
		# drag.setDragCursor(_makeReorderCursorPixmap(), Qt.DropAction.MoveAction)
		drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
	# endregion

	# region Tooltip
	def enterEvent(self, event):
		self._ScheduleTooltip()
		super().enterEvent(event)

	def _GetTooltipHtml(self) -> str | None:
		return self._buildTooltipHtml()

	def _buildTooltipHtml(self) -> str:
		def _append_scope_rows(rows: list[str], scopes: list[TagScope], colorPrimary: QColor):
			"""Append scope-related rows into the provided rows list."""
			if not scopes:
				rows.append(f'<tr><td colspan="2" style="padding-top:6px; color:{colorPrimary.name()};"><i>Scope: global (&lt;all&gt;)</i></td></tr>')
				return
			# Scopes header
			def getScopeLine(title: str, value: str) -> str:
				return f'<tr><td style="padding-right:10px; white-space:nowrap; color:{colorPrimary.name()};">{title}</td><td colspan="2" style="padding-left:6px;">{value or "&lt;all&gt;"}</td></tr>'
			
			rows.append(f'<tr><td colspan="2" style="padding-top:6px; color:{colorPrimary.name()};"><i>Scopes:</i></td></tr>')
			for scope in scopes:
				rows.append(getScopeLine("plugin", scope.pluginID))
				rows.append(getScopeLine("software", scope.softwareID))
				rows.append(getScopeLine("view", scope.viewUID))
				# spacer between scopes
				rows.append('<tr><td colspan="2" style="height:6px"></td></tr>')
				
		themeData = GetThemeData()
		colorPrimary = QColor(themeData.get('primaryColor', '#ffffff')) if themeData else QColor('#ffffff')
		colorSecondary = QColor(themeData.get('secondaryColor', '#0f0f0f')) if themeData else QColor('#0f0f0f')

		rows: list[str] = []
		rows.append(f'<tr><td style="vertical-align:middle; font-weight:600;">{self.tag.GetName()}</td></tr>')

		# Optional description spans full width
		if description := self.tag.GetDescription():
			rows.append(f'<tr><td colspan="2" style="padding-top:6px; color:{colorPrimary.name()};">{PlainTextToTooltipHtml(description)}</td></tr>')

		scopes: list[TagScope] = self.tag.GetScopes()
		_append_scope_rows(rows, scopes, colorPrimary)

		# Number of descriptors that currently have this tag assigned.
		usageCount: int = self._CountTagUsages()
		rows.append(f'<tr><td colspan="2" style="padding-top:6px; color:{colorPrimary.name()};"><i>Usages: {usageCount}</i></td></tr>')

		# Use theme: table background = secondary, text = primary. Keep swatch color intact.
		table_style = f'border-collapse:collapse; margin:0; background-color:{colorSecondary.name()}; color:{colorPrimary.name()}; padding:6px; border-radius:6px;'
		table_html = f'<table style="{table_style}">' + ''.join(rows) + '</table>'
		return table_html
	# endregion

	# region Context menu
	def contextMenuEvent(self, event):
		if not self._contextMenuEnabled:
			return super().contextMenuEvent(event)
		self._CancelTooltip()
		menu: QMenu = QMenu(self)
		menu.addAction(QAction("Show usage", menu, triggered=self._ShowUsage))
		menu.addSeparator()
		menu.addAction(QAction("Edit Tag", menu, triggered=lambda: self.editRequested.emit(self.tag)))
		menu.addAction(QAction("Delete Tag", menu, triggered=lambda: self.deleteRequested.emit(self.tag)))
		menu.exec(event.globalPos())

	def _ShowUsage(self):
		""" Opens a modal dialog listing every descriptor (grouped by plugin/software) that has this tag assigned. """
		usages: list[tuple[str, str, list[BaseDescriptor]]] = self._CollectTagUsages()
		dialog = TagUsageDialog(self.tag, usages, self)
		dialog.exec()
	# endregion

class TagUsageDialog(QDialog):
	""" Modal dialog that lists every descriptor (grouped by plugin/software) that has a given tag assigned. """
	def __init__(self, tag: BaseTagImpl, usages: list[tuple[str, str, list[BaseDescriptor]]], parent: QWidget | None = None):
		super().__init__(parent)
		self.setWindowTitle(f"Tag Usage [{tag.GetName()}]")
		self.setModal(True)
		self.resize(480, 420)

		layout = QVBoxLayout(self)

		themeData = GetThemeData()
		colorPrimary = QColor(themeData.get('primaryColor', '#ffffff')) if themeData else QColor('#ffffff')

		totalCount: int = sum(len(descs) for _, _, descs in usages)
		summary = QLabel(
			f"Tag '{tag.GetName()}' is used by {totalCount} descriptor(s)."
			if totalCount else f"Tag '{tag.GetName()}' is not assigned to any descriptor."
		)
		summary.setWordWrap(True)
		summary.setStyleSheet(f'color: {colorPrimary.name()};')
		layout.addWidget(summary)

		tree = QTreeWidget()
		tree.setHeaderHidden(True)
		tree.setColumnCount(1)
		for pluginName, softwareName, descs in usages:
			groupItem = QTreeWidgetItem(tree, [f"[{pluginName}] {softwareName} ({len(descs)})"])
			groupItem.setExpanded(True)
			for desc in descs:
				childItem = QTreeWidgetItem(groupItem, [str(desc)])
				childItem.setToolTip(0, str(getattr(desc, 'dirPath', '')))
		tree.expandAll()
		layout.addWidget(tree, 1)

		buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
		buttonBox.rejected.connect(self.reject)
		buttonBox.accepted.connect(self.accept)
		layout.addWidget(buttonBox)


class _TagFlowContainer(QWidget):
	""" Holds the tag bubbles in a FlowLayout and accepts drops of tag bubbles to reorder them. """
	reorderRequested = pyqtSignal(str, int)  # (draggedTagUID, targetIndex)
	cloneRequested = pyqtSignal(str, int)    # (draggedTagUID, targetIndex) - Ctrl+drop clones the tag

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
		if event.dropAction() == Qt.DropAction.CopyAction:
			self.cloneRequested.emit(draggedUID, targetIndex)
		else:
			self.reorderRequested.emit(draggedUID, targetIndex)
		event.acceptProposedAction()

	def _computeDropIndex(self, pos: QPoint) -> int:
		""" Computes the insertion index in the global tag order based on the drop position.

		The flow layout only holds the currently visible (filtered) bubbles, so the layout
		index does not match the global tag order the reorder handlers operate on. We therefore
		derive the insertion index from the dropped-after tag's global order, not its layout index. """
		index: int = 0
		for i in range(self.flowLayout.count()):
			item = self.flowLayout.itemAt(i)
			if item is None:
				continue
			widget = item.widget()
			if not isinstance(widget, TagBubbleWidget):
				continue
			order: int = widget.GetTag().GetOrder()
			geo = widget.geometry()
			# Classify the drop relative to this widget's row using the widget's actual
			# vertical band, so the row test is consistent regardless of where inside the
			# row the cursor is released.
			if pos.y() > geo.bottom():
				# Drop is on a row below this widget → widget comes before the drop.
				index = order + 1
			elif pos.y() >= geo.top():
				# Same row as this widget → 'before' if the drop is right of its center.
				if pos.x() >= geo.center().x():
					index = order + 1
			# else: pos.y() < geo.top() → widget is on a row below the drop; never before it.
		return index


class TagsPaletteWidget(QWidget):
	""" Palette listing available tags as colorful bubbles, with management and scope filtering. """
	def __init__(self, mainWindow: 'MainWindow', parent: QWidget | None = None) -> None:
		super().__init__(parent)

		app = QApplication.instance()
		self.tagsManager: TagsManager = app.GetTagsManager()
		self.pluginManager: PluginManager = app.GetPluginManager()
		self.mainWindow: 'MainWindow' = mainWindow

		self.setWindowTitle("Tags Palette")

		self._pluginOptions, self._softwareOptions, self._viewOptions = self._collectScopeOptions()

		mainLayout = QVBoxLayout(self)
		mainLayout.setContentsMargins(6, 6, 6, 6)

		mainLayout.addLayout(self._buildFilterBar())

		self.container: _TagFlowContainer = _TagFlowContainer()
		self.container.reorderRequested.connect(self._onReorderRequested)
		self.container.cloneRequested.connect(self._onCloneTagAtIndex)

		# Refresh whenever tags change anywhere (palette, table/tiles tag bubbles, ...).
		self.tagsManager.tagsChanged.connect(self.RefreshTags)

		scrollArea = QScrollArea()
		scrollArea.setWidgetResizable(True)
		scrollArea.setWidget(self.container)
		mainLayout.addWidget(scrollArea, 1)

		self._applyPreset(ScopePreset.ACTIVE_SOFTWARE)
		self.filterSection.setVisible(False)  # ACTIVE_SOFTWARE is not Custom
		self.RefreshTags()

	# region Setup
	def _buildFilterBar(self) -> QVBoxLayout:
		layout = QVBoxLayout()
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(4)

		# Top row: Add Tag button + preset combo (always visible)
		topRow = QHBoxLayout()
		self.addTagButton: QPushButton = QPushButton("+ Add Tag")
		self.addTagButton.clicked.connect(self._onAddTag)
		topRow.addWidget(self.addTagButton)

		self.presetCombo: QComboBox = QComboBox()
		self.presetCombo.addItem("All", ScopePreset.ALL)
		self.presetCombo.addItem("Active Plugin(s)", ScopePreset.ACTIVE_PLUGIN)
		self.presetCombo.addItem("Active Software(s)", ScopePreset.ACTIVE_SOFTWARE)
		self.presetCombo.addItem("Custom", ScopePreset.CUSTOM)
		self.presetCombo.currentIndexChanged.connect(self._onPresetChanged)
		topRow.addWidget(self.presetCombo, 1)
		layout.addLayout(topRow)

		# Filter dropdowns - visible only when preset is Custom, stacked vertically
		self.filterSection: QWidget = QWidget()
		filterLayout = QVBoxLayout(self.filterSection)
		filterLayout.setContentsMargins(0, 2, 0, 2)
		filterLayout.setSpacing(4)

		self.pluginCombo: QComboBox = self._makeFilterCombo(self._pluginOptions)
		self.softwareCombo: QComboBox = self._makeFilterCombo(self._softwareOptions)
		self.viewCombo: QComboBox = self._makeFilterCombo(self._viewOptions)
		for labelText, combo in (("Plugin:", self.pluginCombo), ("Software:", self.softwareCombo), ("View:", self.viewCombo)):
			row = QHBoxLayout()
			row.addWidget(QLabel(labelText))
			row.addWidget(combo, 1)
			filterLayout.addLayout(row)

		layout.addWidget(self.filterSection)
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

	# region Persisted filter state
	def GetFilterState(self) -> dict:
		""" Returns the persistable filter state (preset + custom filter values). """
		preset = self.presetCombo.currentData()
		return {
			'preset': int(preset) if preset is not None else int(ScopePreset.ACTIVE_SOFTWARE),
			'plugin': self.pluginCombo.currentData() or '',
			'software': self.softwareCombo.currentData() or '',
			'view': self.viewCombo.currentData() or '',
		}

	def ApplyFilterState(self, state: dict):
		""" Restores a previously persisted filter state. """
		if not isinstance(state, dict):
			return
		try:
			preset: ScopePreset = ScopePreset(state.get('preset'))
		except (ValueError, TypeError):
			return

		if preset == ScopePreset.CUSTOM:
			self._setCombo(self.pluginCombo, state.get('plugin', '') or '')
			self._setCombo(self.softwareCombo, state.get('software', '') or '')
			self._setCombo(self.viewCombo, state.get('view', '') or '')
			self.presetCombo.blockSignals(True)
			self.presetCombo.setCurrentIndex(self.presetCombo.findData(ScopePreset.CUSTOM))
			self.presetCombo.blockSignals(False)
			self.filterSection.setVisible(True)
		else:
			self._applyPreset(preset)
			self.filterSection.setVisible(False)
		self.RefreshTags()
	# endregion

	# region Events
	def _onPresetChanged(self):
		preset: ScopePreset = self.presetCombo.currentData()
		if preset != ScopePreset.CUSTOM:
			self._applyPreset(preset)
		self.filterSection.setVisible(preset == ScopePreset.CUSTOM)
		self.RefreshTags()

	def _onDropdownChanged(self):
		# Manually changing a dropdown switches the preset selector to Custom.
		self.presetCombo.blockSignals(True)
		self.presetCombo.setCurrentIndex(self.presetCombo.findData(ScopePreset.CUSTOM))
		self.presetCombo.blockSignals(False)
		self.RefreshTags()

	def _onAddTag(self):
		pluginFilter: str = self.pluginCombo.currentData() or ''
		softwareFilter: str = self.softwareCombo.currentData() or ''
		viewFilter: str = self.viewCombo.currentData() or ''
		visibleTags: list[BaseTagImpl] = [
			tag for tag in self.tagsManager.GetTagsOrdered()
			if _tagMatchesFilter(tag, pluginFilter, softwareFilter, viewFilter)
		]
		initialScope: TagScope = TagScope(pluginFilter, softwareFilter, viewFilter)
		dialog = TagEditorDialog(None, self, existingTags=visibleTags, initialScope=initialScope)
		dialog.exec()  # palette refreshes via tagsManager.tagsChanged

	def _onEditTag(self, tag: BaseTagImpl):
		OpenTagEditorDialog(tag, self)  # palette refreshes via tagsManager.tagsChanged

	def _onDeleteTag(self, tag: BaseTagImpl):
		reply = QMessageBox.question(
			self, "Delete Tag",
			f"Delete tag '{tag.GetName()}'?\nIt will be removed from all items it is assigned to.",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		if reply == QMessageBox.StandardButton.Yes:
			self.tagsManager.DeleteTag(tag)  # palette refreshes via tagsManager.tagsChanged

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
		self.tagsManager.ReorderTags(orderedUIDs)  # palette refreshes via tagsManager.tagsChanged

	def _onCloneTagAtIndex(self, draggedUID: str, targetIndex: int):
		""" Ctrl+drop: create a new tag that is an exact copy of the dragged one, inserted at targetIndex. """
		sourceTag: BaseTagImpl | None = self.tagsManager.GetTag(draggedUID)
		if sourceTag is None:
			return
		# Snapshot the ordered list BEFORE the new tag exists, then splice the new UID in.
		orderedUIDs: list[str] = [tag.GetUID() for tag in self.tagsManager.GetTagsOrdered()]
		newUID: str = str(uuid.uuid4())
		targetIndex = max(0, min(targetIndex, len(orderedUIDs)))
		orderedUIDs.insert(targetIndex, newUID)
		cloneTag = BaseTagImpl(
			uid=newUID,
			name=sourceTag.GetName(),
			color=sourceTag.GetColor(),
			tagScopes=list(sourceTag.GetScopes()),
			description=sourceTag.GetDescription()
		)
		self.tagsManager.blockSignals(True)
		self.tagsManager.AddTag(cloneTag)        # appends at end; tagsChanged suppressed
		self.tagsManager.blockSignals(False)
		self.tagsManager.ReorderTags(orderedUIDs, True)  # moves clone to correct position, emits tagsChanged once
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
				w.hide()
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
