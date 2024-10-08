import importlib.util, os, re
from pathlib import Path

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings, BaseTableBuilder, BaseContextMenu
)
import qavm.qavmapi.utils as utils

import qavm.logs as logs
logger = logs.logger

class QAVMModule:
	def __init__(self, plugin, regData):
		self.id = regData.get('id', None)

class QAVMModuleNamed(QAVMModule):
	def __init__(self, plugin, regData) -> None:
		super().__init__(plugin, regData)
		self.name = regData.get('name', self.id)
	
	def GetName(self) -> str:
		return self.name

class SoftwareHandler(QAVMModuleNamed):
	def __init__(self, plugin, regData) -> None:
		super().__init__(plugin, regData)
		
		if not QAVMPlugin.ValidateID(self.id):
			raise Exception(f'Invalid or missing Software ID: {self.id}')
		
		# TODO: lots of repeated code here, refactor

		self.settingsClass = regData.get('settings', None)  # optional
		if not self.settingsClass:
			self.settingsClass = BaseSettings
		if not issubclass(self.settingsClass, BaseSettings):
			raise Exception(f'Invalid settings for software: {self.id}')
		self.settingsInstance = self.settingsClass()

		self.qualifierClass = regData.get('qualifier', None)
		if not self.qualifierClass or not issubclass(self.qualifierClass, BaseQualifier):  # required
			raise Exception(f'Missing or invalid qualifier for software: {self.id}')
		self.qualifierInstance = self.qualifierClass()

		self.descriptorClass = regData.get('descriptor', None)
		if not self.descriptorClass or not issubclass(self.descriptorClass, BaseDescriptor):  # required
			raise Exception(f'Missing or invalid descriptor for software: {self.id}')
		
		self.tileBuilderClass: BaseTileBuilder = BaseTileBuilder
		self.tileContextMenuClass: BaseContextMenu = BaseContextMenu
		tileViewData: dict = regData.get('tile_view', {})
		if tileViewData:
			if not isinstance(tileViewData, dict):
				raise Exception(f'Invalid tile view data for software: {self.id}')
			self.tileBuilderClass: BaseTileBuilder = tileViewData.get('tile_builder', None)
			if not self.tileBuilderClass:
				self.tileBuilderClass = BaseTileBuilder
			if not issubclass(self.tileBuilderClass, BaseTileBuilder):
				raise Exception(f'Invalid tile builder for software: {self.id}')
			
			self.tileContextMenuClass: BaseContextMenu = tileViewData.get('context_menu', None)
			if not self.tileContextMenuClass:
				self.tileContextMenuClass = BaseContextMenu
			if not issubclass(self.tileContextMenuClass, BaseContextMenu):
				raise Exception(f'Invalid context menu for software: {self.id}')
		
		self.tableBuilderClass: BaseTableBuilder = BaseTableBuilder
		self.tableContextMenuClass: BaseContextMenu = BaseContextMenu
		tableViewData: dict = regData.get('table_view', {})
		if tableViewData:
			if not isinstance(tableViewData, dict):
				raise Exception(f'Invalid table view data for software: {self.id}')
			self.tableBuilderClass: BaseTableBuilder = tableViewData.get('table_builder', None)
			if not self.tableBuilderClass:
				self.tableBuilderClass = BaseTableBuilder
			if not issubclass(self.tableBuilderClass, BaseTableBuilder):
				raise Exception(f'Invalid table builder for software: {self.id}')

			self.tableContextMenuClass: BaseContextMenu = tableViewData.get('context_menu', None)
			if not self.tableContextMenuClass:
				self.tableContextMenuClass = BaseContextMenu
			if not issubclass(self.tableContextMenuClass, BaseContextMenu):
				raise Exception(f'Invalid context menu for software: {self.id}')

	
	def GetDescriptorClass(self) -> BaseDescriptor.__class__:
		return self.descriptorClass
	def GetTileBuilderClass(self) -> BaseTileBuilder.__class__:
		return self.tileBuilderClass
	def GetTileBuilderContextMenuClass(self) -> BaseContextMenu.__class__:
		return self.tileContextMenuClass
	def GetTableBuilderClass(self) -> BaseTableBuilder.__class__:
		return self.tableBuilderClass
	def GetTableBuilderContextMenuClass(self) -> BaseContextMenu.__class__:
		return self.tableContextMenuClass
	def GetQualifier(self) -> BaseQualifier:
		return self.qualifierInstance
	def GetSettings(self) -> BaseSettings:
		return self.settingsInstance

