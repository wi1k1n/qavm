import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
	QWidget, QFormLayout, QCheckBox, QLineEdit, QApplication, QListWidget, QListWidgetItem,
	QVBoxLayout, QPushButton, QLabel, QFileDialog
)

import qavm.qavmapi.utils as utils

from qavm.qavmapi import BaseSettings, BaseSettingsContainer, BaseSettingsEntry, SoftwareBaseSettings
from qavm.manager_plugin import PluginManager, SoftwareHandler

import qavm.logs as logs
logger = logs.logger

# # TODO: should this be part of qavmapi?
# class QAVMSettingsContainer:
# 	SETTINGS_ENTRIES: dict[str, Any] = {  # key: default value
# 		'selectedSoftwareUID': 						'', 			# str
# 		'searchPaths': 								[], 			# list[str]
# 		'searchSubfoldersDepth': 					2, 				# int
# 		'hideOnClose': 								False, 			# bool
# 		'lastOpenedTab': 							0, 				# enum  # TODO: use enum, currently 0 - tiles, 1 - table, 2 - freemove
# 	}

# 	def __init__(self):
# 		super().__init__()
# 		for key, default in self.SETTINGS_ENTRIES.items():
# 			setattr(self, key, default)
		
# 		if utils.PlatformWindows():
# 			self.searchPaths: list[str] = [
# 				'C:\\Program Files'
# 			]
# 		elif utils.PlatformMacOS():
# 			self.searchPaths: list[str] = [
# 				'/Applications'
# 			]
	
# 	def DumpToString(self) -> str:
# 		data: dict = dict()
# 		for key in self.SETTINGS_ENTRIES.keys():
# 			data[key] = getattr(self, key)
# 		return json.dumps(data)
	
# 	def InitializeFromString(self, dataStr: str) -> bool:
# 		try:
# 			data: dict = json.loads(dataStr)
# 			for key in self.SETTINGS_ENTRIES.keys():
# 				if key not in data: return False
# 				setattr(self, key, data[key])
# 			return True
# 		except Exception as e:
# 			logger.exception(f'Failed to parse settings data: {e}')
# 			return False

class DeletableListWidget(QListWidget):
	def keyPressEvent(self, event: QKeyEvent) -> None:
		if event.key() == Qt.Key.Key_Delete:
			for item in self.selectedItems():
				self.takeItem(self.row(item))
		else:
			super().keyPressEvent(event)

# class QAVMSettings(BaseSettings):
# 	""" Global settings that are related to the QAVM app itself """
# 	def __init__(self) -> None:
# 		super().__init__()
# 		self.container = QAVMSettingsContainer()

# 		self.prefFilePath: Path = utils.GetPrefsFolderPath()/'qavm-preferences.json'
# 		if not self.prefFilePath.exists():
# 			logger.info(f'QAVM settings file not found, creating a new one. Path: {self.prefFilePath}')
# 			self.Save()

# 	def Load(self):
# 		with open(self.prefFilePath, 'r') as f:
# 			if not self.container.InitializeFromString(f.read()):
# 				logger.error('Failed to load QAVM settings')

# 	def Save(self):
# 		if not self.prefFilePath.parent.exists():
# 			logger.info(f"QAVM preferences folder doesn't exist. Creating: {self.prefFilePath.parent}")
# 			self.prefFilePath.parent.mkdir(parents=True, exist_ok=True)
# 		with open(self.prefFilePath, 'w') as f:
# 			f.write(self.container.DumpToString())

# 	def CreateWidget(self, parent: QWidget) -> QWidget:
# 		settingsWidget: QWidget = QWidget(parent)

# 		vboxLayout: QVBoxLayout = QVBoxLayout(settingsWidget)
# 		vboxLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

# 		vboxLayout.addWidget(QLabel('Search paths', settingsWidget))
# 		vboxLayout.addWidget(self._createSearchPathsWidget(settingsWidget))

# 		# vboxLayout.addWidget(QLabel('Search subfolders depth', self._createSearchSubfoldersDepthSliderWidget(settingsWidget)))
# 		# formLayout.addRow('Hide on close', QCheckBox())

# 		return settingsWidget
	
# 	def _spListWidgetAddSearchPathItem(self, path: str) -> None:
# 		item: QListWidgetItem = QListWidgetItem(path)
# 		item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
# 		self.spListWidget.addItem(item)

# 	def _createSearchPathsWidget(self, parent: QWidget) -> QWidget:
# 		spWidget: QWidget = QWidget(parent)
# 		vboxLayout: QVBoxLayout = QVBoxLayout(spWidget)
# 		vboxLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

# 		self.spListWidget: DeletableListWidget = DeletableListWidget(spWidget)
# 		self.spListWidget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

# 		for path in self.container.searchPaths:
# 			self._spListWidgetAddSearchPathItem(path)
		
# 		btnBrowse: QPushButton = QPushButton('Browse', spWidget)
# 		btnBrowse.clicked.connect(self._browseSearchPath)
		
# 		vboxLayout.addWidget(self.spListWidget)
# 		vboxLayout.addWidget(btnBrowse)

# 		return spWidget
	
# 	def _browseSearchPath(self) -> None:
# 		if folder := QFileDialog.getExistingDirectory(None, "Select a folder", None, QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks):
# 			path: Path = Path(folder)
# 			if path not in self.container.searchPaths:
# 				pathStr: str = str(path)
# 				self.container.searchPaths.append(pathStr)
# 				self._spListWidgetAddSearchPathItem(pathStr)
		

	
# 	# def _createSearchSubfoldersDepthSliderWidget(self, parent: QWidget) -> QWidget:
# 	# 	sliderWidget: QWidget = QWidget(parent)

