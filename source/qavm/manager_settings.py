import json
from pathlib import Path

import qavm.qavmapi.utils as utils

from qavm.qavmapi import BaseSettings
from qavm.manager_plugin import PluginManager, SoftwareHandler, SettingsHandler

import qavm.logs as logs
logger = logs.logger

class SettingsEntry:
	def __init__(self, uid: str, value):
		self.uid: str = uid
		self.value = value
	def getValue(self):
		return self.value
	def setValue(self, value):
		self.value = value
	def serialize(self) -> tuple[str, str]:
		return (self.uid, self.getValue())
	def deserialize(self, data: dict) -> None:
		self.value = data[self.uid]

class SettingsEntryStringList(SettingsEntry):
	def serialize(self) -> tuple[str, str]:
		return (self.uid, json.dumps(self.value))
	def deserialize(self, data: dict) -> None:
		self.value = json.loads(data[self.uid])

class SettingsManager:
	def __init__(self, app, prefsFolderPath: Path):
		self.app = app
		self.prefsFolderPath: Path = prefsFolderPath
		self.settings: dict[str, SettingsEntry] = dict()
		self.moduleSettings: dict[str, BaseSettings] = dict()

		searchPaths: list[str] = []
		if utils.PlatformWindows():
			searchPaths: list[str] = [
				'C:\\Program Files'
			]
		elif utils.PlatformMacOS():
			searchPaths: list[str] = [
				'/Applications'
			]
		
		# Initialize with default values
		self.settings['_selectedSoftwareUID_'] = SettingsEntry('_selectedSoftwareUID_', '')
		self.settings['_searchPaths_'] = SettingsEntryStringList('_searchPaths_', searchPaths)
		self.settings['_searchSubfoldersDepth_'] = SettingsEntry('_searchSubfoldersDepth_', 2)
		self.settings['_hideOnClose_'] = SettingsEntry('_hideOnClose_', False)
		self.settings['_extractIcons_'] = SettingsEntry('_extractIcons_', True)
	
	""" Load settings from the disk """
	def LoadSettings(self):
		logger.info('Loading settings: NotImplemented')
	
	def LoadModuleSettings(self):
		pluginManager: PluginManager = self.app.GetPluginManager()
		settingsModules: list[tuple[str, str, SettingsHandler]] = pluginManager.GetSettingsHandlers()  # [pluginID, moduleID, SettingsHandler]
		for pluginID, settingsID, settingsHandler in settingsModules:
			self.moduleSettings[f'{pluginID}#{settingsID}'] = settingsHandler.GetSettingsClass()()
		

	def GetSelectedSoftwarePluginID(self) -> str:
		return self.GetSelectedSoftwareUID().split('#')[0]
	
	def GetSelectedSoftwareUID(self) -> str:
		return self.settings['_selectedSoftwareUID_'].getValue()
	
	""" The softwareUID is in the format: PLUGIN_ID#SoftwareID """
	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
		self.settings['_selectedSoftwareUID_'].setValue(softwareUID)

	def GetSearchPaths(self) -> list[str]:
		return self.settings['_searchPaths_'].getValue()
	def GetSearchSubfoldersDepth(self) -> int:
		return self.settings['_searchSubfoldersDepth_'].getValue()
	
	def GetSoftwareSettings(self) -> BaseSettings:
		if not self.settings['_selectedSoftwareUID_'].getValue():
			raise Exception('No software selected')
		softwareHandler: SoftwareHandler = self.app.GetPluginManager().GetSoftwareHandler(self.settings['_selectedSoftwareUID_'].getValue())
		return softwareHandler.GetSettingsClass()()
	
	""" Returns dict of settings modules that are implemented in currently selected plugin: {moduleUID: BaseSettings}. The moduleUID is in form PLUGIN_ID#SettingsModuleID """
	def GetModuleSettings(self) -> dict[str, BaseSettings]:
		return self.moduleSettings