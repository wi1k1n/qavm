import importlib.util, os, re

from qavmapi import BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings

import logs
logger = logs.logger

class Module:
    def __init__(self, plugin, regData):
        self.id = regData.get('id', None)

class SoftwareHandler(Module):
    def __init__(self, plugin, regData) -> None:
        super().__init__(plugin, regData)
        
        if not Plugin.ValidateID(self.id):
            raise Exception(f'Invalid or missing Software ID: {self.id}')
        
        self.name = regData.get('name', self.id)
        
        self.qualifierClass = regData.get('qualifier', None)
        if not self.qualifierClass or not issubclass(self.qualifierClass, BaseQualifier):  # required
            raise Exception(f'Missing or invalid qualifier for software: {self.id}')
        self.descriptorClass = regData.get('descriptor', None)
        if not self.descriptorClass or not issubclass(self.descriptorClass, BaseDescriptor):  # required
            raise Exception(f'Missing or invalid descriptor for software: {self.id}')
        self.tileBuilderClass = regData.get('tile_builder', None)
        if not self.tileBuilderClass or not issubclass(self.tileBuilderClass, BaseTileBuilder):  # required
            raise Exception(f'Missing or invalid tile builder for software: {self.id}')
        
        self.settingsClass = regData.get('settings', None)  # optional
    
    def GetName(self) -> str:
        return self.name
    
    def GetQualifierClass(self) -> BaseQualifier.__class__:
        return self.qualifierClass
    def GetDescriptorClass(self) -> BaseDescriptor.__class__:
        return self.descriptorClass
    def GetTileBuilderClass(self) -> BaseTileBuilder.__class__:
        return self.tileBuilderClass
    def GetSettingsClass(self) -> BaseSettings.__class__:
        return self.settingsClass

class Plugin:
    def __init__(self, pluginModule: object) -> None:
        self.module = pluginModule

        self.pluginID = ''
        self.pluginVersion = ''
        self.pluginName = self.module.__name__

        self.softwareHandlers: dict[str, SoftwareHandler] = dict()  # softwareID: SoftwareHandler

        # First check if plugin contains PLUGIN_ID and PLUGIN_VERSION
        self.pluginID = getattr(self.module, 'PLUGIN_ID', '')
        if not Plugin.ValidateUID(self.pluginID):
            raise Exception(f'Invalid or missing PLUGIN_ID for: {self.module.__name__}')
        
        self.pluginVersion = getattr(self.module, 'PLUGIN_VERSION', '')
        if not Plugin.ValidateVersion(self.pluginVersion):
            raise Exception(f'Invalid or missing PLUGIN_VERSION for: {self.module.__name__}')

        self.LoadModuleSoftware()
    
    def LoadModuleSoftware(self) -> None:
        pluginSoftwareRegisterFunc = getattr(self.module, 'RegisterModuleSoftware', None)
        if pluginSoftwareRegisterFunc is None:
            return
        
        softwareRegDataList = pluginSoftwareRegisterFunc()

        for softwareRegData in softwareRegDataList:
            softwareHandler = SoftwareHandler(self, softwareRegData)

            if softwareHandler.id in self.softwareHandlers:
                raise Exception(f'Duplicate software ID found: {self.id}')
            
            self.softwareHandlers[softwareHandler.id] = softwareHandler

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
        pattern = re.compile("(?:[0-9]{1,3}\.){2}[0-9]{1,4}")
        return pattern.match(version) is not None


class PluginManager:
    def __init__(self, pluginsFolderPath: str) -> None:
        self.pluginsFolderPath = pluginsFolderPath
        self.plugins: dict[str, Plugin] = dict()

        if not os.path.exists(self.pluginsFolderPath):
            os.makedirs(self.pluginsFolderPath)
            logger.info(f'Created plugins folder: {self.pluginsFolderPath}')

    def LoadPlugins(self) -> bool:
        if not os.path.exists(self.pluginsFolderPath):
            logger.error(f'Plugins folder not found: {self.pluginsFolderPath}')
            return False
        
        # Iterate over plugins
        for dir in os.scandir(self.pluginsFolderPath):
            if not dir.is_dir():
                continue
            
            pluginFolderPath = os.path.join(self.pluginsFolderPath, dir)
            if not os.path.exists(pluginFolderPath):
                logger.error(f'Plugin folder not found: {pluginFolderPath}')
                return
            
            pluginName = os.path.basename(pluginFolderPath)
            pluginMainFile = os.path.join(pluginFolderPath, f'{pluginName}.py')

            if not os.path.exists(pluginMainFile):
                logger.error(f'Plugin main file not found: {pluginMainFile}')
                return

            try:
                spec = importlib.util.spec_from_file_location(pluginName, pluginMainFile)
                pluginPyModule = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(pluginPyModule)
                
                plugin = Plugin(pluginPyModule)
                logger.info(f'Loaded plugin: {pluginName} @ {plugin.GetVersionStr()} ({plugin.GetUID()})')
                self.plugins[plugin.pluginID] = plugin
            
            except:
                logger.exception(f'Failed to load plugin: {pluginMainFile}')
    
    def GetPlugins(self) -> list[Plugin]:
        return list(self.plugins.values())  # TODO: rewrite with yield
    
    def GetPlugin(self, pluginUID: str) -> Plugin:
        return self.plugins.get(pluginUID, None)
    
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