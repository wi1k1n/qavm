import importlib.util, os, re
from pathlib import Path
from typing import Type

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings, BaseTableBuilder, BaseContextMenu,
	BaseCustomView, SoftwareBaseSettings, BaseMenuItems, 
)
import qavm.qavmapi.utils as utils

from PyQt6.QtWidgets import QApplication

import qavm.logs as logs
logger = logs.logger


class SoftwareHandler:
	def __init__(self, plugin, regData) -> None:
		self._initRegDataNew(regData)

	def _initRegDataNew(self, regData: dict) -> None:
		########################### ID ###########################
		self.id: str = regData.get('id', '')
		self._checkType(self.id, str, 'software ID')
		if not QAVMPlugin.ValidateID(self.id):
			raise Exception(f'Invalid Software ID: {self.id}')
		
		########################### Name ###########################
		self.name: str = regData.get('name', self.id)
		self._checkType(self.name, str, 'software name')
		
		########################### Descriptors ###########################
		self.descriptorClasses: dict[str, tuple[BaseQualifier, Type[BaseDescriptor]]] = dict()  # descriptorTypeId: (qualifierClass, descriptorClass)

		descTypesData: dict = regData.get('descriptors', {})
		self._checkType(descTypesData, dict, 'descriptors')
		for descTypeId, descType in descTypesData.items():
			self._checkType(descTypeId, str, 'descriptor type ID')
			self._checkType(descType, dict, 'descriptor type data')
			qualifierClass = descType.get('qualifier', None)
			self._checkSubClass(qualifierClass, BaseQualifier, 'qualifier class')
			descriptorClass = descType.get('descriptor', None)
			self._checkSubClass(descriptorClass, BaseDescriptor, 'descriptor class')
			
			self.descriptorClasses[descTypeId] = (qualifierClass(), descriptorClass)

		########################### Views ###########################
		self.tileBuilderClasses: dict[str, Type[BaseTileBuilder]] = dict()  # viewTypeId: tileBuilderClass
		self.tableBuilderClasses: dict[str, Type[BaseTableBuilder]] = dict()  # viewTypeId: tableBuilderClass
		self.customViewClasses: dict[str, Type[BaseCustomView]] = dict()  # viewTypeId: customViewClass

		viewsData: dict = regData.get('views', {})
		self._checkType(viewsData, dict, 'views')
		
		tileViewsData: dict = viewsData.get('tiles', {})
		self._checkType(tileViewsData, dict, 'tile views')
		for viewTypeId, tileBuilderClass in tileViewsData.items():
			self._checkType(viewTypeId, str, 'tile view type ID')
			self._checkSubClass(tileBuilderClass, BaseTileBuilder, 'tile builder class')
			self.tileBuilderClasses[viewTypeId] = tileBuilderClass

		tableViewsData: dict = viewsData.get('table', {})
		self._checkType(tableViewsData, dict, 'table views')
		for viewTypeId, tableBuilderClass in tableViewsData.items():
			self._checkType(viewTypeId, str, 'table view type ID')
			self._checkSubClass(tableBuilderClass, BaseTableBuilder, 'table builder class')
			self.tableBuilderClasses[viewTypeId] = tableBuilderClass

		customViewsData: dict = viewsData.get('custom', {})
		self._checkType(customViewsData, dict, 'custom views')
		for viewTypeId, customViewClass in customViewsData.items():
			self._checkType(viewTypeId, str, 'custom view type ID')
			self._checkSubClass(customViewClass, BaseCustomView, 'custom view class')
			self.customViewClasses[viewTypeId] = customViewClass

		########################### Settings ###########################
		self.settingsClass: Type[BaseSettings] = regData.get('settings', None)
		self.settingsInstance: BaseSettings | None = None
		if self.settingsClass is not None:  # optional
			self._checkSubClass(self.settingsClass, BaseSettings, 'settings class')
			self.settingsInstance = self.settingsClass(self.GetID())

		########################### MenuItems ###########################
		self.menuItemsClass: Type[BaseMenuItems] | None = regData.get('menuitems', None)
		self.menuItemsInstance: BaseMenuItems | None = None
		if self.menuItemsClass is not None:  # optional
			self._checkSubClass(self.menuItemsClass, BaseMenuItems, 'menu items class')
			self.menuItemsInstance = self.menuItemsClass(self.settingsInstance)
			
	def _checkType(self, value: object, expectedType: type, name: str) -> None:
		if not isinstance(value, expectedType):
			raise Exception(f'Invalid {name} type for software: {self.id}. Expected {expectedType.__name__}, got {type(value).__name__}')
		
	def _checkSubClass(self, value: object, expectedType: type, name: str) -> None:
		if not issubclass(value, expectedType):
			raise Exception(f'Invalid {name} class for software: {self.id}. Expected subclass of {expectedType.__name__}, got {value.__name__}')


	def GetName(self) -> str:
		""" Returns the name of the software handler, e.g. 'Example SW' """
		return self.name
	
	def GetID(self) -> str:
		""" Returns the unique identifier of the software handler, e.g. 'software.example1' """
		return self.id

	def GetDescriptorClasses(self) -> dict[str, tuple[BaseQualifier, Type[BaseDescriptor]]]:
		""" Returns a dictionary of descriptor classes registered by the software handler, e.g. {'descriptor_type_id': (BaseQualifier, BaseDescriptor.__class__)} """
		return self.descriptorClasses
	
	def GetDescriptorClass(self, descriptorTypeId: str) -> tuple[BaseQualifier | None, Type[BaseDescriptor] | None]:
		""" Returns the descriptor class for the given descriptor type ID, e.g. ('BaseQualifier', 'BaseDescriptor') """
		return self.descriptorClasses.get(descriptorTypeId, (None, None))
	
	def GetTileBuilderClasses(self) -> dict[str, Type[BaseTileBuilder]]:
		""" Returns a dictionary of tile builder classes registered by the software handler, e.g. {'view_type_id': BaseTileBuilder} """
		return self.tileBuilderClasses
	
	def GetTileBuilderClass(self, viewTypeId: str) -> Type[BaseTileBuilder] | None:
		""" Returns the tile builder class for the given view type ID, e.g. 'BaseTileBuilder' """
		return self.tileBuilderClasses.get(viewTypeId, None)
	
	def GetTableBuilderClasses(self) -> dict[str, Type[BaseTableBuilder]]:
		""" Returns a dictionary of table builder classes registered by the software handler, e.g. {'view_type_id': BaseTableBuilder} """
		return self.tableBuilderClasses
	
	def GetTableBuilderClass(self, viewTypeId: str) -> Type[BaseTableBuilder] | None:
		""" Returns the table builder class for the given view type ID, e.g. 'BaseTableBuilder' """
		return self.tableBuilderClasses.get(viewTypeId, None)
	
	def GetCustomViewClasses(self) -> dict[str, Type[BaseCustomView]]:
		""" Returns a dictionary of custom view classes registered by the software handler, e.g. {'view_type_id': BaseCustomView} """
		return self.customViewClasses
	
	def GetCustomViewClass(self, viewTypeId: str) -> Type[BaseCustomView] | None:
		""" Returns the custom view class for the given view type ID, e.g. 'BaseCustomView' """
		return self.customViewClasses.get(viewTypeId, None)
	
	def GetSettings(self) -> BaseSettings | None:
		""" Returns the settings class registered by the software handler, e.g. 'BaseSettings' or None if not set """
		return self.settingsInstance
	
	def GetMenuItems(self) -> BaseMenuItems | None:
		""" Returns the menu items class registered by the software handler, e.g. 'BaseMenuItems' or None if not set """
		return self.menuItemsInstance