# 	# 	formLayout: QFormLayout = QFormLayout(sliderWidget)
# 	# 	formLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

# 	# 	slider: QLineEdit = QLineEdit(str(self.container.searchSubfoldersDepth), sliderWidget)
# 	# 	# slider.setValidator(utils.IntValidator(0, 10, slider))
# 	# 	slider.setMaximumWidth(50)
# 	# 	slider.editingFinished.connect(lambda: print('Slider value changed'))

# 	# 	formLayout.addRow('Search subfolders depth', slider)

# 	# 	return sliderWidget
	
# 	def GetSelectedSoftwarePluginID(self) -> str:
# 		return self.GetSelectedSoftwareUID().split('#')[0]
	
# 	def GetSelectedSoftwareUID(self) -> str:
# 		app = QApplication.instance()  # QAVMApp
# 		if app.selectedSoftwareUID:  # selectedSoftwareUID override coming from CL argument
# 			return app.selectedSoftwareUID
# 		return self.container.selectedSoftwareUID
	
# 	""" The softwareUID is in the format: PLUGIN_ID#SoftwareID """
# 	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
# 		self.container.selectedSoftwareUID = softwareUID

# 	def GetSearchPaths(self) -> list[str]:
# 		return self.container.searchPaths
	
# 	def GetSearchSubfoldersDepth(self) -> int:
# 		return self.container.searchSubfoldersDepth
	
# 	def GetLastOpenedTab(self) -> int:
# 		return self.container.lastOpenedTab
# 	def SetLastOpenedTab(self, tabIndex: int) -> None:
# 		self.container.lastOpenedTab = tabIndex

class QAVMGlobalSettings(BaseSettings):
	CONTAINER_DEFAULTS: dict[str, Any] = {
		'selected_software_uid': '',  # str, the software UID in form PLUGIN_ID#SoftwareID
		'last_opened_tab': 0,  # int, the last opened tab index
		'app_theme': 'light_pink',  # str, the app theme name
	}
	
	def GetSelectedSoftwareUID(self) -> str:
		app = QApplication.instance()  # QAVMApp
		if app.selectedSoftwareUID:  # that's where the override coming from CL argument is stored
			return app.selectedSoftwareUID
		return self.GetSetting('selected_software_uid')
	
	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
		""" The softwareUID is in the format: PLUGIN_ID#SoftwareID """
		self.SetSetting('selected_software_uid', softwareUID)
	
	def CreateWidget(self, parent) -> QWidget:
		settingsWidget: QWidget = QWidget(parent)
		layout: QFormLayout = QFormLayout(settingsWidget)

		self.appThemeEdit: QLineEdit = QLineEdit(self.GetSetting('app_theme'), settingsWidget)
		self.appThemeEdit.setPlaceholderText('Enter app theme name')
		self.appThemeEdit.textChanged.connect(lambda text: self.SetSetting('app_theme', text))
		layout.addRow('App Theme', self.appThemeEdit)

		self.lastOpenedTabEdit: QLineEdit = QLineEdit(str(self.GetSetting('last_opened_tab')), settingsWidget)
		self.lastOpenedTabEdit.textChanged.connect(lambda text: self.SetSetting('last_opened_tab', int(text) if text.isdigit() else 0))
		layout.addRow('Last Opened Tab', self.lastOpenedTabEdit)

		return settingsWidget

class SettingsManager:
	def __init__(self, app, prefsFolderPath: Path):
		self.app = app
		self.prefsFolderPath: Path = prefsFolderPath

		self.qavmGlobalSettings: QAVMGlobalSettings = QAVMGlobalSettings('qavm-global')
		self.softwareSettings: SoftwareBaseSettings = None

		# self.moduleSettings: dict[str, BaseSettings] = dict()

	def GetQAVMSettings(self) -> QAVMGlobalSettings:
		return self.qavmGlobalSettings
	
	def LoadQAVMSettings(self):
		self.prefsFolderPath.mkdir(parents=True, exist_ok=True)
		self.qavmGlobalSettings.Load()

	def SaveQAVMSettings(self):
		self.qavmGlobalSettings.Save()
	
	
	def GetSoftwareSettings(self) -> SoftwareBaseSettings:
		return self.softwareSettings
	
	def LoadSoftwareSettings(self):
		if not self.qavmGlobalSettings.GetSelectedSoftwareUID():
			raise Exception('No software selected')
		softwareHandler: SoftwareHandler = self.app.GetPluginManager().GetCurrentSoftwareHandler()
		self.softwareSettings = softwareHandler.GetSettings()
		self.softwareSettings.Load()

	def SaveSoftwareSettings(self):
		if not self.softwareSettings:
			raise Exception('No software settings loaded')
		self.softwareSettings.Save()
	
	# def LoadModuleSettings(self):
	# 	pluginManager: PluginManager = self.app.GetPluginManager()
	# 	settingsModules: list[tuple[str, str, SettingsHandler]] = pluginManager.GetSettingsHandlers()  # [pluginID, moduleID, SettingsHandler]
	# 	for pluginID, settingsID, settingsHandler in settingsModules:
	# 		moduleSettings: BaseSettings = settingsHandler.GetSettings()
	# 		moduleSettings.Load()
	# 		self.moduleSettings[f'{pluginID}#{settingsID}'] = moduleSettings
	
	# """ Returns dict of settings modules that are implemented in currently selected plugin: {moduleUID: BaseSettings}. The moduleUID is in form PLUGIN_ID#SettingsModuleID """
	# def GetModuleSettings(self) -> dict[str, BaseSettings]:
	# 	return self.moduleSettings