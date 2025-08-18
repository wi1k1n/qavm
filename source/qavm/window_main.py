import os  # TODO: Get rid of os.path in favor of pathlib
from pathlib import Path
from functools import partial
from typing import Type, Optional

from PyQt6.QtCore import Qt, QMargins, QPoint, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QCursor, QColor, QBrush, QPainter, QMouseEvent
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QLabel, QTabWidget, QScrollArea, QStatusBar, QTableWidgetItem, QTableWidget,
	QHeaderView, QMenu, QMenuBar, QStyledItemDelegate, QApplication, QAbstractItemView, QMessageBox,
	QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QLineEdit, QHBoxLayout,
	QSizePolicy, QTableView, QTableWidgetSelectionRange, 
)

from qavm.manager_plugin import PluginManager, SoftwareHandler, UID, QAVMWorkspace
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings
from qavm.widget_tiles import TilesWidget
from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorData
from qavm.manager_tags import TagsManager, Tag

from qavm.window_note_editor import NoteEditorDialog
from qavm.window_about import AboutDialog
from qavm.widget_table import MyTableWidget

from qavm.qavmapi import (
	BaseDescriptor, BaseSettings, BaseTileBuilder, BaseTableBuilder,
	BaseCustomView, SoftwareBaseSettings, BaseMenuItem, BaseBuilder, 
)
from qavm.qavmapi.utils import PlatformMacOS, PlatformWindows, PlatformLinux
from qavm.utils_gui import FlowLayout
from qavm.qavm_version import GetBuildVersion, GetPackageVersion, GetQAVMVersion, GetQAVMVersionVariant

import qavm.logs as logs
logger = logs.logger

