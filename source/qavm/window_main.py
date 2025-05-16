import os  # TODO: Get rid of os.path in favor of pathlib
from pathlib import Path
from functools import partial

from PyQt6.QtCore import Qt, QMargins, QPoint
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QCursor
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QLabel, QTabWidget, QScrollArea, QStatusBar, QTableWidgetItem, QTableWidget,
	QHeaderView, QMenu
)

from qavm.manager_plugin import PluginManager, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMSettings

from qavm.qavmapi import (
	BaseDescriptor, BaseSettings, BaseTileBuilder, BaseTableBuilder, BaseContextMenu
)
from qavm.utils_gui import FlowLayout
import qavm.qavmapi_utils as qavmapi_utils

import qavm.logs as logs
logger = logs.logger

class MainWindow(QMainWindow):
	def __init__(self, app, parent: QWidget | None = None) -> None:
		super(MainWindow, self).__init__(parent)

		self.app = app
		
		self.dialogsManager = self.app.GetDialogsManager()
		self.pluginManager: PluginManager = self.app.GetPluginManager()
		self.settingsManager: SettingsManager = self.app.GetSettingsManager()
		self.qavmSettings: QAVMSettings = self.settingsManager.GetQAVMSettings()
		self.softwareSettings: BaseSettings = self.settingsManager.GetSoftwareSettings()
		self.softwareSettings.tilesUpdateRequired.connect(self.UpdateTilesWidget)
		self.softwareSettings.tablesUpdateRequired.connect(self.UpdateTableWidget)

		self.setWindowTitle("QAVM")
		self.resize(1420, 840)
		self.setMinimumSize(350, 250)

		self._setupActions()
		self._setupMenuBar()
		self._setupStatusBar()

		self._setupCentralWidget()

	def _setupActions(self):
		# self.actionSave = QAction("&Save tags and tiles", self)
		# self.actionSave.setShortcut(QKeySequence.StandardKey.Save)

		self.actionPrefs = QAction(QIcon(":preferences.svg"), "&Preferences", self)
		self.actionPrefs.setShortcut("Ctrl+E")
		self.actionPrefs.triggered.connect(self._showPreferences)

		self.actionExit = QAction("&Exit", self, shortcut=QKeySequence.StandardKey.Quit)
		self.actionExit.triggered.connect(self.close)

		self.actionPluginSelection = QAction("Select software", self)
		self.actionPluginSelection.setEnabled(len(self.pluginManager.GetSoftwareHandlers()) > 1)
		self.actionPluginSelection.triggered.connect(self._switchToPluginSelection)

		self.actionRescan = QAction("&Rescan", self)
		self.actionRescan.setShortcut("Ctrl+F5")
		self.actionRescan.triggered.connect(self._rescanSoftware)

		# self.actionAbout = QAction("&About", self)
		# self.actionShortcuts = QAction("&Shortcuts", self)
		# self.actionShortcuts.setShortcut("F1")
		# self.actionReportBug = QAction("&Report a bug", self)
		# self.actionReportBug.setShortcut("Ctrl+Shift+B")
		# self.actionCheckUpdates = QAction("&Check for updates", self)
		
		# self.actionRefresh = QAction("&Refresh", self)
		# self.actionRefresh.setShortcut(QKeySequence.StandardKey.Refresh)
		# self.actionRescan = QAction("Re&scan", self)
		# self.actionRescan.setShortcut("Ctrl+F5")

		# self.actionTags = QAction("&Tags", self)
		# self.actionTags.setShortcut("Ctrl+T")

		# self.actionFiltersort = QAction("Filte&r/Sort", self)
		# self.actionFiltersort.setShortcut("Ctrl+F")

		# self.actionFoldAll = QAction("Toggle &fold all", self)
		# self.actionFoldAll.setShortcut("Ctrl+A")

		# self._createGroupActions()
		
		# self.actionSave.triggered.connect(self._storeData)
		# self.actionPrefs.triggered.connect(self.openPreferences)
		# self.actionExit.triggered.connect(sys.exit)
		# self.actionAbout.triggered.connect(self.about)
		# self.actionCheckUpdates.triggered.connect(CheckForUpdates)
		# self.actionShortcuts.triggered.connect(self.help)
		# self.actionReportBug.triggered.connect(lambda: self._showActivateDialog('trackbugs'))
		# self.actionRefresh.triggered.connect(lambda: self.updateTilesWidget())
		# self.actionRescan.triggered.connect(self.rescan)
		# self.actionTags.triggered.connect(self.toggleOpenTagsWindow)
		# self.actionFiltersort.triggered.connect(self.toggleOpenFilterSortWindow)
		# self.actionFoldAll.triggered.connect(self._toggleFoldAllC4DGroups)
		
		# # Adding help tips
		# newTip = "Create a new file"
		# self.newAction.setStatusTip(newTip)
		# self.newAction.setToolTip(newTip)

	def _setupMenuBar(self):
		menuBar = self.menuBar()
		menuBar.setNativeMenuBar(True)
		
		fileMenu = menuBar.addMenu('&File')
		# fileMenu.addAction(self.actionSave)
		# fileMenu.addSeparator()
		fileMenu.addAction(self.actionRescan)
		fileMenu.addSeparator()
		fileMenu.addAction(self.actionPluginSelection)
		fileMenu.addSeparator()
		fileMenu.addAction(self.actionExit)
		
		editMenu = menuBar.addMenu("&Edit")
		# editMenu.addAction(self.actionRefresh)
		# editMenu.addAction(self.actionRescan)
		# editMenu.addSeparator()
		# editMenu.addAction(self.actionTags)
		# editMenu.addAction(self.actionFiltersort)
		# fileMenu.addSeparator()
		editMenu.addAction(self.actionPrefs)
		
		viewMenu = menuBar.addMenu("&View")
		# viewMenu.addAction(self.actionFoldAll)
		# viewMenu.addSeparator()
		# # for k, action in self.actionsGrouping.items():
		# # 	viewMenu.addAction(action)

		helpMenu = menuBar.addMenu("&Help")
		# helpMenu.addAction(self.actionShortcuts)
		# helpMenu.addAction(self.actionReportBug)
		# helpMenu.addAction(self.actionCheckUpdates)
		# helpMenu.addAction(self.actionAbout)
	
	def _setupStatusBar(self):
		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)

	# TODO: this shouldn't be in constructor!
	def _setupCentralWidget(self):
		self.tabsWidget: QTabWidget = QTabWidget()
		
		self.UpdateTilesWidget()
		self.UpdateTableWidget()

		# TODO: handle case when softwareHandler is None
		softwareHandler: SoftwareHandler = self.pluginManager.GetSoftwareHandler(self.qavmSettings.GetSelectedSoftwareUID())
		contextMenu: BaseContextMenu = softwareHandler.GetTileBuilderContextMenuClass()(softwareHandler.GetSettings())
		tileBuilder: BaseTileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings(), contextMenu)

		self.freeMoveWidget = self._createFreeMoveWidget(self.app.GetSoftwareDescriptions(), tileBuilder, self)
		self.tabsWidget.insertTab(2, self.freeMoveWidget, "Free Move")

		self.setCentralWidget(self.tabsWidget)
	
	def _createFreeMoveWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget):
		return QLabel("Freemove", parent)
	
	def UpdateTableWidget(self):
		softwareHandler: SoftwareHandler = self.pluginManager.GetSoftwareHandler(self.qavmSettings.GetSelectedSoftwareUID())  # TODO: handle case when softwareHandler is None
		contextMenu: BaseContextMenu = softwareHandler.GetTableBuilderContextMenuClass()(softwareHandler.GetSettings())
		tableBuilder = softwareHandler.GetTableBuilderClass()(softwareHandler.GetSettings(), contextMenu)
		if type(tableBuilder) is BaseTableBuilder:
			return
		
		currentTabIndex: int = self.tabsWidget.currentIndex()

		if hasattr(self, 'tableWidget') and self.tableWidget:
			self.tableWidget.deleteLater()
		
		self.tableWidget = self._createTableWidget(self.app.GetSoftwareDescriptions(), tableBuilder, contextMenu, self)
		self.tabsWidget.insertTab(1, self.tableWidget, "Details")
		
		self.tabsWidget.setCurrentIndex(currentTabIndex)

	def _createTableWidget(self, descs: list[BaseDescriptor], tableBuilder: BaseTableBuilder, contextMenu: BaseContextMenu, parent: QWidget):
		tableWidget = QTableWidget(parent)

		headers: list[str] = tableBuilder.GetTableCaptions()

		tableWidget.setColumnCount(len(headers) + 1)
		tableWidget.setHorizontalHeaderLabels(headers + ['descIdx'])
		tableWidget.setRowCount(len(descs))
		tableWidget.verticalHeader().setVisible(False)
		tableWidget.hideColumn(len(headers))  # hide descIdx column, this is kinda dirty, but gives more flexibility comparing to qabstracttablemodel and qproxymodel
		
		tableWidget.setSortingEnabled(True)

		tableWidget.horizontalHeader().setStretchLastSection(True)
		tableWidget.horizontalHeader().setMinimumSectionSize(150)
		tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		
		tableWidget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
		tableWidget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

		# TODO: this sounds like a temp solution
		contextMenus: list[QMenu] = list()
		def showContextMenu(pos):
			selectedRowsUnique: set = {idx.row() for idx in tableWidget.selectedIndexes()}
			currentRow = selectedRowsUnique.pop()
			descIdx: int = int(tableWidget.item(currentRow, len(headers)).text())
			contextMenus[descIdx].exec(QCursor.pos())
		
		for r, desc in enumerate(descs):
			for c, header in enumerate(headers):
				tableWidgetItem = tableBuilder.GetTableCellValue(desc, c)
				if not isinstance(tableWidgetItem, QTableWidgetItem):
					tableWidgetItem = QTableWidgetItem(tableWidgetItem)
				tableWidget.setItem(r, c, tableWidgetItem)
			tableWidget.setItem(r, len(headers) + 0, QTableWidgetItem(str(r)))

			contextMenus.append(contextMenu.CreateMenu(desc))
		
		tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		tableWidget.customContextMenuRequested.connect(showContextMenu)
		
		return tableWidget
	
	def UpdateTilesWidget(self):
		softwareHandler: SoftwareHandler = self.pluginManager.GetSoftwareHandler(self.qavmSettings.GetSelectedSoftwareUID())  # TODO: handle case when softwareHandler is None
		contextMenu: BaseContextMenu = softwareHandler.GetTileBuilderContextMenuClass()(softwareHandler.GetSettings())
		tileBuilder: BaseTileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings(), contextMenu)
		if type(tileBuilder) is BaseTileBuilder:
			return

		currentTabIndex: int = self.tabsWidget.currentIndex()

		if hasattr(self, 'tilesWidget') and self.tilesWidget:
			self.tilesWidget.deleteLater()

		self.tilesWidget = self._createTilesWidget(self.app.GetSoftwareDescriptions(), tileBuilder, contextMenu, self)
		self.tabsWidget.insertTab(0, self.tilesWidget, "Tiles")
		
		self.tabsWidget.setCurrentIndex(currentTabIndex)

	def _createTilesWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, contextMenu: BaseContextMenu, parent: QWidget):
		tiles: list[QWidget] = list()

		for desc in descs:
			tileWidget = tileBuilder.CreateTileWidget(desc, parent)
			
			tileWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
			menu = contextMenu.CreateMenu(desc)
			tileWidget.customContextMenuRequested.connect(partial(lambda m, p: m.exec(QCursor.pos()), menu))

			tiles.append(tileWidget)

		flWidget = self._createFlowLayoutWithFromWidgets(self, tiles)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget, self)

		return scrollWidget

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
	
	def _switchToPluginSelection(self):
		# TODO: this should probably has clearer handling
		self.qavmSettings.SetSelectedSoftwareUID('')
		self.qavmSettings.Save()
		self.dialogsManager.GetPluginSelectionWindow().show()
		self.close()
	
	def _rescanSoftware(self):
		self.app.ResetSoftwareDescriptions()
		self.UpdateTilesWidget()


	def _showPreferences(self):
		prefsWindow: QMainWindow = self.app.GetDialogsManager().GetPreferencesWindow()
		prefsWindow.show()
		prefsWindow.activateWindow()
