import importlib.util, os, re

from qavmapi import BaseQualifier, BaseDescriptor, BaseTileBuilder

import logs
logger = logs.logger

class Module:
    def __init__(self, plugin, regData):
        softwareId = regData.get('id', None)
        self.id = f'{plugin.pluginID}.{softwareId}'

class SoftwareHandler(Module):
    def __init__(self, plugin, regData) -> None:
        super().__init__(plugin, regData)
        
        if not Plugin.ValidateUID(self.id):
            raise Exception(f'Invalid or missing Software ID: {self.id}')
        
        self.name = regData.get('name', self.id)
        
        self.qualifier = regData.get('qualifier', None)
        if not self.qualifier or not issubclass(self.qualifier, BaseQualifier):
            raise Exception(f'Missing or invalid qualifier for software: {self.id}')
        self.descriptor = regData.get('descriptor', None)
        if not self.descriptor or not issubclass(self.descriptor, BaseDescriptor):
            raise Exception(f'Missing or invalid descriptor for software: {self.id}')
        self.tileBuilder = regData.get('tile_builder', None)
        if not self.tileBuilder or not issubclass(self.tileBuilder, BaseTileBuilder):
            raise Exception(f'Missing or invalid tile builder for software: {self.id}')

class Plugin:
    def __init__(self, pluginModule: object) -> None:
        self.module = pluginModule

        self.pluginID = ''
        self.pluginVersion = ''
        self.pluginName = self.module.__name__
        
        self.valid = False

        self.softwareHandlers = dict()

        # First check if plugin contains PLUGIN_ID and PLUGIN_VERSION
        self.pluginID = getattr(self.module, 'PLUGIN_ID', '')
        if not Plugin.ValidateUID(self.pluginID):
            raise Exception(f'Invalid or missing PLUGIN_ID for: {self.module.__name__}')
        
        self.pluginVersion = getattr(self.module, 'PLUGIN_VERSION', '')
        if not Plugin.ValidateVersion(self.pluginVersion):
            raise Exception(f'Invalid or missing PLUGIN_VERSION for: {self.module.__name__}')

        self.LoadModuleSoftware()

        self.valid = True
    
    def IsValid(self) -> bool:
        return self.valid
    
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
            
    
    
    @staticmethod
    def ValidateUID(UID: str) -> bool:
        # checks id to be in domain-style format
        pattern = re.compile("(?:[a-z0-9](?:[a-z0-9]{0,61}[a-z0-9])?\\.)+[a-z0-9][a-z0-9]{0,61}[a-z0-9]")
        return pattern.match(UID) is not None
    
    @staticmethod
    def ValidateVersion(version: str) -> bool:
        # version should be in XXX.XXX.XXXX format, where each part can be at least 1 digit long
        pattern = re.compile("(?:[0-9]{1,3}\.){2}[0-9]{1,4}")
        return pattern.match(version) is not None


class PluginManager:
    def __init__(self, pluginsFolderPath: str) -> None:
        self.pluginsFolderPath = pluginsFolderPath
        self.plugins = dict()

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

                if not plugin.IsValid():
                    raise Exception(f'Could not load plugin: {pluginMainFile}')
                logger.info(f'Loaded plugin: {pluginName}')

                self.plugins[plugin.pluginID] = plugin
            
            except:
                logger.exception(f'Failed to load plugin: {pluginMainFile}')
    
    def GetSoftwareHandlers(self) -> dict[Plugin, dict[str, SoftwareHandler]]:
        softwareHandlers = dict()
        for plugin in self.plugins.values():
            softwareHandlers[plugin] = plugin.softwareHandlers
        return softwareHandlers