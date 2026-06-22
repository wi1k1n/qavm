import os  # TODO: Get rid of os.path in favor of pathlib
from pathlib import Path
from functools import partial
from contextlib import contextmanager
from typing import Type, Optional

from PyQt6.QtCore import Qt, QMargins, QPoint, QByteArray, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QCursor, QColor, QBrush, QPainter, QMouseEvent
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QLabel, QTabWidget, QScrollArea, QStatusBar, QTableWidgetItem, QTableWidget,
	QHeaderView, QMenu, QMenuBar, QStyledItemDelegate, QApplication, QAbstractItemView, QMessageBox,
	QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QLineEdit, QHBoxLayout,
	QSizePolicy, QTableView, QTableWidgetSelectionRange, QDockWidget, 
)

from qavm.manager_plugin import PluginManager, SoftwareHandler, UID, QAVMWorkspace
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings
from qavm.widget_tiles import TilesWidget
from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorDataImpl
from qavm.manager_tags import TagsManager, BaseTagImpl

from qavm.window_note_editor import NoteEditorDialog
from qavm.window_about import AboutDialog
from qavm.widget_table import MyTableWidget
from qavm.window_tag_palette import TagsPaletteWidget

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

		workspace: QAVMWorkspace = app.GetWorkspace()
		self.workspaceID: str = workspace.GetID()
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
		self._setupTagsDock()

		self._restoreWindowGeometry()

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

		self.actionRescan = QAction("&Rescan", self)
		self.actionRescan.setShortcut("Ctrl+F5")
		self.actionRescan.triggered.connect(self._rescanSoftware)

		self.actionAbout = QAction("&About", self)
		self.actionAbout.triggered.connect(self._showAboutDialog)

		self.actionCheckUpdates = QAction("Check Updates Now", self)
		self.actionCheckUpdates.triggered.connect(self._checkForUpdates)

	def _setupMenuBar(self):
		menuBar: QMenuBar = self.menuBar()
		menuBar.setNativeMenuBar(True)  # Use native menu bar on macOS
		
		fileMenu: QMenu = QMenu("&File", self)
		fileMenu.addAction(self.actionPluginSelection)
		fileMenu.addAction(self.actionRescan)
		fileMenu.addSeparator()
		fileMenu.addAction(self.actionPrefs)
		fileMenu.addSeparator()
		fileMenu.addAction(self.actionExit)
		menuBar.addMenu(fileMenu)

		# Application View menu — place before plugin-provided menus
		self.viewMenu: QMenu = QMenu("&View", self)
		menuBar.addMenu(self.viewMenu)

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
		helpMenu.addAction(self.actionCheckUpdates)
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
		self.tableWidgets: list[MyTableWidget] = []

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

		# TODO: FreeMove view is currently not implemented

		self.setCentralWidget(self.tabsWidget)

		self.tabsWidget.currentChanged.connect(self._onTabChanged)
		lastOpenedTab: int = self.qavmSettings.GetWorkspaceLastOpenedTab(self.workspaceID)
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
		tileBuilder: BaseTileBuilder = tileBuilderClass(swHandler.GetSettings(), self.descDataManager.GetDescriptorDataAccessor())
		
		descs: list[BaseDescriptor] = self._prepareDescriptors(swHandler, viewUID, tileBuilder)

		if tilesView := TilesWidget(descs, tileBuilder, swHandler, viewUID, parent=self):
			self.tabsWidget.insertTab(0, tilesView, tileBuilder.GetName())
			# self.tabsWidget.addTabWithUid(tilesView, tileBuilder.GetName(), viewUID+descUID)
			
	def _createTableView(self, swHandler: SoftwareHandler, viewUID: str):
		tableBuilderClass: Type[BaseTableBuilder] | None = swHandler.GetTableBuilderClass(viewUID)
		if tableBuilderClass is None or not issubclass(tableBuilderClass, BaseTableBuilder):
			return
		
		tableBuilder: BaseTableBuilder = tableBuilderClass(swHandler.GetSettings(), self.descDataManager.GetDescriptorDataAccessor())
		
		descs: list[BaseDescriptor] = self._prepareDescriptors(swHandler, viewUID, tableBuilder)
		
		self.tableWidget: MyTableWidget = MyTableWidget(descs, tableBuilder, swHandler, viewUID, parent=self)
		self.tabsWidget.insertTab(0, self.tableWidget, tableBuilder.GetName())
		# self.tabsWidget.addTabWithUid(tableWidget, tableBuilder.GetName(), viewUID+descUID)
		self.tableWidgets.append(self.tableWidget)

		savedState: dict = self.qavmSettings.GetWorkspaceTableViewState(self.workspaceID, viewUID)
		if savedState:
			self.tableWidget.ApplyViewState(savedState)

	def _createCustomView(self, swHandler: SoftwareHandler, viewUID: str):
		customViewClass: Type[BaseCustomView] | None = swHandler.GetCustomViewClass(viewUID)
		if customViewClass is None or not issubclass(customViewClass, BaseCustomView):
			return
		
		softwareSettings: SoftwareBaseSettings = swHandler.GetSettings()
		if customViewWidget := customViewClass(softwareSettings, self):
			self.tabsWidget.insertTab(0, customViewWidget, customViewWidget.GetName())

	def _setupTagsDock(self):
		self.tagsPalette: TagsPaletteWidget = TagsPaletteWidget(self)

		self.tagsDock: QDockWidget = QDockWidget("Tags Palette", self)
		self.tagsDock.setObjectName("TagsPaletteDock")
		self.tagsDock.setWidget(self.tagsPalette)
		# self.tagsDock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
		self.tagsDock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
		self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.tagsDock)
		self.tagsDock.hide()  # hidden by default; toggled via the View menu

		toggleAction: QAction = self.tagsDock.toggleViewAction()
		toggleAction.setText("Tags &Palette")
		toggleAction.setShortcut("Ctrl+T")
		self.viewMenu.addAction(toggleAction)

		# Keep the palette's active-context filter in sync with the current tab
		self.tabsWidget.currentChanged.connect(lambda _idx: self.tagsPalette.OnActiveContextChanged())

		# Restore the tags palette dock layout (visibility / floating / docked side) from the last session.
		savedWindowState: str = self.qavmSettings.GetMainWindowState()
		if savedWindowState:
			self.restoreState(QByteArray.fromBase64(savedWindowState.encode('ascii')))

		# When there's no restored dock layout, the first manual activation should dock the
		# palette to the right at its minimum width (instead of some arbitrary default width).
		self._tagsDockSizeApplied: bool = bool(savedWindowState)
		self.tagsDock.visibilityChanged.connect(self._onTagsDockVisibilityChanged)

		# Restore the tags palette filter (preset + custom filter values) from the last session.
		savedFilter: dict = self.qavmSettings.GetTagsPaletteFilter()
		if savedFilter:
			self.tagsPalette.ApplyFilterState(savedFilter)

	def _onTagsDockVisibilityChanged(self, visible: bool):
		""" On the first activation without a restored layout, dock the palette to the right
		at its minimum width. """
		if not visible or self._tagsDockSizeApplied:
			return
		self._tagsDockSizeApplied = True
		if self.tagsDock.isFloating():
			return
		self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.tagsDock)
		minWidth: int = max(self.tagsDock.minimumSizeHint().width(), self.tagsPalette.minimumSizeHint().width())
		# Defer so the resize is applied after the dock has been laid out for the first time.
		QTimer.singleShot(0, lambda: self.resizeDocks([self.tagsDock], [minWidth], Qt.Orientation.Horizontal))

	@contextmanager
	def _frozenTagsDockWidth(self):
		""" Temporarily pins the tags dock width so it doesn't grab the space momentarily
		vacated by the central widget while it is rebuilt. """
		dock: QDockWidget | None = getattr(self, 'tagsDock', None)
		if dock is None or not dock.isVisible() or dock.isFloating():
			yield
			return
		width: int = dock.width()
		oldMin: int = dock.minimumWidth()
		oldMax: int = dock.maximumWidth()
		dock.setFixedWidth(width)
		try:
			yield
		finally:
			# Keep the width pinned through the deferred relayout, then restore resizability.
			def _restore():
				dock.setMinimumWidth(oldMin)
				dock.setMaximumWidth(oldMax)
			QTimer.singleShot(0, _restore)

	def _onTabChanged(self, index: int):
		self.qavmSettings.SetWorkspaceLastOpenedTab(self.workspaceID, index)
		self.qavmSettings.Save()  # TODO: should save now or later once per all changes?

		if getattr(self, 'tableWidget', None) is not None:
			self.tableWidget.clearFocus()

	def closeEvent(self, event):
		self._saveUIState()
		super().closeEvent(event)

	def _saveUIState(self):
		""" Persists per-workspace table state (sorting + column widths) and the global window/tags palette state. """
		for tableWidget in getattr(self, 'tableWidgets', []):
			self.qavmSettings.SetWorkspaceTableViewState(self.workspaceID, tableWidget.viewUID, tableWidget.GetViewState())

		windowStateB64: str = bytes(self.saveState().toBase64().data()).decode('ascii')
		self.qavmSettings.SetMainWindowState(windowStateB64)

		windowGeometryB64: str = bytes(self.saveGeometry().toBase64().data()).decode('ascii')
		self.qavmSettings.SetMainWindowGeometry(windowGeometryB64)

		if getattr(self, 'tagsPalette', None) is not None:
			self.qavmSettings.SetTagsPaletteFilter(self.tagsPalette.GetFilterState())

		self.qavmSettings.Save()

	def _restoreWindowGeometry(self):
		""" Restores the window position/size onto the same screen; falls back to centering on the primary screen. """
		geometryB64: str = self.qavmSettings.GetMainWindowGeometry()
		if geometryB64:
			restored: bool = self.restoreGeometry(QByteArray.fromBase64(geometryB64.encode('ascii')))
			if restored and self._isOnAvailableScreen():
				return
		self._centerOnPrimaryScreen()

	def _isOnAvailableScreen(self) -> bool:
		""" Returns True if the window's frame is visible on at least one currently available screen. """
		frame = self.frameGeometry()
		for screen in QApplication.screens():
			if screen.availableGeometry().intersects(frame):
				return True
		return False

	def _centerOnPrimaryScreen(self):
		screen = QApplication.primaryScreen()
		if screen is None:
			return
		frame = self.frameGeometry()
		frame.moveCenter(screen.availableGeometry().center())
		self.move(frame.topLeft())
		
	def _showNoteEditorDialog(self, desc: BaseDescriptor):
		"""
		Open a Note Editor dialog for the given descriptor.
		This is a placeholder for the actual implementation.
		"""
		noteEditor = NoteEditorDialog(desc, self)
		if noteEditor.exec() == QDialog.DialogCode.Accepted:
			desc.descDataUpdated.emit()
	
	
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
		
		descData: DescriptorDataImpl = self.descDataManager.GetDescriptorData(desc)
		for tagUID in descData.tags:
			if tag := self.tagsManager.GetTag(tagUID):
				tagsLabel.setText(f"{tagsLabel.text()} <span style='color: {tag.GetColor()};'>#{tag.GetName()}</span> ")

		tagsLabel.setWordWrap(True)  # Allow word wrapping for the tags label
		layout.addWidget(tagsLabel)
		wrapper.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

		return wrapper

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
	
	def _rescanSoftware(self):
		app = QApplication.instance()
		swHandlers, _ = app.GetWorkspace().GetInvolvedSoftwareHandlers()
		for swHandler in swHandlers:
			app.LoadSoftwareDescriptors(swHandler)
		with self._frozenTagsDockWidth():
			oldWidget = self.takeCentralWidget()
			if oldWidget:
				oldWidget.deleteLater()
			self._setupCentralWidget()

	def _showAboutDialog(self):
		aboutDialog: AboutDialog = AboutDialog(self, self.pluginManager)
		aboutDialog.exec()

	def _checkForUpdates(self):
		app = QApplication.instance()
		app.GetUpdateManager().CheckNow(force=True, manual=True)