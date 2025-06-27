from __future__ import annotations
import importlib.util, os, re
from pathlib import Path
from typing import Type, Optional, Any

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings, BaseTableBuilder,
	BaseCustomView, SoftwareBaseSettings, BaseMenuItem, 
)
import qavm.qavmapi.utils as utils

from PyQt6.QtWidgets import QApplication

# from qavm.manager_plugin import QAVMWorkspace

import qavm.logs as logs
logger = logs.logger
import re
from typing import Optional

# TODO: having double # in the full UID was a bad idea. Switch to having different separator symbols.
# For example, use `:` as a separator between plugin and software IDs, and `#` for software IDs and data paths.
class UID:
	"""
	UIDs are in the format: 'plugin.id#software.id#data/path'
	- plugin.id: e.g. 'com.example.plugin'
	- software.id: e.g. 'software.example1'
	- data/path: e.g. 'view/tiles/c4d'
	Supports wildcard matching (* and ?) in the data path.
	"""

	DOMAIN_ID_REGEX = r'[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*'
	DATAPATH_REGEX = r'[a-zA-Z0-9_\-\*\?]+(?:/[a-zA-Z0-9_\-\*\?]+)*'
	
	DOMAIN_ID_PATTERN = re.compile(f'^{DOMAIN_ID_REGEX}$')
	DATAPATH_PATTERN = re.compile(f'^{DATAPATH_REGEX}$')
	UID_PATTERN = re.compile(f'^({DOMAIN_ID_REGEX})#({DOMAIN_ID_REGEX})#({DATAPATH_REGEX})$')
	PLUGIN_SOFTWARE_PATTERN = re.compile(f'^({DOMAIN_ID_REGEX})#({DOMAIN_ID_REGEX})$')
	SOFTWARE_DATAPATH_PATTERN = re.compile(f'^({DOMAIN_ID_REGEX})#({DATAPATH_REGEX})$')

	WILDCARD_SAFE_CHARS = '[a-zA-Z0-9_\\-/]'

	@staticmethod
	def _datapath_wildcard_to_regex(pattern: str) -> str:
		"""Convert pattern with * and ? to regex limited to UID-safe characters + slashes."""		
		regex = ''
		for char in pattern:
			if char == '*':
				regex += f'{UID.WILDCARD_SAFE_CHARS}*'
			elif char == '?':
				regex += f'{UID.WILDCARD_SAFE_CHARS}'
			else:
				regex += re.escape(char)
		return f'^{regex}$'

	@staticmethod
	def IsPluginIDValid(plugin_id: str) -> bool:
		""" Checks if the plugin ID is valid, e.g. 'com.example.plugin' """
		return UID.DOMAIN_ID_PATTERN.fullmatch(plugin_id) is not None

	@staticmethod
	def IsSoftwareIDValid(software_id: str) -> bool:
		""" Checks if the software ID is valid, e.g. 'software.example1' """
		return UID.DOMAIN_ID_PATTERN.fullmatch(software_id) is not None

	@staticmethod
	def IsDataPathValid(data_path: str) -> bool:
		""" Checks if the data path is valid, e.g. 'view/tiles/c4d' """
		return UID.DATAPATH_PATTERN.fullmatch(data_path) is not None

	@staticmethod
	def IsUIDValid(uid: str) -> bool:
		""" Checks if the UID is valid, e.g. 'com.example.plugin#software.example1#view/tiles/c4d' """
		return UID.UID_PATTERN.fullmatch(uid) is not None

	@staticmethod
	def IsPluginSoftwareIDValid(uid: str) -> bool:
		""" Checks if the UID is a valid Plugin#Software ID, e.g. 'com.example.plugin#software.example1' """
		return UID.PLUGIN_SOFTWARE_PATTERN.fullmatch(uid) is not None

	@staticmethod
	def IsSoftwareIDDataPathValid(uid: str) -> bool:
		""" Checks if the UID is a valid Software#DataPath ID, e.g. 'software.example1#view/tiles/c4d' """
		return UID.SOFTWARE_DATAPATH_PATTERN.fullmatch(uid) is not None

	@staticmethod
	def FetchPluginID(uid: str) -> Optional[str]:
		""" Fetches the plugin ID from a UID string, e.g. 'com.example.plugin#software.example1#view/tiles/c4d' -> 'com.example.plugin' """
		parts = uid.split('#')
		if len(parts) == 3 and UID.IsPluginIDValid(parts[0]):
			return parts[0]
		if len(parts) == 2:
			# Could be Plugin#Software or Software#DataPath
			if UID.IsPluginSoftwareIDValid(uid):
				return parts[0]
			if UID.IsSoftwareIDDataPathValid(uid):
				return None
			return None
		return uid if UID.IsPluginIDValid(uid) else None

	@staticmethod
	def FetchSoftwareID(uid: str) -> Optional[str]:
		""" Fetches the software ID from a UID string, e.g. 'com.example.plugin#software.example1#view/tiles/c4d' -> 'software.example1' """
		parts = uid.split('#')
		if len(parts) == 3 and UID.IsSoftwareIDValid(parts[1]):
			return parts[1]
		if len(parts) == 2:
			# Could be Plugin#Software or Software#DataPath
			if UID.IsPluginSoftwareIDValid(uid):
				return parts[1]
			if UID.IsSoftwareIDDataPathValid(uid):
				return parts[0]
		return uid if UID.IsSoftwareIDValid(uid) else None

	@staticmethod
	def FetchDataPath(uid: str) -> Optional[str]:
		""" Fetches the data path from a UID string, e.g. 'com.example.plugin#software.example1#view/tiles/c4d' -> 'view/tiles/c4d' """
		parts = uid.split('#')
		if len(parts) == 3 and UID.IsDataPathValid(parts[2]):
			return parts[2]
		if len(parts) == 2 and UID.IsSoftwareIDDataPathValid(uid):
			return parts[1]
		return uid if UID.IsDataPathValid(uid) else None

	@staticmethod
	def FetchPluginSoftwareID(uid: str) -> Optional[str]:
		""" Fetches the Plugin#Software ID from a UID string, e.g. 'com.example.plugin#software.example1#view/tiles/c4d' -> 'com.example.plugin#software.example1' """
		if UID.IsPluginSoftwareIDValid(uid):
			return uid
		parts = uid.split('#')
		if len(parts) == 3:
			return f"{parts[0]}#{parts[1]}" if UID.IsPluginIDValid(parts[0]) and UID.IsSoftwareIDValid(parts[1]) else None
		return None

	@staticmethod
	def FetchSoftwareIDDataPath(uid: str) -> Optional[str]:
		""" Fetches the Software#DataPath ID from a UID string, e.g. 'com.example.plugin#software.example1#view/tiles/c4d' -> 'software.example1#view/tiles/c4d' """
		if UID.IsSoftwareIDDataPathValid(uid):
			return uid
		parts = uid.split('#')
		if len(parts) == 3:
			return f"{parts[1]}#{parts[2]}" if UID.IsSoftwareIDValid(parts[1]) and UID.IsDataPathValid(parts[2]) else None
		return None
	
	@staticmethod
	def IsDataPathWildcard(dataPath: str) -> bool:
		""" Checks if the data path contains wildcards (* or ?). """
		if dPath := UID.FetchDataPath(dataPath):
			return '*' in dPath or '?' in dPath
		return False

	@staticmethod
	def MatchDataPath(pattern: str, path: str) -> bool:
		"""Checks if a data path matches the wildcard pattern."""
		regex = re.compile(UID._datapath_wildcard_to_regex(pattern))
		return regex.fullmatch(path) is not None

	@staticmethod
	def DataPathGetParts(dataPath: str) -> list[str]:
		""" Returns the parts of the data path as a list, e.g. 'view/tiles/c4d' -> ['view', 'tiles', 'c4d'] """
		if dataPathFetched := UID.FetchDataPath(dataPath):
			return dataPathFetched.split('/')
		return []

	@staticmethod
	def DataPathGetFirstPart(dataPath: str) -> Optional[str]:
		""" Returns the first part of the data path, e.g. 'view/tiles/c4d' -> 'view' """
		if dataPathFetched := UID.FetchDataPath(dataPath):
			parts = dataPathFetched.split('/')
			return parts[0] if parts else None
		return None

	@staticmethod
	def DataPathGetLastPart(dataPath: str) -> Optional[str]:
		""" Returns the last part of the data path, e.g. 'view/tiles/c4d' -> 'c4d' """
		if dataPathFetched := UID.FetchDataPath(dataPath):
			parts = dataPathFetched.split('/')
			return parts[-1] if parts else None
		return None