class QAVMPlugin:
	"""
	Represents a QAVM plugin.
	QAVM plugins are used to implement functionality that solves specific tasks.
	For example, software handlers handle specific software and automate related tasks.
	"""
	def __init__(self, pluginModule: object, pluginExecutablePath: Path) -> None:
		self.module = pluginModule
		self.pluginExecutablePath: Path = pluginExecutablePath.resolve().absolute()

		self.pluginID = ''
		self.pluginVersion = ''
		self.pluginPackageName = self.module.__name__

		self.softwareHandlers: dict[str, SoftwareHandler] = dict()  # softwareID: SoftwareHandler
		# self.settingsHandlers: dict[str, SettingsHandler] = dict()  # moduleID: SettingsHandler

		# PLUGIN_ID and PLUGIN_VERSION are required
		self.pluginID = getattr(self.module, 'PLUGIN_ID', '')
		if not QAVMPlugin.ValidateUID(self.pluginID):
			raise Exception(f'Invalid or missing PLUGIN_ID for: {self.module.__name__}')
		
		self.pluginVersion = getattr(self.module, 'PLUGIN_VERSION', '')
		if not QAVMPlugin.ValidateVersion(self.pluginVersion):
			raise Exception(f'Invalid or missing PLUGIN_VERSION for: {self.module.__name__}')
		
		# These are optional
		self.pluginVariant = getattr(self.module, 'PLUGIN_VARIANT', '')
		self.pluginName = getattr(self.module, 'PLUGIN_NAME', self.pluginPackageName)
		self.pluginDeveloper = getattr(self.module, 'PLUGIN_DEVELOPER', 'Unknown')
		self.pluginWebsite = getattr(self.module, 'PLUGIN_WEBSITE', '')

		self.LoadModuleSoftware()
	
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
	
	def GetSoftwareHandlers(self) -> dict[str, SoftwareHandler]:
		""" Returns a dictionary of software handlers registered by the plugin, e.g. {'software_id': SoftwareHandler} """
		return self.softwareHandlers

	def GetUID(self) -> str:
		""" Returns the unique identifier of the plugin, e.g. 'com.example.plugin' """
		return self.pluginID
	
	def GetName(self) -> str:
		""" Returns the name of the plugin, e.g. 'Example Plugin'. Returns Package name if not set. """
		return self.pluginName
	
	def GetVersionStr(self) -> str:
		""" Returns the version of the plugin as a string, e.g. '0.1.0' """
		return self.pluginVersion
	
	def GetVersion(self) -> tuple[int, int, int]:
		""" Returns the version of the plugin as a tuple of integers, e.g. (0, 1, 0) """
		return tuple(map(int, self.pluginVersion.split('.')))

	def GetPluginPackageName(self) -> str:
		""" Returns the package name of the plugin (the plugin folder name), e.g. 'example_plugin' """
		return self.pluginPackageName
	
	def GetExecutablePath(self) -> Path:
		""" Returns the absolute path to the plugin executable file, e.g. '/path/to/plugin/example_plugin.py' """
		return self.pluginExecutablePath
	
	def GetPluginVariant(self) -> str:
		""" Returns the variant of the plugin (can be empty), e.g. 'Alpha', 'Beta', 'Stable' """
		return self.pluginVariant

	def GetPluginDeveloper(self) -> str:
		""" Returns the name of the plugin developer (can be empty), e.g. 'John Doe' """
		return self.pluginDeveloper
	
	def GetPluginWebsite(self) -> str:
		""" Returns the website of the plugin (can be empty), e.g. 'https://example.com/plugin' """
		return self.pluginWebsite
			
	
	@staticmethod
	def FetchPluginIDFromUID(UID: str) -> str:
		# extracts plugin ID from UID, e.g. 'com.example.plugin#software_id' -> 'com.example.plugin'
		if not QAVMPlugin.ValidateUID(UID):
			raise ValueError(f'Invalid UID format: {UID}')
		return UID.split('#')[0]
	
	@staticmethod
	def FetchIDFromUID(UID: str) -> str:
		# extracts ID from UID, e.g. 'com.example.plugin#software_id' -> 'software_id'
		if not QAVMPlugin.ValidateUID(UID):
			raise ValueError(f'Invalid UID format: {UID}')
		return UID.split('#')[1] if '#' in UID else ''
	
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
	def __init__(self, pluginPaths: set[Path], pluginsFolderPaths: list[Path]) -> None:
		self.pluginsFolderPaths: list[Path] = pluginsFolderPaths
		self.pluginsPaths: list[Path] = pluginPaths  # individual plugins paths

		self.plugins: dict[str, QAVMPlugin] = dict()

		defaultPluginsFolderPath = utils.GetDefaultPluginsFolderPath()
		if not defaultPluginsFolderPath.exists():
			defaultPluginsFolderPath.mkdir(parents=True)
			logger.info(f'Created plugins folder: {defaultPluginsFolderPath}')

	def LoadPlugins(self) -> bool:
		# Iterate over individual plugin paths
		for pluginPath in self.pluginsPaths:
			if not pluginPath.is_dir():
				continue
			if not self.LoadPluginFromPath(pluginPath):
				logger.error(f'Failed to load plugin from path: {pluginPath}')
				continue

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
			
			plugin = QAVMPlugin(pluginPyModule, pluginMainFile)
			if plugin.pluginID in self.plugins:
				logger.error(f'Duplicate plugin ID found: {plugin.pluginID} ({pluginName})')
				return False
			
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
		if '#' not in softwareUID:  # TODO: make related Validate method
			return None
		pluginUID, softwareID = softwareUID.split('#')
		plugin = self.GetPlugin(pluginUID)
		if not plugin:
			return None
		return plugin.GetSoftwareHandlers().get(softwareID, None)
	
	def GetCurrentSoftwareHandler(self) -> SoftwareHandler:
		app = QApplication.instance()
		qavmSettings = app.GetSettingsManager().GetQAVMSettings()
		return self.GetSoftwareHandler(qavmSettings.GetSelectedSoftwareUID())