from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMenu, QWidget, QApplication
from PyQt6.QtGui import QAction, QColor, QDrag, QCursor
from PyQt6.QtCore import Qt, QMimeData, QPoint, QTimer, pyqtSignal

from qavm.manager_tags import BaseTagImpl, TagScope
from qavm.qavmapi import BaseDescriptor
from qavm.utils_gui import BubbleWidget, FadeTooltip

if TYPE_CHECKING:
	from qavm.window_main import MainWindow
	from qavm.manager_descriptor_data import DescriptorDataImpl

import qavm.logs as logs
logger = logs.logger

# Custom MIME type used when dragging a tag bubble onto a drop target (table row / tile).
TAG_MIME_TYPE: str = 'application/x-qavm-tag-uid'


def AssignTagUIDToDescriptor(desc: BaseDescriptor, tagUID: str) -> bool:
	""" Assigns the tag with the given UID to the descriptor and notifies listeners. Returns True on success. """
	app = QApplication.instance()
	tagsManager = app.GetTagsManager()
	tag: BaseTagImpl | None = tagsManager.GetTag(tagUID)
	if tag is None:
		logger.warning(f"Cannot assign tag: unknown tag UID {tagUID}")
		return False
	tagsManager.AssignTag(desc, tag)
	desc.descDataUpdated.emit()
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

	def __init__(self, tag: BaseTagImpl, draggable: bool = True, contextMenuEnabled: bool = True, parent: QWidget | None = None):
		bgColor: QColor | None = QColor(tag.GetColor()) if tag.GetColor() else None
		super().__init__(tag.GetName(), bgColor=bgColor, rounding=14, margin=7)
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

		self._hoverTimer: QTimer = QTimer(self)
		self._hoverTimer.setSingleShot(True)
		self._hoverTimer.timeout.connect(self._showTooltip)

	def GetTag(self) -> BaseTagImpl:
		return self.tag

	# region Drag
	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			self._dragStartPos = event.pos()
		super().mousePressEvent(event)

	def mouseMoveEvent(self, event):
		if not self._draggable or self._dragStartPos is None:
			return super().mouseMoveEvent(event)
		if not (event.buttons() & Qt.MouseButton.LeftButton):
			return super().mouseMoveEvent(event)
		if (event.pos() - self._dragStartPos).manhattanLength() < QApplication.startDragDistance():
			return super().mouseMoveEvent(event)

		self._hoverTimer.stop()
		if self._tooltip:
			self._tooltip.hideWithFade()

		drag: QDrag = QDrag(self)
		mimeData: QMimeData = QMimeData()
		mimeData.setData(TAG_MIME_TYPE, self.tag.GetUID().encode('utf-8'))
		drag.setMimeData(mimeData)
		drag.setPixmap(self.grab())
		drag.setHotSpot(event.pos())
		drag.exec(Qt.DropAction.CopyAction)
		self._dragStartPos = None
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
		colorStr: str = self.tag.GetColor() or '#000000'
		swatch: str = f'<span style="background-color:{colorStr};">&nbsp;&nbsp;&nbsp;</span>'
		lines: list[str] = [
			f'<b>{self.tag.GetName()}</b> {swatch} <code>{colorStr}</code>',
		]
		scopes: list[TagScope] = self.tag.GetScopes()
		if not scopes:
			lines.append('<i>Scope: global (all)</i>')
		else:
			lines.append('<i>Scopes:</i>')
			for scope in scopes:
				parts: list[str] = []
				parts.append(f'plugin: {scope.pluginID or "*"}')
				parts.append(f'software: {scope.softwareID or "*"}')
				parts.append(f'view: {scope.viewUID or "*"}')
				lines.append('&bull; ' + ', '.join(parts))
		return '<br>'.join(lines)
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
		desc.descDataUpdated.emit()
	def removeTag(desc: BaseDescriptor, tag: BaseTagImpl):
		logger.info(f"Removing tag {tag.GetName()} from descriptor {desc.GetUID()}")
		mainWindow.tagsManager.RemoveTag(desc, tag)
		desc.descDataUpdated.emit()

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