# TODO: move this to qavmapi and make use of it
class SerializableBase(object):
	def Serialize(self) -> Any:
		""" Serializes the object to a format suitable for being stored as json. """
		raise NotImplementedError("Serialize method should be implemented in subclasses.")
	
	@staticmethod
	def Deserialize(data: Any) -> SerializableBase:
		""" Deserializes the object from json. """
		raise NotImplementedError("Deserialize method should be implemented in subclasses.")

class QAVMWorkspace(SerializableBase):
	def __init__(self, data: list[str] = [], name: str = '') -> None:
		self.name: str = name
		
		self.tiles: list[str] = []
		self.table: list[str] = []
		self.custom: list[str] = []
		self.menuItems: list[str] = []

		for uid in data:
			if not isinstance(uid, str):
				raise ValueError("Invalid workspace data: all view UIDs should be strings.")

			plID: str = UID.FetchPluginID(uid)
			if not plID:
				raise ValueError(f"Invalid workspace item UID '{uid}': plugin ID is missing or invalid.")

			if dataPath := UID.FetchDataPath(uid):
				parts: list[str] = UID.DataPathGetParts(dataPath)
				if not parts:
					raise ValueError(f"Invalid view UID '{uid}': data path is empty.")
				if parts[0] == 'views':
					if len(parts) < 2:
						raise ValueError(f"Invalid view UID '{uid}': missing view type.")
					if parts[1] == 'tiles':
						self.tiles.append(uid)
					elif parts[1] == 'table':
						self.table.append(uid)
					elif parts[1] == 'custom':
						self.custom.append(uid)
				elif parts[0] == 'menuitems':
					self.menuItems.append(uid)

	def GetName(self) -> str:
		return self.name

	def IsEmpty(self) -> bool:
		""" Returns True if the workspace has no views or menu items. """
		return not self.tiles and not self.table and not self.custom and not self.menuItems
	
	def GetInvolvedPlugins(self) -> tuple[set[QAVMPlugin], set[str]]:
		""" Returns a set of loaded plugins involved in the workspace views (and a set of plugins that were not found). """
		plugins: set[QAVMPlugin] = set()
		notFoundPlugins: set[str] = set()

		# TODO: make it more generic (in case new view types are added in the future)
		tiles, tilesNotFound = self._getInvolvedPluginsUIDs(self.tiles)
		table, tableNotFound = self._getInvolvedPluginsUIDs(self.table)
		custom, customNotFound = self._getInvolvedPluginsUIDs(self.custom)

		plugins.update(tiles)
		plugins.update(table)
		plugins.update(custom)
		notFoundPlugins.update(tilesNotFound)
		notFoundPlugins.update(tableNotFound)
		notFoundPlugins.update(customNotFound)

		return plugins, notFoundPlugins

	def GetInvolvedSoftwareHandlers(self) -> tuple[set[SoftwareHandler], set[str]]:
		""" Returns a set of software handlers involved in the workspace views (and a set of plugins that were not found). """
		plugins, notFoundPlugins = self.GetInvolvedPlugins()
		softwareHandlers: set[SoftwareHandler] = set()
		for plugin in plugins:
			softwareHandlers.update(plugin.GetSoftwareHandlers().values())
		return softwareHandlers, notFoundPlugins
	
	def GetTilesViews(self) -> dict[SoftwareHandler, list[str]]:  # -> {SoftwareHandler: [viewUIDs]}
		""" Returns tiles views in current workspace grouped by software handlers. """
		return self._getItems(self.tiles)
	
	def GetTableViews(self) -> dict[SoftwareHandler, list[str]]:  # -> {SoftwareHandler: [viewUIDs]}
		""" Returns table views in current workspace grouped by software handlers. """
		return self._getItems(self.table)
	
	def GetCustomViews(self) -> dict[SoftwareHandler, list[str]]:  # -> {SoftwareHandler: [viewUIDs]}
		""" Returns custom views in current workspace grouped by software handlers. """
		return self._getItems(self.custom)
	
	def GetMenuItems(self) -> dict[SoftwareHandler, list[str]]:  # -> {SoftwareHandler: [viewUIDs]}
		""" Returns menu items in current workspace grouped by software handlers. """
		return self._getItems(self.menuItems)
	
	def Serialize(self) -> list[str]:
		""" Serializes the workspace to a list of view UIDs. """
		data: list[str] = []
		data.extend(self.tiles)
		data.extend(self.table)
		data.extend(self.custom)
		data.extend(self.menuItems)
		return data
	
	@staticmethod
	def Deserialize(data: list[str]) -> QAVMWorkspace:
		""" Deserializes the workspace from a list of view UIDs. """
		return QAVMWorkspace(data)
	
	def _getItems(self, itemUIDs: list[str]) -> dict[SoftwareHandler, list[str]]:  # -> {SoftwareHandler: [itemUIDs]}
		items: dict[SoftwareHandler, list[str]] = {}
		for itemUID in itemUIDs:
			if plugin := QApplication.instance().GetPluginManager().GetPlugin(itemUID):
				if swHandler := plugin.GetSoftwareHandler(itemUID):
					if swHandler not in items:
						items[swHandler] = []
					items[swHandler].append(itemUID)
		return items
	
	def _getInvolvedPluginsUIDs(self, uids: list[str]) -> tuple[set[QAVMPlugin], set[str]]:
		app = QApplication.instance()
		pluginManager: PluginManager = app.GetPluginManager()
		plugins: set[QAVMPlugin] = set()
		notFoundPlugins: set[str] = set()
		for viewUID in uids:
			if plugin := pluginManager.GetPlugin(viewUID):
				plugins.add(plugin)
			else:
				notFoundPlugins.add(viewUID)
		return plugins, notFoundPlugins

