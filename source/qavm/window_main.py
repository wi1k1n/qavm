import os  # TODO: Get rid of os.path in favor of pathlib
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget, QScrollArea, QStatusBar,
	QListWidgetItem, QListWidget, QPushButton, QHBoxLayout
)

from manager_plugin import PluginManager, SoftwareHandler
from manager_settings import SettingsManager

from qavmapi import BaseDescriptor, BaseSettings, BaseTileBuilder
from qavmapi.gui import StaticBorderWidget
import qavmapi_utils
from utils_gui import FlowLayout, BubbleWidget
import qavmapi.utils as utils

import logs
logger = logs.logger


class SettingsWindowExample(QWidget):
	def __init__(self, app, parent: QWidget | None = None) -> None:
		super().__init__(parent)

		self.setWindowTitle("QAVM - Settings")
		self.resize(600, 600)
		self.setMinimumHeight(300)
		
		def createMenuItem(text: str) -> QListWidgetItem:
			item = QListWidgetItem(text)
			item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			return item
		
		menuWidget = QListWidget()
		menuWidget.addItem(createMenuItem("General"))
		menuWidget.addItem(createMenuItem("Software"))
		menuWidget.addItem(createMenuItem("Plugins"))
		menuWidget.setMinimumWidth(menuWidget.minimumSizeHint().width() + 20)
		menuWidget.setMaximumWidth(200)

		contentWidget = QLabel("This is my text here")

		contentLayout = QVBoxLayout()
		contentLayout.addWidget(contentWidget)

		contentWidget = QWidget()
		contentWidget.setLayout(contentLayout)

		mainLayout = QHBoxLayout()
		mainLayout.addWidget(menuWidget, 1)
		mainLayout.addWidget(contentWidget, 3)
		self.setLayout(mainLayout)

class DialogsManager:
	def __init__(self, parent: QMainWindow) -> None:
		self.parent = parent
		
		self.settings = SettingsWindowExample(self)

	def GetPreferencesWindow(self):
		return self.preferences

class MainWindow(QMainWindow):
	def __init__(self, app, parent: QWidget | None = None) -> None:
		super(MainWindow, self).__init__(parent)

		self.app = app

		self.setWindowTitle("QAVM")
		self.resize(1420, 840)
		self.setMinimumSize(350, 250)

		self.dialogsManager: DialogsManager = DialogsManager(self)

		self._setupActions()
		self._setupMenuBar()
		self._setupStatusBar()

		self._setupCentralWidget()

	def _setupActions(self):
		# self.actionSave = QAction("&Save tags and tiles", self)
		# self.actionSave.setShortcut(QKeySequence.StandardKey.Save)

		self.actionPrefs = QAction(QIcon(":preferences.svg"), "&Preferences", self)
		self.actionPrefs.setShortcut("Ctrl+E")
		self.actionPrefs.triggered.connect(self.dialogsManager.settings.show)

		self.actionExit = QAction("&Exit", self, shortcut=QKeySequence.StandardKey.Quit)
		self.actionExit.triggered.connect(self.close)

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

	def _setupCentralWidget(self):
		tabsWidget: QTabWidget = QTabWidget()

		pluginManager: PluginManager = self.app.GetPluginManager()
		settingsManager: SettingsManager = self.app.GetSettingsManager()
		softwareHandler: SoftwareHandler = pluginManager.GetSoftwareHandler(settingsManager.GetSelectedSoftwareUID())
		descs: list[BaseDescriptor] = self._scanSoftware()
		defaultTileBuilder = softwareHandler.GetTileBuilderClass()()

		tilesWidget = self._createTilesWidget(descs, defaultTileBuilder, self)
		freeMoveWidget = self._createFreeMoveWidget(descs, defaultTileBuilder, self)
		tabsWidget.addTab(tilesWidget, "Tiles")
		tabsWidget.addTab(freeMoveWidget, "Free Move")
		
		self.setCentralWidget(tabsWidget)
	
	def _createFreeMoveWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget):
		return QLabel("Freemove", parent)
	
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




	def _scanSoftware(self) -> list[BaseDescriptor]:
		pluginManager: PluginManager = self.app.GetPluginManager()
		settingsManager: SettingsManager = self.app.GetSettingsManager()
		softwareHandler: SoftwareHandler = pluginManager.GetSoftwareHandler(settingsManager.GetSelectedSoftwareUID())

		qualifier = softwareHandler.GetQualifierClass()()
		descriptorClass = softwareHandler.GetDescriptorClass()
		settingsClass = softwareHandler.GetSettingsClass()
		if not settingsClass:
			settingsClass = BaseSettings

		searchPaths = settingsManager.GetSearchPaths()
		searchPaths = qualifier.ProcessSearchPaths(searchPaths)

		config = qualifier.GetIdentificationConfig()
		if not qavmapi_utils.ValidateQualifierConfig(config):
			raise Exception('Invalid Qualifier config')
		
		def getDirListIgnoreError(pathDir: str) -> list[Path]:
			try:
				dirList: list[Path] = [Path(pathDir)/d for d in os.listdir(pathDir)]
				return list(filter(lambda d: os.path.isdir(d), dirList))
			except:
				logger.warning(f'Failed to get dir list: {pathDir}')
			return list()
		
		def TryPassFileMask(dirPath: Path, config: dict[str, list[str]]) -> bool:
			for file in config['requiredFileList']:
				if not (dirPath / file).is_file():
					return False
			for folder in config['requiredDirList']:
				if not (dirPath / folder).is_dir():
					return False
			for file in config['negativeFileList']:
				if (dirPath / file).is_file():
					return False
			for folder in config['negativeDirList']:
				if (dirPath / folder).is_dir():
					return False
			return True
		
		def GetFileContents(dirPath: Path, config: dict[str, list[str]]) -> dict[str, str | bytes]:
			fileContents = dict()
			for file, isBinary, lengthLimit in config['fileContentsList']:
				try:
					# TODO: use pathlib instead
					with open(os.path.join(dirPath, file), 'rb' if isBinary else 'r') as f:
						fileContents[file] = f.read(lengthLimit if lengthLimit else -1)
				except Exception as e:
					# logger.warning(f'Failed to read file "{os.path.join(dirPath, file)}": {e}')
					pass
			return fileContents
		
		softwareDescs: list[BaseDescriptor] = list()

		MAX_DEPTH = 1  # TODO: make this a settings value
		currentDepthLevel: int = 0
		searchPathsList = set(searchPaths)
		while currentDepthLevel < MAX_DEPTH:
			subfoldersSearchPathsList = set()
			for searchPath in searchPathsList:
				dirs: set[Path] = set(getDirListIgnoreError(searchPath))
				subdirs: set[str] = set()
				# for dir in dirs:
				for dir in sorted(dirs):
					passed = TryPassFileMask(dir, config)
					if not passed:
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue

					fileContents: dict[str, str | bytes] = GetFileContents(dir, config)
					if not qualifier.Identify(dir, fileContents):
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue
					softwareDescs.append(descriptorClass(dir, fileContents))
				subfoldersSearchPathsList.update(subdirs)
			searchPathsList = subfoldersSearchPathsList
			currentDepthLevel += 1
		
		return softwareDescs