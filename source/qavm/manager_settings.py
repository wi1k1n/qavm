import json
from pathlib import Path

import qavmapi.utils as utils

from qavmapi import BaseSettings
from manager_plugin import SoftwareHandler

import logs
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
		self.settings['selectedSoftwareUID'] = SettingsEntry('selectedSoftwareUID', '')

		searchPaths: list[str] = []
		if utils.PlatformWindows():
			searchPaths: list[str] = [
				'C:\\Program Files'
			]
		elif utils.PlatformMacOS():
			searchPaths: list[str] = [
				'/Applications'
			]
		self.settings['searchPaths'] = SettingsEntryStringList('searchPaths', searchPaths)

		self.settings['searchSubfoldersDepth'] = SettingsEntry('searchSubfoldersDepth', 2)
		self.settings['hideOnClose'] = SettingsEntry('hideOnClose', False)
		self.settings['extractIcons'] = SettingsEntry('extractIcons', True)
	
	def LoadSettings(self):
		logger.info('Loading settings: NotImplemented')
	
	def RegisterSoftwareSettings(self):
		if not self.settings['selectedSoftwareUID'].getValue():
			raise Exception('No software selected')
		softwareHandler: SoftwareHandler = self.app.GetPluginManager().GetSoftwareHandler(self.settings['selectedSoftwareUID'].getValue())
		settings: BaseSettings = softwareHandler.GetSettingsClass()()

	def GetSelectedSoftwareUID(self) -> str:
		return self.settings['selectedSoftwareUID'].getValue()
	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
		self.settings['selectedSoftwareUID'].setValue(softwareUID)
		self.RegisterSoftwareSettings()

	def GetSearchPaths(self) -> list[str]:
		return self.settings['searchPaths'].getValue()
	
	def GetSearchSubfoldersDepth(self) -> int:
		return self.settings['searchSubfoldersDepth'].getValue()