class SettingsHandler(QAVMModuleNamed):
	def __init__(self, plugin, regData) -> None:
		super().__init__(plugin, regData)

		self.settingsClass = regData.get('settings', None)
		if not self.settingsClass or not issubclass(self.settingsClass, BaseSettings):
			raise Exception(f'Missing or invalid settings for module: {self.id}')
		self.settingsInstance = self.settingsClass()
	
	def GetSettings(self) -> BaseSettings:
		return self.settingsInstance

class QAVMPlugin:
	def __init__(self, pluginModule: object) -> None:
		self.module = pluginModule

		self.pluginID = ''
		self.pluginVersion = ''
		self.pluginName = self.module.__name__

		self.softwareHandlers: dict[str, SoftwareHandler] = dict()  # softwareID: SoftwareHandler
		self.settingsHandlers: dict[str, SettingsHandler] = dict()  # moduleID: SettingsHandler

		# First check if plugin contains PLUGIN_ID and PLUGIN_VERSION
		self.pluginID = getattr(self.module, 'PLUGIN_ID', '')
		if not QAVMPlugin.ValidateUID(self.pluginID):
			raise Exception(f'Invalid or missing PLUGIN_ID for: {self.module.__name__}')
		
		self.pluginVersion = getattr(self.module, 'PLUGIN_VERSION', '')
		if not QAVMPlugin.ValidateVersion(self.pluginVersion):
			raise Exception(f'Invalid or missing PLUGIN_VERSION for: {self.module.__name__}')

		self.LoadModuleSoftware()
		self.LoadModuleSettings()
	
	def LoadModuleSoftware(self) -> None:
		pluginSoftwareRegisterFunc = getattr(self.module, 'RegisterModuleSoftware', None)
		if pluginSoftwareRegisterFunc is None or not callable(pluginSoftwareRegisterFunc):
			return
		
		softwareRegDataList = pluginSoftwareRegisterFunc()

		for softwareRegData in softwareRegDataList:
			softwareHandler = SoftwareHandler(self, softwareRegData)

			if softwareHandler.id in self.softwareHandlers:
				raise Exception(f'Duplicate software ID found: {self.id}')
			
			self.softwareHandlers[softwareHandler.id] = softwareHandler
	
	def LoadModuleSettings(self) -> None:
		pluginSettingsRegisterFunc = getattr(self.module, 'RegisterModuleSettings', None)
		if pluginSettingsRegisterFunc is None or not callable(pluginSettingsRegisterFunc):
			return
		
		moduleSettingsRegDataList = pluginSettingsRegisterFunc()

		for moduleSettingsRegData in moduleSettingsRegDataList:
			moduleSettings = SettingsHandler(self, moduleSettingsRegData)
			
			if moduleSettings.id in self.softwareHandlers:
				raise Exception(f'Duplicate module ID found: {self.id}')
			
			self.settingsHandlers[moduleSettings.id] = moduleSettings

	def GetUID(self) -> str:
		return self.pluginID

	def GetName(self) -> str:
		return self.pluginName
	
	def GetVersionStr(self) -> str:
		return self.pluginVersion
	
	def GetVersion(self) -> tuple[int, int, int]:
		return tuple(map(int, self.pluginVersion.split('.')))
	
	def GetSoftwareHandlers(self) -> dict[str, SoftwareHandler]:
		return self.softwareHandlers
	
	def GetSettingsHandlers(self) -> dict[str, SettingsHandler]:
		return self.settingsHandlers
			
	
	
	@staticmethod
	def ValidateUID(UID: str) -> bool:
		# checks id to be in domain-style format
		pattern = re.compile("(?:[a-z0-9](?:[a-z0-9]{0,61}[a-z0-9])?\\.)+[a-z0-9][a-z0-9]{0,61}[a-z0-9]")
		return pattern.match(UID) is not None
	
	@staticmethod
	def ValidateID(ID: str) -> bool:
		# checks id to be in domain-style format + single alphanumrical words
		pattern = re.compile("(?:[a-z0-9](?:[a-z0-9]{0,61}[a-z0-9]\\.)?)+[a-z0-9][a-z0-9]{0,61}[a-z0-9]")
		return pattern.match(ID) is not None
	
	@staticmethod
	def ValidateVersion(version: str) -> bool:
		# version should be in XXX.XXX.XXXX format, where each part can be at least 1 digit long
		pattern = re.compile("(?:[0-9]{1,3}\\.){2}[0-9]{1,4}")
		return pattern.match(version) is not None


