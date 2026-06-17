from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMenu, QWidget
from PyQt6.QtGui import QAction

from qavm.manager_tags import BaseTagImpl
from qavm.qavmapi import BaseDescriptor

if TYPE_CHECKING:
	from qavm.window_main import MainWindow
	from qavm.manager_descriptor_data import DescriptorDataImpl

import qavm.logs as logs
logger = logs.logger


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