# TODO: wtf, rename it please!
class MyTabWidget(QTabWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self._uidToWidget = {}  # uid → QWidget

	def addTabWithUid(self, widget: QWidget, title: str, uid: str):
		if uid in self._uidToWidget:
			raise ValueError(f"UID '{uid}' already exists")
		self._uidToWidget[uid] = widget
		self.addTab(widget, title)

	def removeTabByUid(self, uid: str):
		widget = self._uidToWidget.pop(uid, None)
		if widget is not None:
			index = self.indexOf(widget)
			if index != -1:
				self.removeTab(index)

	def setTabVisibleByUid(self, uid: str, visible: bool):
		widget = self._uidToWidget.get(uid)
		if widget:
			index = self.indexOf(widget)
			self.tabBar().setTabVisible(index, visible)

	def getTabByUid(self, uid: str) -> QWidget | None:
		return self._uidToWidget.get(uid)

	def setCurrentTabByUid(self, uid: str):
		widget = self._uidToWidget.get(uid)
		if widget:
			self.setCurrentWidget(widget)

class MainWindow(QMainWindow):
	def __init__(self, parent: QWidget | None = None) -> None:
		super(MainWindow, self).__init__(parent)

		app = QApplication.instance()
		self.dialogsManager = app.GetDialogsManager()
		self.pluginManager: PluginManager = app.GetPluginManager()
		self.settingsManager: SettingsManager = app.GetSettingsManager()
		self.qavmSettings: QAVMGlobalSettings = self.settingsManager.GetQAVMSettings()
		self.descDataManager: DescriptorDataManager = app.GetDescriptorDataManager()
		self.tagsManager: TagsManager = app.GetTagsManager()
		
		# self.softwareSettings: SoftwareBaseSettings = self.settingsManager.GetSoftwareSettings()

		# self.softwareSettings.tilesUpdateRequired.connect(self.UpdateTilesWidget)
		# self.softwareSettings.tablesUpdateRequired.connect(self.UpdateTableWidget)
		
		# softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()

		workspace: QAVMWorkspace = app.GetWorkspace()
		swHandlers, _ = workspace.GetInvolvedSoftwareHandlers()
		swTitle: str = ', '.join([f'{sw.GetName()}' for sw in swHandlers])[:50]

		self.setWindowTitle(f'QAVM {GetQAVMVersionVariant()} - [{swTitle}]')
		self.resize(1420, 840)
		self.setMinimumSize(350, 250)

		self.pluginMenuItems: list[QMenu | QAction] = list()  # for some reason QMenu and QAction need to live in the MainWindow, otherwise Qt gets rid of them

		self._setupActions()
		self._setupMenuBar()
		self._setupStatusBar()

		self._setupCentralWidget()

	def _setupActions(self):
		self.actionPrefs = QAction("&Preferences", self)
		self.actionPrefs.setShortcut("Ctrl+E")
		self.actionPrefs.triggered.connect(self.dialogsManager.ShowPreferences)

		self.actionExit = QAction("&Exit", self, shortcut=QKeySequence.StandardKey.Quit)
		self.actionExit.triggered.connect(self.close)

		self.actionPluginSelection = QAction("Switch Workspace", self)
		self.actionPluginSelection.setShortcut("Ctrl+`")
		# self.actionPluginSelection.setEnabled(len(self.pluginManager.GetSoftwareHandlers()) > 1)
		self.actionPluginSelection.triggered.connect(self._switchToPluginSelection)

		# self.actionRescan = QAction("&Rescan", self)
		# self.actionRescan.setShortcut("Ctrl+F5")
		# self.actionRescan.triggered.connect(self._rescanSoftware)

		self.actionAbout = QAction("&About", self)
		self.actionAbout.triggered.connect(self._showAboutDialog)

	def _setupMenuBar(self):
		menuBar: QMenuBar = self.menuBar()
		menuBar.setNativeMenuBar(True)  # Use native menu bar on macOS
		
		fileMenu: QMenu = QMenu("&File", self)
		# fileMenu.addAction(self.actionRescan)
		# fileMenu.addSeparator()
		fileMenu.addAction(self.actionPluginSelection)
		fileMenu.addAction(self.actionPrefs)
		fileMenu.addSeparator()
		fileMenu.addAction(self.actionExit)
		menuBar.addMenu(fileMenu)
		
		# switchMenu: QMenu = QMenu("&Switch Workspace", self)
		# switchMenu.addAction(QAction("osx sucks", self))
		# menuBar.addMenu(switchMenu)
		# def populate_switch_menu():
		# 	switchMenu.clear()
		# 	swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()  # [pluginID, softwareID, SoftwareHandler]
		# 	for pluginID, softwareID, softwareHandler in swHandlers:
		# 		plugin: QAVMPlugin = self.pluginManager.GetPlugin(pluginID)
		# 		swUID: str = f'{pluginID}#{softwareID}'
		# 		title: str = f'{softwareHandler.GetName()} [{plugin.GetName()} @ {plugin.GetVersionStr()}] ({swUID})'
		# 		action = QAction(title, self)
		# 		action.triggered.connect(partial(self._switchToPluginSelection, swUID))
		# 		switchMenu.addAction(action)
		# switchMenu.aboutToShow.connect(populate_switch_menu)  # TODO: does this need dynamic update?

		app = QApplication.instance()
		workspace: QAVMWorkspace = app.GetWorkspace()

		for swHandler, menuItemsUIDs in workspace.GetMenuItems().items():
			for menuItemUID in menuItemsUIDs:
				if menuItem := swHandler.GetMenuItem(menuItemUID):
					if menu := menuItem.GetMenu(self):
						if isinstance(menu, QMenu):
							menuBar.addMenu(menu)
							self.pluginMenuItems.append(menu)  # for some reason QMenu and QAction need to live in the MainWindow, otherwise Qt gets rid of them
						elif isinstance(menu, QAction):
							menuBar.addAction(menu)
							self.pluginMenuItems.append(menu)  # for some reason QMenu and QAction need to live in the MainWindow, otherwise Qt gets rid of them
						else:
							logger.warning(f"Menu item {menu} is not a valid QMenu or QAction. Skipping.")

		helpMenu: QMenu = QMenu("&Help", self)
		helpMenu.addAction(self.actionAbout)
		menuBar.addMenu(helpMenu)

		# ##################################################################
		# ########################## Right Corner ##########################
		# ##################################################################
		# if not PlatformMacOS():  # macOS isn't capable of complex things
		# 	rightCornerMenu = QMenuBar(menuBar)
		# 	for pluginID, softwareID, softwareHandler in self.pluginManager.GetSoftwareHandlers():
		# 		swUID: str = f'{pluginID}#{softwareID}'
		# 		title: str = softwareHandler.GetName()
		# 		action = QAction(title, self, triggered=partial(self._switchToPluginSelection, swUID))
		# 		rightCornerMenu.addAction(action)
		# 	menuBar.setCornerWidget(rightCornerMenu)
	
	def _setupStatusBar(self):
		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)

	# TODO: this shouldn't be in constructor!
	def _setupCentralWidget(self):
		self.tabsWidget: MyTabWidget = MyTabWidget(self)
		
		app = QApplication.instance()
		workspace: QAVMWorkspace = app.GetWorkspace()

		for swHandler, tilesViewsUIDs in workspace.GetTilesViews().items():
			for viewUID in tilesViewsUIDs:
				self._createTilesView(swHandler, viewUID)

		for swHandler, tilesViewsUIDs in workspace.GetTableViews().items():
			for viewUID in tilesViewsUIDs:
				self._createTableView(swHandler, viewUID)

		for swHandler, customViews in workspace.GetCustomViews().items():
			for viewUID in customViews:
				self._createCustomView(swHandler, viewUID)

		# self.UpdateTilesWidget()
		# self.UpdateTableWidget()

		# TODO: FreeMove view is currently not implemented

		self.setCentralWidget(self.tabsWidget)

		self.tabsWidget.currentChanged.connect(self._onTabChanged)
		lastOpenedTab: int = self.qavmSettings.GetSetting('last_opened_tab')
		if lastOpenedTab >= 0 and lastOpenedTab < self.tabsWidget.count():
			self.tabsWidget.setCurrentIndex(lastOpenedTab)


	def _prepareDescriptors(self, swHandler: SoftwareHandler, viewUID: str, builder: BaseBuilder):
		# TODO: consider having some more understandable scheme for fetching descriptor types from dataPaths
		descTypes: list[str] = [t for t in map(UID.DataPathGetLastPart, swHandler.GetDescriptorClasses().keys()) if t]
		descTypes = builder.GetSupportedDescriptorTypes(descTypes)
		if not descTypes:
			return []

		app = QApplication.instance()
		descsMap: dict[str, list[BaseDescriptor]] = app.GetSoftwareDescriptors(swHandler)  # TODO: check to not iterate unnecessarily over unsupported descriptors
		
		descs: list[BaseDescriptor] = []
		for descUID, descsCur in descsMap.items():
			descType: Optional[str] = UID.DataPathGetLastPart(descUID)
			if descType in descTypes:
				descs.extend(builder.ProcessDescriptors(descType, descsCur))

		return descs
		
	def _createTilesView(self, swHandler: SoftwareHandler, viewUID: str):
		tileBuilderClass: Type[BaseTileBuilder] | None = swHandler.GetTileBuilderClass(viewUID)
		if tileBuilderClass is None or not issubclass(tileBuilderClass, BaseTileBuilder):
			return
		tileBuilder: BaseTileBuilder = tileBuilderClass(swHandler.GetSettings())
		
		descs: list[BaseDescriptor] = self._prepareDescriptors(swHandler, viewUID, tileBuilder)

		if tilesView := TilesWidget(descs, tileBuilder, parent=self):
			tileBuilder.updateTileRequired.connect(partial(self._updateTilesWidget, descs, tileBuilder))
			self.tabsWidget.insertTab(0, tilesView, tileBuilder.GetName())
			# self.tabsWidget.addTabWithUid(tilesView, tileBuilder.GetName(), viewUID+descUID)
			
	def _createTableView(self, swHandler: SoftwareHandler, viewUID: str):
		tableBuilderClass: Type[BaseTableBuilder] | None = swHandler.GetTableBuilderClass(viewUID)
		if tableBuilderClass is None or not issubclass(tableBuilderClass, BaseTableBuilder):
			return
		tableBuilder: BaseTableBuilder = tableBuilderClass(swHandler.GetSettings())
		
		descs: list[BaseDescriptor] = self._prepareDescriptors(swHandler, viewUID, tableBuilder)
		
		tableWidget: MyTableWidget = MyTableWidget(descs, tableBuilder, parent=self)
		tableWidget.itemSelectionChanged.connect(partial(self._tableItemFocusBuggedWorkaround, tableWidget))
		self.tabsWidget.insertTab(0, tableWidget, tableBuilder.GetName())
		# self.tabsWidget.addTabWithUid(tableWidget, tableBuilder.GetName(), viewUID+descUID)

	def _createCustomView(self, swHandler: SoftwareHandler, viewUID: str):
		customViewClass: Type[BaseCustomView] | None = swHandler.GetCustomViewClass(viewUID)
		if customViewClass is None or not issubclass(customViewClass, BaseCustomView):
			return
		
		softwareSettings: SoftwareBaseSettings = swHandler.GetSettings()
		if customViewWidget := customViewClass(softwareSettings, self):
			self.tabsWidget.insertTab(0, customViewWidget, customViewWidget.GetName())

	def _onTabChanged(self, index: int):
		self.qavmSettings.SetSetting('last_opened_tab', index)
		self.qavmSettings.Save()  # TODO: should save now or later once per all changes?
	
	def _tableItemFocusBuggedWorkaround(self, tableWidget: QTableWidget):
		"""
		For some reason, after switching to the TilesWidget + RMB click there and switching back to the TableWidget,
		the TableWidget starts highlighting the currently selected item regardless of the Qt.FocusPolicy.NoFocus
		"""
		if self.tabsWidget.currentIndex() == 1:  # TODO: dynamically get table tab index, don't hardcode!
			tableWidget.clearFocus()
	
	
	# def UpdateTilesWidget(self):
	# 	softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()  # TODO: handle case when softwareHandler is None
	# 	contextMenu: BaseContextMenu = softwareHandler.GetTileBuilderContextMenuClass()(softwareHandler.GetSettings())
	# 	tileBuilder: BaseTileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings(), contextMenu)
	# 	if type(tileBuilder) is BaseTileBuilder:
	# 		return

	# 	currentTabIndex: int = self.tabsWidget.currentIndex()

	# 	if hasattr(self, 'tilesWidget') and self.tilesWidget:
	# 		self.tilesWidget.deleteLater()

	# 	app = QApplication.instance()
	# 	self.tilesWidget = self._createTilesWidget(app.GetSoftwareDescriptions(), tileBuilder, contextMenu, self)
	# 	self.tabsWidget.insertTab(0, self.tilesWidget, "Tiles")
		
	# 	self.tabsWidget.setCurrentIndex(currentTabIndex)

	def _createTilesWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget) -> QWidget:
		tiles: list[QWidget] = list()

		def showContextMenu(desc):
			def assignTag(tag: Tag):
				logger.info(f"Assigning tag {tag.GetName()} to descriptor {desc.GetUID()}")
				self.tagsManager.AssignTag(desc, tag)
			def removeTag(desc: BaseDescriptor, tag: Tag):
				logger.info(f"Removing tag {tag.GetName()} from descriptor {desc.GetUID()}")
				self.tagsManager.RemoveTag(desc, tag)

			if menu := tileBuilder.GetContextMenu(desc):
				descData: DescriptorData = self.descDataManager.GetDescriptorData(desc)
				descTagsUIDs: list[str] = descData.tags
				
				addTagSubMenu = None
				if tags := self.tagsManager.GetTags().values():
					addTagSubMenu: QMenu = QMenu("Assign Tag", self)
					for tag in tags:
						if tag.GetUID() in descTagsUIDs:
							continue
						action = QAction(tag.GetName(), self, triggered=partial(assignTag, tag))
						addTagSubMenu.addAction(action)
					

				removeTagsSubMenu = None
				if descTags := [self.tagsManager.GetTag(tagUID) for tagUID in descTagsUIDs if self.tagsManager.GetTag(tagUID)]:
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
				menu.addAction(QAction("Edit Note", self, triggered=partial(self._showNoteEditorDialog, desc)))
				
				menu.exec(QCursor.pos())

		for desc in descs:
			# desc.updated.connect(partial(self._onDescriptorUpdated, desc))
			tileWidget = tileBuilder.CreateTileWidget(desc, parent)
			
			tileWidgetWithTags = self._wrapWidgetWithTags(tileWidget, parent, desc)

			descData: DescriptorData = self.descDataManager.GetDescriptorData(desc)
			tileWidgetWithTags.setToolTip(descData.note)
			
			tileWidgetWithTags.descriptor = desc  # TODO: what-a-heck? make a setter for that
			tileWidgetWithTags.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
			tileWidgetWithTags.customContextMenuRequested.connect(partial(lambda d, p: showContextMenu(d), desc))

			tiles.append(tileWidgetWithTags)

		flWidget = self._createFlowLayoutWithFromWidgets(self, tiles)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget, self)

		return scrollWidget
		
	def _showNoteEditorDialog(self, desc: BaseDescriptor):
		"""
		Open a Note Editor dialog for the given descriptor.
		This is a placeholder for the actual implementation.
		"""
		noteEditor = NoteEditorDialog(desc, self)
		if noteEditor.exec() == QDialog.DialogCode.Accepted:
			# TODO: Emit signal to update descriptor in views
			pass
	
	
	def _wrapWidgetWithTags(self, widget: QWidget, parent: QWidget, desc: BaseDescriptor) -> QWidget:
		wrapper = QWidget(parent)
		layout = QVBoxLayout(wrapper)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(5)

		layout.addWidget(widget)

		# Create a label for tags
		tagsLabel = QLabel(wrapper)
		tagsLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
		tagsLabel.setWordWrap(True)
		tagsLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		tagsLabel.setStyleSheet("QLabel { color: gray; font-size: 10px; }")  # Style the tags label
		
		descData: DescriptorData = self.descDataManager.GetDescriptorData(desc)
		for tagUID in descData.tags:
			if tag := self.tagsManager.GetTag(tagUID):
				tagsLabel.setText(f"{tagsLabel.text()} <span style='color: {tag.GetColor()};'>#{tag.GetName()}</span> ")

		tagsLabel.setWordWrap(True)  # Allow word wrapping for the tags label
		layout.addWidget(tagsLabel)
		wrapper.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

		return wrapper
	
	# # TODO: this is very similar to UpdateTilesWidget, code duplication
	# def _onDescriptorUpdated(self, desc: BaseDescriptor):
	# 	if not hasattr(self, 'tilesWidget'):
	# 		return
		
	# 	scrollArea = self.tilesWidget
	# 	flWidget = scrollArea.widget()
	# 	if not flWidget or not isinstance(flWidget.layout(), FlowLayout):
	# 		return

	# 	flowLayout: FlowLayout = flWidget.layout()

	# 	for i in range(flowLayout.count()):
	# 		widget = flowLayout.itemAt(i).widget()
	# 		if getattr(widget, 'descriptor', None) == desc:
	# 			# Remove old widget
	# 			flowLayout.removeWidget(widget)
	# 			widget.deleteLater()

	# 			# Create and insert new tile
	# 			softwareHandler = self.pluginManager.GetSoftwareHandler(self.qavmSettings.GetSelectedSoftwareUID())
	# 			contextMenu = softwareHandler.GetTileBuilderContextMenuClass()(softwareHandler.GetSettings())
	# 			tileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings(), contextMenu)

	# 			newTile = tileBuilder.CreateTileWidget(desc, self)
	# 			newTile.descriptor = desc
	# 			newTile.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
	# 			menu = contextMenu.CreateMenu(desc)
	# 			newTile.customContextMenuRequested.connect(partial(lambda m, p: m.exec(QCursor.pos()), menu))

	# 			# Optional: keep tiles sorted or in original order
	# 			flowLayout.insertWidget(i, newTile)
	# 			break

	# 	self.tableWidget.update()


	def _createFlowLayoutWithFromWidgets(self, parent, widgets: list[QWidget]):
		flWidget = QWidget(parent)
		flWidget.setMinimumWidth(50)

		flowLayout = FlowLayout(flWidget, margin=5, hspacing=5, vspacing=5)
		flowLayout.setSpacing(0)

		for widget in widgets:
			widget.setFixedWidth(widget.sizeHint().width())
			flowLayout.addWidget(widget)

		return flWidget
	
	def _wrapWidgetInScrollArea(self, widget, parent):
		scrollWidget = QScrollArea(parent)
		scrollWidget.setWidgetResizable(True)
		scrollWidget.setWidget(widget)
		return scrollWidget
	
	def _switchToPluginSelection(self, swUID: str = ''):
		app = QApplication.instance()
		app.SetWorkspace(QAVMWorkspace())  # reset the workspace to force workspace manager dialog
		
		self.qavmSettings.SetWorkspaceLast(app.GetWorkspace())
		self.qavmSettings.Save()  # TODO: storing the setting without being sure that the plugin runs leads to a deadlock (start and crash)
		
		self.dialogsManager.ShowWorkspaceManager()
	
	# def _rescanSoftware(self):
	# 	app = QApplication.instance()
	# 	app.ResetSoftwareDescriptions()
	# 	self.UpdateTilesWidget()

	def _showAboutDialog(self):
		aboutDialog: AboutDialog = AboutDialog(self, self.pluginManager)
		aboutDialog.exec()