class SoftwareHandler:
	# TODO: should be a unified dataPath accessing scheme (check UID class for IsDataPathValid, etc...)
	KEY_DESCRIPTORS = 'descriptors'
	KEY_VIEWS = 'views'
	KEY_TILES = 'tiles'
	KEY_TABLE = 'table'
	KEY_CUSTOM = 'custom'
	KEY_SETTINGS = 'settings'
	KEY_MENUITEMS = 'menuitems'

	def __init__(self, regData: dict) -> None:
		########################### ID ###########################
		self.id: str = regData.get('id', '')
		self._checkType(self.id, str, 'software ID')
		if not UID.IsSoftwareIDValid(self.id):
			raise Exception(f'Invalid Software ID: {self.id}')
		
		########################### Name ###########################
		self.name: str = regData.get('name', self.id)
		self._checkType(self.name, str, 'software name')
		
		########################### Descriptors ###########################
		self.descriptorClasses: dict[str, tuple[BaseQualifier, Type[BaseDescriptor]]] = dict()  # descriptorTypeId: (qualifierClass, descriptorClass)

		descTypesData: dict = regData.get(self.KEY_DESCRIPTORS, {})
		self._checkType(descTypesData, dict, self.KEY_DESCRIPTORS)
		for descTypeId, descType in descTypesData.items():
			self._checkType(descTypeId, str, 'descriptor type ID')
			self._checkType(descType, dict, 'descriptor type data')
			qualifierClass = descType.get('qualifier', None)
			self._checkSubClass(qualifierClass, BaseQualifier, 'qualifier class')
			descriptorClass = descType.get('descriptor', None)
			self._checkSubClass(descriptorClass, BaseDescriptor, 'descriptor class')
			
			self.descriptorClasses[f'{self.KEY_DESCRIPTORS}/{descTypeId}'] = (qualifierClass(), descriptorClass)

		########################### Views ###########################
		self.tileBuilderClasses: dict[str, Type[BaseTileBuilder]] = dict()  # viewTypeId: tileBuilderClass
		self.tableBuilderClasses: dict[str, Type[BaseTableBuilder]] = dict()  # viewTypeId: tableBuilderClass
		self.customViewClasses: dict[str, Type[BaseCustomView]] = dict()  # viewTypeId: customViewClass

		viewsData: dict = regData.get(self.KEY_VIEWS, {})
		self._checkType(viewsData, dict, self.KEY_VIEWS)
		
		tileViewsData: dict = viewsData.get(self.KEY_TILES, {})
		self._checkType(tileViewsData, dict, self.KEY_TILES)
		for viewTypeId, tileBuilderClass in tileViewsData.items():
			self._checkType(viewTypeId, str, 'tile view type ID')
			self._checkSubClass(tileBuilderClass, BaseTileBuilder, 'tile builder class')
			self.tileBuilderClasses[f'{self.KEY_VIEWS}/{self.KEY_TILES}/{viewTypeId}'] = tileBuilderClass

		tableViewsData: dict = viewsData.get(self.KEY_TABLE, {})
		self._checkType(tableViewsData, dict, self.KEY_TABLE)
		for viewTypeId, tableBuilderClass in tableViewsData.items():
			self._checkType(viewTypeId, str, 'table view type ID')
			self._checkSubClass(tableBuilderClass, BaseTableBuilder, 'table builder class')
			self.tableBuilderClasses[f'{self.KEY_VIEWS}/{self.KEY_TABLE}/{viewTypeId}'] = tableBuilderClass

		customViewsData: dict = viewsData.get(self.KEY_CUSTOM, {})
		self._checkType(customViewsData, dict, self.KEY_CUSTOM)
		for viewTypeId, customViewClass in customViewsData.items():
			self._checkType(viewTypeId, str, 'custom view type ID')
			self._checkSubClass(customViewClass, BaseCustomView, 'custom view class')
			self.customViewClasses[f'{self.KEY_VIEWS}/{self.KEY_CUSTOM}/{viewTypeId}'] = customViewClass

		########################### Settings ###########################
		self.settingsClass: Optional[Type[BaseSettings]] = regData.get(self.KEY_SETTINGS, None)
		self.settingsInstance: Optional[BaseSettings] = None  # TODO: allow to use without settings (fallback to BaseSettings?)
		if self.settingsClass is not None:  # optional
			self._checkSubClass(self.settingsClass, BaseSettings, self.KEY_SETTINGS)
			self.settingsInstance = self.settingsClass(self.GetID())

		########################### MenuItems ###########################
		self.menuItems: dict[str, BaseMenuItem] = dict()  # menuItemTypeId: menuItemInstance

		menuItemsData: dict = regData.get(self.KEY_MENUITEMS, {})
		self._checkType(menuItemsData, dict, self.KEY_MENUITEMS)
		for menuItemTypeId, menuItemClass in menuItemsData.items():
			self._checkType(menuItemTypeId, str, 'menu item type ID')
			self._checkSubClass(menuItemClass, BaseMenuItem, 'menu items class')
			self.menuItems[f'{self.KEY_MENUITEMS}/{menuItemTypeId}'] = menuItemClass(self.settingsInstance)
			
	def _checkType(self, value: object, expectedType: type, name: str) -> None:
		# TODO: move to some plugins utils module
		if not isinstance(value, expectedType):
			raise Exception(f'Invalid {name} type for software: {self.id}. Expected {expectedType.__name__}, got {type(value).__name__}')
		
	def _checkSubClass(self, value: type, expectedType: type, name: str) -> None:
		# TODO: move to some plugins utils module
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
		if descTypeId := UID.FetchDataPath(descriptorTypeId):
			return self.descriptorClasses.get(f'{self.KEY_DESCRIPTORS}/{descTypeId}', (None, None))
		return None, None
	
	def GetTileBuilderClasses(self) -> dict[str, Type[BaseTileBuilder]]:
		""" Returns a dictionary of tile builder classes registered by the software handler, e.g. {'view_type_id': BaseTileBuilder} """
		return self.tileBuilderClasses
	
	def GetTileBuilderClass(self, viewTypeId: str) -> Type[BaseTileBuilder] | None:
		""" Returns the tile builder class for the given view type ID, e.g. 'BaseTileBuilder' """
		if viewTypeId := UID.FetchDataPath(viewTypeId):
			return self.tileBuilderClasses.get(viewTypeId, None)
		return None
	
	def GetTableBuilderClasses(self) -> dict[str, Type[BaseTableBuilder]]:
		""" Returns a dictionary of table builder classes registered by the software handler, e.g. {'view_type_id': BaseTableBuilder} """
		return self.tableBuilderClasses
	
	def GetTableBuilderClass(self, viewTypeId: str) -> Type[BaseTableBuilder] | None:
		""" Returns the table builder class for the given view type ID, e.g. 'BaseTableBuilder' """
		if viewTypeId := UID.FetchDataPath(viewTypeId):
			return self.tableBuilderClasses.get(viewTypeId, None)
		return None
	
	def GetCustomViewClasses(self) -> dict[str, Type[BaseCustomView]]:
		""" Returns a dictionary of custom view classes registered by the software handler, e.g. {'view_type_id': BaseCustomView} """
		return self.customViewClasses
	
	def GetCustomViewClass(self, viewTypeId: str) -> Type[BaseCustomView] | None:
		""" Returns the custom view class for the given view type ID, e.g. 'BaseCustomView' """
		if viewTypeId := UID.FetchDataPath(viewTypeId):
			return self.customViewClasses.get(viewTypeId, None)
		return None
	
	def GetSettings(self) -> BaseSettings | None:
		""" Returns the settings class registered by the software handler, e.g. 'BaseSettings' or None if not set """
		return self.settingsInstance
	
	def GetMenuItems(self) -> dict[str, BaseMenuItem]:
		""" Returns a dictionary of menu items registered by the software handler, e.g. {'menu_item_type_id': BaseMenuItem} """
		return self.menuItems
	
	def GetMenuItem(self, menuItemTypeId: str) -> BaseMenuItem | None:
		""" Returns the menu item for the given menu item type ID, e.g. 'BaseMenuItem' """
		if menuItemTypeId := UID.FetchDataPath(menuItemTypeId):
			return self.menuItems.get(menuItemTypeId, None)
		return None

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
		if not UID.IsPluginIDValid(self.pluginID):
			raise Exception(f'Invalid or missing PLUGIN_ID for: {self.module.__name__}')
		
		self.pluginVersion = getattr(self.module, 'PLUGIN_VERSION', '')
		if not QAVMPlugin.IsVersionValid(self.pluginVersion):
			raise Exception(f'Invalid or missing PLUGIN_VERSION for: {self.module.__name__}')
		
		# These are optional
		self.pluginVariant = getattr(self.module, 'PLUGIN_VARIANT', '')
		self.pluginName = getattr(self.module, 'PLUGIN_NAME', self.pluginPackageName)
		self.pluginDeveloper = getattr(self.module, 'PLUGIN_DEVELOPER', 'Unknown')
		self.pluginWebsite = getattr(self.module, 'PLUGIN_WEBSITE', '')

		self.pluginWorkspaces: list[QAVMWorkspace] = []

		self._loadPluginSoftware()
	
	def _loadPluginSoftware(self) -> None:
		pluginSoftwareRegisterFunc = getattr(self.module, 'RegisterPluginSoftware', None)
		if pluginSoftwareRegisterFunc is None or not callable(pluginSoftwareRegisterFunc):
			return

		softwareRegDataList = pluginSoftwareRegisterFunc()
		if not isinstance(softwareRegDataList, list):
			raise Exception(f'Invalid software registration data for plugin: {self.pluginID}. Expected a list, got {type(softwareRegDataList).__name__}')

		for softwareRegData in softwareRegDataList:
			softwareHandler = SoftwareHandler(softwareRegData)

			if softwareHandler.id in self.softwareHandlers:
				raise Exception(f'Duplicate software ID found: {self.id}')
			
			self.softwareHandlers[softwareHandler.id] = softwareHandler

	def LoadPluginWorkspaces(self) -> None:
		pluginWorkspacesRegisterFunc = getattr(self.module, 'RegisterPluginWorkspaces', None)
		if pluginWorkspacesRegisterFunc is None or not callable(pluginWorkspacesRegisterFunc):
			return
		
		workspaceRegDataList = pluginWorkspacesRegisterFunc()
		if not isinstance(workspaceRegDataList, dict):  # TODO: use _checkType instead
			raise Exception(f'Invalid workspace registration data for plugin: {self.pluginID}. Expected a dictionary, got {type(workspaceRegDataList).__name__}')

		for wsName, wsData in workspaceRegDataList.items():
			if not isinstance(wsData, list):  # TODO: use _checkType instead
				raise Exception(f'Invalid workspace data for plugin: {self.pluginID}. Expected a list, got {type(wsData).__name__}')
			if not isinstance(wsName, str) or not wsName:  # TODO: use _checkType instead
				raise Exception(f'Invalid workspace name for plugin: {self.pluginID}. Expected a non-empty string, got {type(wsName).__name__}')
			if not wsData:  # empty workspace data
				continue

			validUIDs = []
			for uid in wsData:
				if wildCardExpanded := self._expandWildcardUID(uid):
					validUIDs.extend(wildCardExpanded)
					continue

				if UID.IsSoftwareIDDataPathValid(uid):
					validUIDs.append(f'{self.pluginID}#{uid}')
				elif UID.IsUIDValid(uid):
					validUIDs.append(uid)

			self.pluginWorkspaces.append(QAVMWorkspace(validUIDs, wsName))

	def _expandWildcardUID(self, uid: str) -> list[str]:
		""" Expands a wildcard UID to a list of valid UIDs. """
		if not UID.IsDataPathWildcard(uid):
			return []
		
		fullWildcardUid: str = uid
		plID: str = UID.FetchPluginID(uid)
		if not plID:
			plID = self.pluginID  # use current plugin ID if not specified
			fullWildcardUid = f'{plID}#{uid}'
		
		pluginManager: PluginManager = QApplication.instance().GetPluginManager()
		plugin: QAVMPlugin = pluginManager.GetPlugin(plID)
		if not plugin:
			logger.warning(f'Plugin not found for workspace item UID: {uid} (plugin ID: {plID})')
			return []

		validUIDs: list[str] = []
		for swHandler in plugin.GetSoftwareHandlers().values():
			allSWHandlerUIDs = [
				swHandler.GetTileBuilderClasses().keys(),
				swHandler.GetTableBuilderClasses().keys(),
				swHandler.GetCustomViewClasses().keys(),
				swHandler.GetMenuItems().keys()
			]
			for uidsList in allSWHandlerUIDs:
				for itemID in uidsList:
					fullItemID = f'{plID}#{swHandler.GetID()}#{itemID}'
					if UID.MatchDataPath(fullWildcardUid, fullItemID):
						validUIDs.append(fullItemID)

		return validUIDs
	
	def GetSoftwareHandlers(self) -> dict[str, SoftwareHandler]:
		""" Returns a dictionary of software handlers registered by the plugin, e.g. {'software_id': SoftwareHandler} """
		return self.softwareHandlers
	
	def GetSoftwareHandler(self, softwareID: str) -> SoftwareHandler | None:
		""" Returns the software handler for the given software ID, e.g. 'software.example1' """
		softwareID = UID.FetchSoftwareID(softwareID)
		return self.softwareHandlers.get(softwareID, None)
	
	def GetWorkspaces(self) -> list[QAVMWorkspace]:
		""" Returns a list of workspaces registered by the plugin, e.g. [QAVMWorkspace, ...] """
		return self.pluginWorkspaces
	
	def GetDefaultWorkspace(self) -> QAVMWorkspace:
		""" Returns the default workspace registered by the plugin, e.g. QAVMWorkspace() or None if not set """
		if self.pluginWorkspaces:
			return self.pluginWorkspaces[0]
		return QAVMWorkspace()  # return an empty workspace if no workspaces are registered

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
	def IsVersionValid(version: str) -> bool:
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

		self.LoadPluginWorkspaces()

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
	
	def LoadPluginWorkspaces(self) -> None:
		# This is done after all plugins are loaded to be able to access all plugins data (e.g. for the wildcard dereferencing)
		for plugin in self.plugins.values():
			plugin.LoadPluginWorkspaces()
	
	def GetPlugins(self) -> list[QAVMPlugin]:
		return list(self.plugins.values())  # TODO: rewrite with yield
	
	def GetPlugin(self, pluginID: str) -> QAVMPlugin:
		pluginID = UID.FetchPluginID(pluginID)  # in case UID is passed
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
	
	# def GetCurrentSoftwareHandler(self) -> SoftwareHandler:
	# 	app = QApplication.instance()
	# 	qavmSettings = app.GetSettingsManager().GetQAVMSettings()
	# 	return self.GetSoftwareHandler(qavmSettings.GetSelectedSoftwareUID())