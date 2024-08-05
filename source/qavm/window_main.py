import os  # TODO: Get rid of os.path in favor of pathlib
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QLabel, QTabWidget, QScrollArea, QStatusBar, QTableWidgetItem, QTableWidget
)

from qavm.manager_plugin import PluginManager, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMSettings

from qavm.qavmapi import BaseDescriptor, BaseSettings, BaseTileBuilder
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
		# tabsWidget.addTab(self.tilesWidget, "Tiles")

		# TODO: handle case when softwareHandler is None
		softwareHandler: SoftwareHandler = self.pluginManager.GetSoftwareHandler(self.qavmSettings.GetSelectedSoftwareUID())
		defaultTileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings())

		self.tableWidget = self._createTableWidget(self.app.GetSoftwareDescriptions(), defaultTileBuilder, self)
		self.tabsWidget.insertTab(1, self.tableWidget, "Details")

		self.freeMoveWidget = self._createFreeMoveWidget(self.app.GetSoftwareDescriptions(), defaultTileBuilder, self)
		self.tabsWidget.insertTab(2, self.freeMoveWidget, "Free Move")
		
		self.setCentralWidget(self.tabsWidget)
	
	def _createFreeMoveWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget):
		return QLabel("Freemove", parent)
	
	def _createTableWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget):
		tableWidget = QTableWidget(parent)
		tableWidget.setColumnCount(2)
		tableWidget.setRowCount(len(descs))
		tableWidget.setHorizontalHeaderLabels(["Name", "Path"])
		tableWidget.verticalHeader().setVisible(False)
		tableWidget.horizontalHeader().setStretchLastSection(True)
		# tableWidget.horizontalHeader().setSectionResizeMode(0, QTableWidget.ResizeMode.ResizeToContents)
		# tableWidget.horizontalHeader().setSectionResizeMode(1, QTableWidget.ResizeMode.Stretch)
		
		for i, desc in enumerate(descs):
			tableWidget.setItem(i, 0, QTableWidgetItem(str(desc)))
			tableWidget.setItem(i, 1, QTableWidgetItem(str(desc.dirPath)))
		
		return tableWidget
	
	def UpdateTilesWidget(self):
		currentTabIndex: int = self.tabsWidget.currentIndex()

		if hasattr(self, 'tilesWidget') and self.tilesWidget:
			self.tilesWidget.deleteLater()
		
		softwareHandler: SoftwareHandler = self.pluginManager.GetSoftwareHandler(self.qavmSettings.GetSelectedSoftwareUID())  # TODO: handle case when softwareHandler is None
		defaultTileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings())

		self.tilesWidget = self._createTilesWidget(self.app.GetSoftwareDescriptions(), defaultTileBuilder, self)
		self.tabsWidget.insertTab(0, self.tilesWidget, "Tiles")
		
		self.tabsWidget.setCurrentIndex(currentTabIndex)

	def _createTilesWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget):
		tiles: list[QWidget] = list()

		for desc in descs:
			tileWidget = tileBuilder.CreateTileWidget(desc, parent)
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
