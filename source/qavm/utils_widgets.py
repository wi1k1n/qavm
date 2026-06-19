from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMenu, QWidget, QApplication
from PyQt6.QtGui import QAction, QColor, QDrag, QCursor, QPainter, QPixmap
from PyQt6.QtCore import Qt, QMimeData, QPoint, QTimer, pyqtSignal

from qavm.manager_tags import BaseTagImpl, TagScope
from qavm.qavmapi import BaseDescriptor
from qavm.utils_gui import BubbleWidget, FadeTooltip
from qavm.qavmapi.gui import GetThemeData

if TYPE_CHECKING:
	from qavm.window_main import MainWindow
	from qavm.manager_descriptor_data import DescriptorDataImpl

import qavm.logs as logs
logger = logs.logger

# Custom MIME type used when dragging a tag bubble onto a drop target (table row / tile).
TAG_MIME_TYPE: str = 'application/x-qavm-tag-uid'


def _makeReorderCursorPixmap() -> QPixmap:
	""" Returns a small 'grip lines' pixmap used as the drag cursor for reorder (MoveAction) drags. """
	size = 20
	pm = QPixmap(size, size)
	pm.fill(Qt.GlobalColor.transparent)
	painter = QPainter(pm)
	painter.setRenderHint(QPainter.RenderHint.Antialiasing)
	painter.setPen(QColor(72, 72, 72))
	cx, cy, half = size // 2, size // 2, 6
	for dy in (-4, 0, 4):
		painter.drawLine(cx - half, cy + dy, cx + half, cy + dy)
	painter.end()
	return pm


def AssignTagUIDToDescriptor(desc: BaseDescriptor, tagUID: str) -> bool:
	""" Assigns the tag with the given UID to the descriptor and notifies listeners. Returns True on success. """
	app = QApplication.instance()
	tagsManager = app.GetTagsManager()
	tag: BaseTagImpl | None = tagsManager.GetTag(tagUID)
	if tag is None:
		logger.warning(f"Cannot assign tag: unknown tag UID {tagUID}")
		return False
	tagsManager.AssignTag(desc, tag)
	return True


def _PickContrastingTextColor(bgColor: QColor | None) -> QColor:
	""" Returns black or white depending on the perceived luminance of the background color. """
	if bgColor is None:
		return QColor('black')
	# Perceived luminance (ITU-R BT.601)
	luminance: float = (0.299 * bgColor.red() + 0.587 * bgColor.green() + 0.114 * bgColor.blue()) / 255.0
	return QColor('black') if luminance > 0.55 else QColor('white')


class TagBubbleWidget(BubbleWidget):
	""" A colorful bubble representing a tag. Supports drag (to assign), hover tooltip and a context menu. """
	editRequested = pyqtSignal(object)    # emits BaseTagImpl
	deleteRequested = pyqtSignal(object)  # emits BaseTagImpl
	
	BUBBLE_ROUNDING: float = 17.0
	BUBBLE_MARGIN: int = 11

	def __init__(self, tag: BaseTagImpl, draggable: bool = True, contextMenuEnabled: bool = True, parent: QWidget | None = None):
		bgColor: QColor | None = QColor(tag.GetColor()) if tag.GetColor() else None
		super().__init__(tag.GetName(), bgColor=bgColor, rounding=self.BUBBLE_ROUNDING, margin=self.BUBBLE_MARGIN)
		if parent is not None:
			self.setParent(parent)

		self.tag: BaseTagImpl = tag
		self._draggable: bool = draggable
		self._contextMenuEnabled: bool = contextMenuEnabled
		self._dragStartPos: QPoint | None = None
		self._tooltip: FadeTooltip | None = None

		textColor: QColor = _PickContrastingTextColor(bgColor)
		self.setStyleSheet(f'color: {textColor.name()};')

		self.setMouseTracking(True)

		self._ctrlHeldOnPress: bool = False

		self._hoverTimer: QTimer = QTimer(self)
		self._hoverTimer.setSingleShot(True)
		self._hoverTimer.timeout.connect(self._showTooltip)

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

		self._hoverTimer.stop()
		if self._tooltip:
			self._tooltip.hideWithFade()

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
		self._hoverTimer.start(500)
		super().enterEvent(event)

	def leaveEvent(self, event):
		self._hoverTimer.stop()
		if self._tooltip:
			self._tooltip.hideWithFade()
		super().leaveEvent(event)

	def _showTooltip(self):
		if self._tooltip is None:
			self._tooltip = FadeTooltip(self)
		self._tooltip.showText(self._buildTooltipHtml(), QCursor.pos() + QPoint(14, 18))

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
			rows.append(f'<tr><td colspan="2" style="padding-top:6px; color:{colorPrimary.name()};">{description}</td></tr>')

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
		self._hoverTimer.stop()
		if self._tooltip:
			self._tooltip.hideWithFade()
		menu: QMenu = QMenu(self)
		menu.addAction(QAction("Edit Tag", menu, triggered=lambda: self.editRequested.emit(self.tag)))
		menu.addAction(QAction("Delete Tag", menu, triggered=lambda: self.deleteRequested.emit(self.tag)))
		menu.exec(event.globalPos())
	# endregion


def PopulateContextMenuTagsAndNotes(menu: QMenu, desc: BaseDescriptor, mainWindow: 'MainWindow', parent: QWidget, pluginID: str, softwareID: str, viewUID: str):
	""" Adds the shared 'Assign Tag' / 'Remove Tag' submenus and the 'Edit Note' action to the given context menu.

	Only tags whose scopes are applicable to the given plugin/software/view context are offered in the 'Assign Tag' submenu. """
	def assignTag(tag: BaseTagImpl):
		logger.info(f"Assigning tag {tag.GetName()} to descriptor {desc.GetUID()}")
		mainWindow.tagsManager.AssignTag(desc, tag)
	def removeTag(desc: BaseDescriptor, tag: BaseTagImpl):
		logger.info(f"Removing tag {tag.GetName()} from descriptor {desc.GetUID()}")
		mainWindow.tagsManager.RemoveTag(desc, tag)

	descData: DescriptorDataImpl = mainWindow.descDataManager.GetDescriptorData(desc)
	descTagsUIDs: list[str] = descData.tags

	addTagSubMenu: QMenu | None = None
	if tags := mainWindow.tagsManager.GetTags().values():
		addTagSubMenu = QMenu("Assign Tag", parent)
		for tag in tags:
			if tag.GetUID() in descTagsUIDs:
				continue
			if not tag.IsApplicableInContext(pluginID, softwareID, viewUID):
				continue
			action = QAction(tag.GetName(), parent, triggered=partial(assignTag, tag))
			addTagSubMenu.addAction(action)
		if addTagSubMenu.isEmpty():
			addTagSubMenu = None

	removeTagsSubMenu: QMenu | None = None
	if descTags := [mainWindow.tagsManager.GetTag(tagUID) for tagUID in descTagsUIDs if mainWindow.tagsManager.GetTag(tagUID)]:
		removeTagsSubMenu = QMenu("Remove Tag", parent)
		for tag in descTags:
			action = QAction(tag.GetName(), parent, triggered=partial(removeTag, desc, tag))
			removeTagsSubMenu.addAction(action)

	if addTagSubMenu or removeTagsSubMenu:
		menu.addSeparator()
	if addTagSubMenu:
		menu.addMenu(addTagSubMenu)
	if removeTagsSubMenu:
		menu.addMenu(removeTagsSubMenu)

	menu.addSeparator()
	menu.addAction(QAction("Edit Note", parent, triggered=partial(mainWindow._showNoteEditorDialog, desc)))
