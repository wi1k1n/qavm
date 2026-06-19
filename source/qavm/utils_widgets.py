from functools import partial
from typing import TYPE_CHECKING, Callable

from PyQt6.QtWidgets import QMenu, QWidget, QApplication, QMessageBox
from PyQt6.QtGui import QAction, QColor, QDrag, QPainter, QPixmap, QMouseEvent
from PyQt6.QtCore import Qt, QMimeData, QPoint, QObject, QEvent, pyqtSignal

from qavm.manager_tags import BaseTagImpl, TagScope
from qavm.qavmapi import BaseDescriptor
from qavm.utils_gui import BubbleWidget
from qavm.qavmapi.gui import GetThemeData, ClickableSubmenuMenu, HoverFadeTooltipMixin

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

class _MenuActionClickFilter(QObject):
	""" Event filter that invokes a handler when a specific (submenu) action in a plain QMenu is clicked.

	Used to make the top-level 'Tags' submenu entry clickable when the host context menu is a plain
	QMenu (i.e. not a ClickableSubmenuMenu). The filter is parented to the menu so it lives as long as it. """
	def __init__(self, menu: QMenu, action: QAction, handler: Callable[[], None]):
		super().__init__(menu)
		self._menu: QMenu = menu
		self._action: QAction = action
		self._handler: Callable[[], None] = handler

	def eventFilter(self, obj: QObject, event: QEvent) -> bool:
		if obj is self._menu and isinstance(event, QMouseEvent) and event.type() == QEvent.Type.MouseButtonRelease:
			if self._menu.actionAt(event.position().toPoint()) is self._action:
				try:
					self._handler()
				except Exception:
					logger.exception("Tags menu click handler failed")
				self._menu.close()
				return True
		return False


def _InstallMenuActionClickHandler(menu: QMenu, action: QAction, handler: Callable[[], None]) -> None:
	""" Makes clicking on `action` (a submenu entry) inside `menu` invoke `handler`, working both for
	ClickableSubmenuMenu hosts and plain QMenu hosts. """
	if isinstance(menu, ClickableSubmenuMenu):
		menu.setClickHandler(action, handler)
		return
	menu.installEventFilter(_MenuActionClickFilter(menu, action, handler))


def PopulateContextMenuTagsAndNotes(menu: QMenu, desc: BaseDescriptor, mainWindow: 'MainWindow', parent: QWidget, pluginID: str, softwareID: str, viewUID: str, tagUnderCursor: BaseTagImpl | None = None):
	""" Adds a single clickable 'Tags' submenu and the 'Edit Note' action to the given context menu.

	The 'Tags' entry:
	- clicking it opens the Tags Palette window;
	- hovering it reveals a submenu with:
	  - 'Assign': a submenu of all tags assignable in the given plugin/software/view context;
	  - 'Remove': a submenu with 'Remove all' (prompts for confirmation), a separator, then every tag
	    currently assigned to the descriptor (regardless of scope);
	  - when `tagUnderCursor` is provided (the context menu was invoked over a tag bubble), a separator
	    followed by a '<TagName>' submenu offering 'Edit' and 'Delete' for that tag. """
	def assignTag(tag: BaseTagImpl):
		logger.info(f"Assigning tag {tag.GetName()} to descriptor {desc.GetUID()}")
		mainWindow.tagsManager.AssignTag(desc, tag)
	def removeTag(tag: BaseTagImpl):
		logger.info(f"Removing tag {tag.GetName()} from descriptor {desc.GetUID()}")
		mainWindow.tagsManager.RemoveTag(desc, tag)
	def removeAllTags(tags: list[BaseTagImpl]):
		reply = QMessageBox.question(
			parent, "Remove All Tags",
			f"Remove all {len(tags)} tag(s) from this item?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		if reply != QMessageBox.StandardButton.Yes:
			return
		for tag in tags:
			removeTag(tag)
	def openTagsPalette():
		mainWindow.tagsDock.show()
		mainWindow.tagsDock.raise_()
	def editTag(tag: BaseTagImpl):
		from qavm.window_tag_editor import OpenTagEditorDialog  # lazy import to avoid an import cycle
		OpenTagEditorDialog(tag, parent)
	def deleteTag(tag: BaseTagImpl):
		reply = QMessageBox.question(
			parent, "Delete Tag",
			f"Delete tag '{tag.GetName()}'?\nIt will be removed from all items it is assigned to.",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		if reply == QMessageBox.StandardButton.Yes:
			mainWindow.tagsManager.DeleteTag(tag)

	descData: DescriptorDataImpl = mainWindow.descDataManager.GetDescriptorData(desc)
	descTagsUIDs: list[str] = descData.tags

	tagsMenu: ClickableSubmenuMenu = ClickableSubmenuMenu("Tags", parent)

	# Per-tag 'Edit'/'Delete' submenu, only when the context menu was invoked over a specific tag bubble.
	if tagUnderCursor is not None:
		tagActionSubMenu: QMenu = QMenu(tagUnderCursor.GetName(), tagsMenu)
		tagActionSubMenu.addAction(QAction("Edit", parent, triggered=partial(editTag, tagUnderCursor)))
		tagActionSubMenu.addAction(QAction("Delete", parent, triggered=partial(deleteTag, tagUnderCursor)))
		tagsMenu.addMenu(tagActionSubMenu)
		tagsMenu.addSeparator()

	# 'Assign' submenu: all tags assignable in the current context that aren't already assigned.
	assignSubMenu: QMenu = QMenu("Assign", tagsMenu)
	for tag in mainWindow.tagsManager.GetTags().values():
		if tag.GetUID() in descTagsUIDs:
			continue
		if not tag.IsApplicableInContext(pluginID, softwareID, viewUID):
			continue
		assignSubMenu.addAction(QAction(tag.GetName(), parent, triggered=partial(assignTag, tag)))
	assignSubMenu.setEnabled(not assignSubMenu.isEmpty())
	tagsMenu.addMenu(assignSubMenu)

	# 'Remove' submenu: 'Remove all' + separator + every assigned tag (regardless of scope).
	descTags: list[BaseTagImpl] = [mainWindow.tagsManager.GetTag(tagUID) for tagUID in descTagsUIDs if mainWindow.tagsManager.GetTag(tagUID)]
	removeSubMenu: QMenu = QMenu("Remove", tagsMenu)
	removeSubMenu.addAction(QAction("Remove all", parent, triggered=partial(removeAllTags, descTags)))
	removeSubMenu.addSeparator()
	for tag in descTags:
		removeSubMenu.addAction(QAction(tag.GetName(), parent, triggered=partial(removeTag, tag)))
	removeSubMenu.setEnabled(bool(descTags))
	tagsMenu.addMenu(removeSubMenu)

	menu.addSeparator()
	tagsAction: QAction = menu.addMenu(tagsMenu)
	# _InstallMenuActionClickHandler(menu, tagsAction, openTagsPalette)

	menu.addAction(QAction("Note", parent, triggered=partial(mainWindow._showNoteEditorDialog, desc)))