class PluginManager:
	def __init__(self, app, pluginsFolderPaths: list[Path]) -> None:
		self.app = app
		self.pluginsFolderPaths: list[Path] = pluginsFolderPaths
		self.plugins: dict[str, QAVMPlugin] = dict()

		defaultPluginsFolderPath = utils.GetDefaultPluginsFolderPath()
		if not defaultPluginsFolderPath.exists():
			defaultPluginsFolderPath.mkdir(parents=True)
			logger.info(f'Created plugins folder: {defaultPluginsFolderPath}')

	def LoadPlugins(self) -> bool:
		for pluginsFolderPath in self.pluginsFolderPaths:
			if not pluginsFolderPath.exists():
				logger.error(f'Plugins folder not found: {pluginsFolderPath}')
				return False

			# Iterate over plugins
			for pluginFolderPath in pluginsFolderPath.iterdir():
				if not pluginFolderPath.is_dir():
					continue
				
				pluginName = pluginFolderPath.name
				pluginMainFile = pluginFolderPath/f'{pluginName}.py'

				if not pluginMainFile.exists():
					logger.error(f'Plugin main file not found: {pluginMainFile}')
					return

				try:
					spec = importlib.util.spec_from_file_location(pluginName, pluginMainFile)
					pluginPyModule = importlib.util.module_from_spec(spec)
					spec.loader.exec_module(pluginPyModule)
					
					plugin = QAVMPlugin(pluginPyModule)
					logger.info(f'Loaded plugin: {pluginName} @ {plugin.GetVersionStr()} ({plugin.GetUID()})')
					self.plugins[plugin.pluginID] = plugin
				
				except:
					logger.exception(f'Failed to load plugin: {pluginMainFile}')
	
	def GetPlugins(self) -> list[QAVMPlugin]:
		return list(self.plugins.values())  # TODO: rewrite with yield
	def GetPlugin(self, pluginID: str) -> QAVMPlugin:
		return self.plugins.get(pluginID, None)


	def GetSoftwareHandlers(self) -> list[tuple[str, str, SoftwareHandler]]:  # TODO: rewrite with yield
		result: list[tuple[str, str, SoftwareHandler]] = []  # [pluginID, softwareID, SoftwareHandler]
		for plugin in self.plugins.values():
			for softwareID, softwareHandler in plugin.GetSoftwareHandlers().items():
				result.append((plugin.pluginID, softwareID, softwareHandler))
		return result
	def GetSoftwareHandler(self, softwareUID: str) -> SoftwareHandler:
		if '#' not in softwareUID:
			return None
		pluginUID, softwareID = softwareUID.split('#')
		plugin = self.GetPlugin(pluginUID)
		if not plugin:
			return None
		return plugin.GetSoftwareHandlers().get(softwareID, None)
	

	def GetSettingsHandlers(self) -> list[tuple[str, str, SettingsHandler]]:
		result: list[tuple[str, str, SettingsHandler]] = []  # [pluginID, moduleID, SettingsHandler]
		for plugin in self.plugins.values():
			for moduleID, settingsHandler in plugin.GetSettingsHandlers().items():
				result.append((plugin.pluginID, moduleID, settingsHandler))
		return result
	def GetSettingsHandler(self, settingsUID: str) -> SettingsHandler:
		if '#' not in settingsUID:
			return None
		pluginUID, moduleID = settingsUID.split('#')
		plugin = self.GetPlugin(pluginUID)
		if not plugin:
			return None
		return plugin.GetSettingsHandlers().get(moduleID, None)