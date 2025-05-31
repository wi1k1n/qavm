import importlib.util, os, re
from pathlib import Path

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings, BaseTableBuilder, BaseContextMenu,
	BaseCustomView, SoftwareBaseSettings
)
import qavm.qavmapi.utils as utils

import qavm.logs as logs
logger = logs.logger

class QAVMHandler:
	""" Base class for QAVM handlers, e.g. is used as base for software handler, settings handler, etc. """
	def __init__(self, plugin, regData):
		self.id = regData.get('id', None)

class QAVMHandlerNamed(QAVMHandler):
	def __init__(self, plugin, regData) -> None:
		super().__init__(plugin, regData)
		self.name = regData.get('name', self.id)
	
	def GetName(self) -> str:
		return self.name

class SoftwareHandler(QAVMHandlerNamed):
	def __init__(self, plugin, regData) -> None:
		super().__init__(plugin, regData)
		
		if not QAVMPlugin.ValidateID(self.id):
			raise Exception(f'Invalid or missing Software ID: {self.id}')
		
		# TODO: lots of repeated code here, refactor

		self.settingsClass = regData.get('settings', None)  # optional
		if not self.settingsClass:
			self.settingsClass = SoftwareBaseSettings
		if not issubclass(self.settingsClass, SoftwareBaseSettings):
			raise Exception(f'Invalid settings for software: {self.id}')
		self.settingsInstance = self.settingsClass(self.id)

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
			
		self.customViews: list[tuple[BaseCustomView.__class__, str]] = []
		customViewsData: list[dict] = regData.get('custom_views', [])
		if customViewsData:
			if not isinstance(customViewsData, list):
				raise Exception(f'Invalid custom views data for software: {self.id}')
			for customViewData in customViewsData:
				customViewName = customViewData.get('name', None)
				customViewClass = customViewData.get('view_class', None)
				if not customViewName or not isinstance(customViewName, str) \
				or not customViewClass or not issubclass(customViewClass, BaseCustomView):
					raise Exception(f'Invalid custom view class for software: {self.id}')
				self.customViews.append((customViewClass, customViewName))

	
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
	
	def GetSettings(self) -> SoftwareBaseSettings:
		return self.settingsInstance
	
	def GetCustomViews(self) -> list[tuple[BaseCustomView.__class__, str]]:
		return self.customViews

# class SettingsHandler(QAVMHandlerNamed):
# 	def __init__(self, plugin, regData) -> None:
# 		super().__init__(plugin, regData)

# 		self.settingsClass = regData.get('settings', None)
# 		if not self.settingsClass or not issubclass(self.settingsClass, BaseSettings):
# 			raise Exception(f'Missing or invalid settings for module: {self.id}')
# 		self.settingsInstance = self.settingsClass()
	
# 	def GetSettings(self) -> BaseSettings:
# 		return self.settingsInstance

