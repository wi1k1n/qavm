import inspect
from functools import partial
from typing import TYPE_CHECKING, Callable, Optional

from PyQt6.QtWidgets import QMenu, QWidget, QApplication, QMessageBox
from PyQt6.QtGui import QAction, QColor, QCursor, QDrag, QPainter, QPixmap, QMouseEvent
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

def UnassignTagUIDFromDescriptor(desc: BaseDescriptor, tagUID: str) -> bool:
	""" Removes the tag with the given UID from the descriptor and notifies listeners. Returns True on success. """
	app = QApplication.instance()
	tagsManager = app.GetTagsManager()
	tag: BaseTagImpl | None = tagsManager.GetTag(tagUID)
	if tag is None:
		logger.warning(f"Cannot unassign tag: unknown tag UID {tagUID}")
		return False
	tagsManager.RemoveTag(desc, tag)
	return True

def AssignTagUIDToDescriptorWithScopeCheck(desc: BaseDescriptor, tagUID: str, pluginID: str, softwareID: str,
										viewUID: str, parent: QWidget | None = None) -> bool:
	""" Assigns the tag to the descriptor, but when the tag's scope doesn't apply to the given
	plugin/software/view context it first asks the user to confirm (the tag stays visible on the item
	but is normally filtered out of this view). Returns True if the tag was assigned. """
	app = QApplication.instance()
	tagsManager = app.GetTagsManager()
	tag: BaseTagImpl | None = tagsManager.GetTag(tagUID)
	if tag is None:
		logger.warning(f"Cannot assign tag: unknown tag UID {tagUID}")
		return False
	if not tag.IsApplicableInContext(pluginID, softwareID, viewUID):
		reply = QMessageBox.question(
			parent, "Assign Out-of-Scope Tag",
			f"The tag '{tag.GetName()}' has wrong scope for this assignment.\n\n"
			f"Assign it anyway?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		if reply != QMessageBox.StandardButton.Yes:
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
		tagActionSubMenu.addAction(QAction("Unassign", parent, triggered=partial(removeTag, tagUnderCursor)))
		tagActionSubMenu.addSeparator()
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


# Modifier keys we care about for context-menu rebuilding, mapped from their Qt key code to the modifier.
_MODIFIER_KEYS: dict[int, Qt.KeyboardModifier] = {
	int(Qt.Key.Key_Shift): Qt.KeyboardModifier.ShiftModifier,
	int(Qt.Key.Key_Control): Qt.KeyboardModifier.ControlModifier,
	int(Qt.Key.Key_Alt): Qt.KeyboardModifier.AltModifier,
	int(Qt.Key.Key_AltGr): Qt.KeyboardModifier.AltModifier,
	int(Qt.Key.Key_Meta): Qt.KeyboardModifier.MetaModifier,
}
# Only these modifiers are considered when deciding whether to rebuild the context menu.
_RELEVANT_MODIFIERS: Qt.KeyboardModifier = (
	Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
	| Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier
)


def CallBuilderGetContextMenu(builder, desc: BaseDescriptor, modifiers: Qt.KeyboardModifier) -> Optional[QMenu]:
	""" Invokes builder.GetContextMenu, passing `modifiers` when the override accepts it.

	Older plugins may still define GetContextMenu(self, desc) without the `modifiers` parameter; those are
	called with a single argument so they keep working. """
	method = builder.GetContextMenu
	acceptsModifiers = True
	try:
		params = list(inspect.signature(method).parameters.values())
		# `method` is bound, so `self` is already excluded. Anything beyond `desc` (an extra positional
		# parameter, a `modifiers` keyword, or *args/**kwargs) means the override can receive the modifiers.
		positional = [p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
		hasVarArgs = any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params)
		hasModifiersKw = any(p.name == 'modifiers' for p in params)
		acceptsModifiers = hasVarArgs or hasModifiersKw or len(positional) >= 2
	except (TypeError, ValueError):
		acceptsModifiers = True
	if acceptsModifiers:
		return method(desc, modifiers)
	return method(desc)


class _ModifierChangeMenuHandler(QObject):
	""" Application-wide event filter that reacts to modifier-key changes while `menu` is open.

	Modifier presses/releases are tracked starting from `baseModifiers`. On each change it asks `updater`
	to rebuild the menu in place (avoiding a close/reopen flash). If the updater declines (returns None),
	the new modifier set is recorded in `rebuildModifiers` and the menu is closed so the caller can rebuild
	it from scratch. """
	def __init__(self, menu: QMenu, baseModifiers: Qt.KeyboardModifier,
				updater: Callable[[QMenu, Qt.KeyboardModifier], Optional[QMenu]]):
		super().__init__()
		self._menu: QMenu = menu
		self._modifiers: Qt.KeyboardModifier = baseModifiers & _RELEVANT_MODIFIERS
		self._updater = updater
		self.rebuildModifiers: Qt.KeyboardModifier | None = None

	def eventFilter(self, obj: QObject, event: QEvent) -> bool:
		etype = event.type()
		if etype in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease) and not self._menu.isHidden():
			mod = _MODIFIER_KEYS.get(event.key())
			if mod is not None:
				updated = (self._modifiers | mod) if etype == QEvent.Type.KeyPress else (self._modifiers & ~mod)
				if updated != self._modifiers:
					result: Optional[QMenu] = None
					try:
						result = self._updater(self._menu, updated)
					except Exception:
						logger.exception("In-place context menu update failed")
					if result is None:
						# Updater declined: fall back to closing and rebuilding the menu from scratch.
						self.rebuildModifiers = updated
						self._menu.close()
					else:
						self._modifiers = updated
						_RestoreActiveActionUnderCursor(self._menu)
		return False


def _RestoreActiveActionUnderCursor(menu: QMenu) -> None:
	""" After rebuilding a menu in place, re-highlights whichever action is currently under the cursor so
	the selection doesn't visually reset while the pointer hasn't moved. """
	pos: QPoint = menu.mapFromGlobal(QCursor.pos())
	menu.setActiveAction(menu.actionAt(pos) if menu.rect().contains(pos) else None)


def ShowDynamicContextMenu(
		menuBuilder: Callable[[Qt.KeyboardModifier], Optional[QMenu]],
		menuUpdater: Callable[[QMenu, Qt.KeyboardModifier], Optional[QMenu]],
		globalPos: QPoint) -> None:
	""" Shows a context menu at `globalPos` and keeps it in sync with the keyboard modifiers.

	`menuBuilder(modifiers)` builds a fresh menu (used for the initial show and whenever an in-place update
	is unavailable). `menuUpdater(menu, modifiers)` rebuilds the currently-shown menu in place and returns
	it; returning None makes QAVM fall back to closing and rebuilding the menu via `menuBuilder`. Either way
	the menu tracks modifier changes until it is dismissed or one of its actions is triggered. """
	app = QApplication.instance()
	modifiers: Qt.KeyboardModifier = QApplication.keyboardModifiers() & _RELEVANT_MODIFIERS
	while True:
		menu = menuBuilder(modifiers)
		if menu is None:
			return
		handler = _ModifierChangeMenuHandler(menu, modifiers, menuUpdater)
		app.installEventFilter(handler)
		try:
			menu.exec(globalPos)
		finally:
			app.removeEventFilter(handler)
		if handler.rebuildModifiers is None:
			return  # menu dismissed or one of its actions was triggered
		modifiers = handler.rebuildModifiers
