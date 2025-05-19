import json
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import QWidget, QFormLayout, QCheckBox, QLineEdit

import qavm.qavmapi.utils as utils

from qavm.qavmapi import BaseSettings
from qavm.manager_plugin import PluginManager, SoftwareHandler, SettingsHandler

import qavm.logs as logs
logger = logs.logger

# TODO: should this be part of qavmapi?
class QAVMSettingsContainer:
	SETTINGS_ENTRIES: dict[str, Any] = {  # key: default value
		'selectedSoftwareUID': '', 	# str
		'searchPaths': [], 			# list[str]
		'searchSubfoldersDepth': 2, # int
		'hideOnClose': False, 		# bool
	}

	def __init__(self):
		super().__init__()
		for key, default in self.SETTINGS_ENTRIES.items():
			setattr(self, key, default)
		
		if utils.PlatformWindows():
			self.searchPaths: list[str] = [
				'C:\\Program Files'
			]
		elif utils.PlatformMacOS():
			self.searchPaths: list[str] = [
				'/Applications'
			]
	
	def DumpToString(self) -> str:
		data: dict = dict()
		for key in self.SETTINGS_ENTRIES.keys():
			data[key] = getattr(self, key)
		return json.dumps(data)
	def InitializeFromString(self, dataStr: str) -> bool:
		try:
			data: dict = json.loads(dataStr)
			for key in self.SETTINGS_ENTRIES.keys():
				if key not in data: return False
				setattr(self, key, data[key])
			return True
		except Exception as e:
			logger.exception(f'Failed to parse settings data: {e}')
			return False

class QAVMSettings(BaseSettings):
	def __init__(self) -> None:
		super().__init__()
		self.container = QAVMSettingsContainer()

		self.prefFilePath: Path = utils.GetPrefsFolderPath()/'qavm-preferences.json'
		if not self.prefFilePath.exists():
			logger.info(f'QAVM settings file not found, creating a new one. Path: {self.prefFilePath}')
			self.Save()

	def Load(self):
		with open(self.prefFilePath, 'r') as f:
			if not self.container.InitializeFromString(f.read()):
				logger.error('Failed to load QAVM settings')

	def Save(self):
		if not self.prefFilePath.parent.exists():
			logger.info(f"QAVM preferences folder doesn't exist. Creating: {self.prefFilePath.parent}")
			self.prefFilePath.parent.mkdir(parents=True, exist_ok=True)
		with open(self.prefFilePath, 'w') as f:
			f.write(self.container.DumpToString())

	def CreateWidget(self, parent: QWidget) -> QWidget:
		settingsWidget: QWidget = QWidget(parent)
		formLayout: QFormLayout = QFormLayout(settingsWidget)

		formLayout.addRow('Search paths', QWidget())
		formLayout.addRow('Search subfolders depth', QLineEdit())
		formLayout.addRow('Hide on close', QCheckBox())

		return settingsWidget

	
	def GetSelectedSoftwarePluginID(self) -> str:
		return self.GetSelectedSoftwareUID().split('#')[0]
	
	def GetSelectedSoftwareUID(self) -> str:
		return self.container.selectedSoftwareUID
	
	""" The softwareUID is in the format: PLUGIN_ID#SoftwareID """
	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
		self.container.selectedSoftwareUID = softwareUID

	def GetSearchPaths(self) -> list[str]:
		return self.container.searchPaths
	
	def GetSearchSubfoldersDepth(self) -> int:
		return self.container.searchSubfoldersDepth

class SettingsManager:
	def __init__(self, app, prefsFolderPath: Path):
		self.app = app
		self.prefsFolderPath: Path = prefsFolderPath

		self.qavmSettings: QAVMSettings = QAVMSettings()
		self.softwareSettings: BaseSettings = None

		self.moduleSettings: dict[str, BaseSettings] = dict()

	def LoadQAVMSettings(self):
		self.prefsFolderPath.mkdir(parents=True, exist_ok=True)
		self.qavmSettings.Load()
	
	def LoadSoftwareSettings(self):
		if not self.qavmSettings.GetSelectedSoftwareUID():
			raise Exception('No software selected')
		softwareHandler: SoftwareHandler = self.app.GetPluginManager().GetCurrentSoftwareHandler()
		self.softwareSettings = softwareHandler.GetSettings()
		self.softwareSettings.Load()
	
	def LoadModuleSettings(self):
		pluginManager: PluginManager = self.app.GetPluginManager()
		settingsModules: list[tuple[str, str, SettingsHandler]] = pluginManager.GetSettingsHandlers()  # [pluginID, moduleID, SettingsHandler]
		for pluginID, settingsID, settingsHandler in settingsModules:
			moduleSettings: BaseSettings = settingsHandler.GetSettings()
			moduleSettings.Load()
			self.moduleSettings[f'{pluginID}#{settingsID}'] = moduleSettings

	def GetQAVMSettings(self) -> QAVMSettings:
		return self.qavmSettings
	
	def GetSoftwareSettings(self) -> BaseSettings:
		return self.softwareSettings
	
	""" Returns dict of settings modules that are implemented in currently selected plugin: {moduleUID: BaseSettings}. The moduleUID is in form PLUGIN_ID#SettingsModuleID """
	def GetModuleSettings(self) -> dict[str, BaseSettings]:
		return self.moduleSettings