class QAVMPlugin:
	"""
	Represents a QAVM plugin.
	QAVM plugins are used to implement functionality that solves specific tasks.
	For example, software handlers handle specific software and automate related tasks.
	"""
	def __init__(self, pluginModule: object) -> None:
		self.module = pluginModule

		self.pluginID = ''
		self.pluginVersion = ''
		self.pluginName = self.module.__name__

		self.softwareHandlers: dict[str, SoftwareHandler] = dict()  # softwareID: SoftwareHandler
		# self.settingsHandlers: dict[str, SettingsHandler] = dict()  # moduleID: SettingsHandler

		# First check if plugin contains PLUGIN_ID and PLUGIN_VERSION
		self.pluginID = getattr(self.module, 'PLUGIN_ID', '')
		if not QAVMPlugin.ValidateUID(self.pluginID):
			raise Exception(f'Invalid or missing PLUGIN_ID for: {self.module.__name__}')
		
		self.pluginVersion = getattr(self.module, 'PLUGIN_VERSION', '')
		if not QAVMPlugin.ValidateVersion(self.pluginVersion):
			raise Exception(f'Invalid or missing PLUGIN_VERSION for: {self.module.__name__}')

		self.LoadModuleSoftware()
		# self.LoadModuleSettings()
	
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
	
	# def LoadModuleSettings(self) -> None:
	# 	pluginSettingsRegisterFunc = getattr(self.module, 'RegisterModuleSettings', None)
	# 	if pluginSettingsRegisterFunc is None or not callable(pluginSettingsRegisterFunc):
	# 		return
		
	# 	moduleSettingsRegDataList = pluginSettingsRegisterFunc()

	# 	for moduleSettingsRegData in moduleSettingsRegDataList:
	# 		moduleSettings = SettingsHandler(self, moduleSettingsRegData)
			
	# 		if moduleSettings.id in self.softwareHandlers:
	# 			raise Exception(f'Duplicate module ID found: {self.id}')
			
	# 		self.settingsHandlers[moduleSettings.id] = moduleSettings

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
	
	# def GetSettingsHandlers(self) -> dict[str, SettingsHandler]:
	# 	return self.settingsHandlers
			
	
	
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
	def __init__(self, app, pluginsFolderPaths: list[Path], pluginPaths: list[Path] = []) -> None:
		self.app = app
		self.pluginsFolderPaths: list[Path] = pluginsFolderPaths
		self.pluginsPaths: list[Path] = pluginPaths  # individual plugins paths

		self.plugins: dict[str, QAVMPlugin] = dict()

		defaultPluginsFolderPath = utils.GetDefaultPluginsFolderPath()
		if not defaultPluginsFolderPath.exists():
			defaultPluginsFolderPath.mkdir(parents=True)
			logger.info(f'Created plugins folder: {defaultPluginsFolderPath}')

	def LoadPlugins(self) -> bool:
		# Iterate over plugins folders first
		for pluginsFolderPath in self.pluginsFolderPaths:
			if not pluginsFolderPath.exists():
				logger.error(f'Plugins folder not found: {pluginsFolderPath}')
				continue
			# Iterate over plugin folders inside current plugins folder
			for pluginPath in pluginsFolderPath.iterdir():
				if not pluginPath.is_dir():
					continue
				logger.info(f'Loading plugin from path: {pluginPath.resolve().absolute()}')
				if not self.LoadPluginFromPath(pluginPath):
					logger.error(f'Failed to load plugin from path: {pluginPath}')
					continue

		# Iterate over individual plugin paths
		for pluginPath in self.pluginsPaths:
			if not pluginPath.is_dir():
				continue
			if not self.LoadPluginFromPath(pluginPath):
				logger.error(f'Failed to load plugin from path: {pluginPath}')
				continue

	def LoadPluginFromPath(self, pluginPath: Path) -> bool:
		pluginName = pluginPath.name
		pluginMainFile = pluginPath/f'{pluginName}.py'

		if not pluginMainFile.exists():
			logger.error(f'Plugin main file not found: {pluginMainFile}')
			return False

		try:
			spec = importlib.util.spec_from_file_location(pluginName, pluginMainFile)
			pluginPyModule = importlib.util.module_from_spec(spec)
			spec.loader.exec_module(pluginPyModule)
			
			plugin = QAVMPlugin(pluginPyModule)
			logger.info(f'Loaded plugin: {pluginName} @ {plugin.GetVersionStr()} ({plugin.GetUID()})')
			self.plugins[plugin.pluginID] = plugin
		except:
			logger.exception(f'Failed to load plugin: {pluginMainFile}')
			return False
		return True
	
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
	
	def GetCurrentSoftwareHandler(self) -> SoftwareHandler:
		qavmSettings = self.app.GetSettingsManager().GetQAVMSettings()
		return self.GetSoftwareHandler(qavmSettings.GetSelectedSoftwareUID())
	

	# def GetSettingsHandlers(self) -> list[tuple[str, str, SettingsHandler]]:
	# 	result: list[tuple[str, str, SettingsHandler]] = []  # [pluginID, moduleID, SettingsHandler]
	# 	for plugin in self.plugins.values():
	# 		for moduleID, settingsHandler in plugin.GetSettingsHandlers().items():
	# 			result.append((plugin.pluginID, moduleID, settingsHandler))
	# 	return result
	# def GetSettingsHandler(self, settingsUID: str) -> SettingsHandler:
	# 	if '#' not in settingsUID:
	# 		return None
	# 	pluginUID, moduleID = settingsUID.split('#')
	# 	plugin = self.GetPlugin(pluginUID)
	# 	if not plugin:
	# 		return None
	# 	return plugin.GetSettingsHandlers().get(moduleID, None)