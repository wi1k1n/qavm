from __future__ import annotations
import uuid
from enum import IntEnum
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QMimeData
from PyQt6.QtWidgets import (
	QApplication, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
	QScrollArea, QMessageBox,
)
from PyQt6.QtGui import QAction, QColor, QDrag, QPainter, QPixmap, QMouseEvent

from qavm.manager_tags import TagsManager, BaseTagImpl, TagScope
from qavm.manager_plugin import PluginManager, UID
from qavm.qavmapi.gui import _PickContrastingTextColor, GetThemeData, HoverFadeTooltipMixin, PlainTextToTooltipHtml, QColor
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

		textColor: QColor = _PickContrastingTextColor(bgColor)
		self.setStyleSheet(f'color: {textColor.name()};')

		self._ctrlHeldOnPress: bool = False

		self._InitHoverTooltip(persistentTooltip=True)

	def GetTag(self) -> BaseTagImpl:
		return self.tag

	# region Drag
	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			self._dragStartPos = event.pos()
			self._ctrlHeldOnPress = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
		super().mousePressEvent(event)

	def mouseReleaseEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			# Ctrl+click (released without having started a drag) → open editor
			if self._ctrlHeldOnPress and self._dragStartPos is not None:
				self.editRequested.emit(self.tag)
			self._dragStartPos = None
			self._ctrlHeldOnPress = False
		super().mouseReleaseEvent(event)

	def mouseMoveEvent(self, event):
		if not self._draggable or self._dragStartPos is None:
			return super().mouseMoveEvent(event)
		if not (event.buttons() & Qt.MouseButton.LeftButton):
			return super().mouseMoveEvent(event)
		if (event.pos() - self._dragStartPos).manhattanLength() < QApplication.startDragDistance():
			return super().mouseMoveEvent(event)
		
		

		# Drag threshold exceeded — commit to dragging; prevent editRequested on release.
		self._dragStartPos = None
		self._ctrlHeldOnPress = False

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
		menu.addAction(QAction("Edit Tag", menu, triggered=lambda: self.editRequested.emit(self.tag)))
		menu.addAction(QAction("Delete Tag", menu, triggered=lambda: self.deleteRequested.emit(self.tag)))
		menu.exec(event.globalPos())
	# endregion

class _TagFlowContainer(QWidget):
	""" Holds the tag bubbles in a FlowLayout and accepts drops of tag bubbles to reorder them. """
	reorderRequested = pyqtSignal(str, int)  # (draggedTagUID, targetIndex)
	cloneRequested = pyqtSignal(str, int)    # (draggedTagUID, targetIndex) — Ctrl+drop clones the tag

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

		# Filter dropdowns — visible only when preset is Custom, stacked vertically
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
