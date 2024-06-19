import importlib.util, os, re

import logs
logger = logs.logger

class Plugin:
    def __init__(self, pluginFolderPath: str) -> None:
        self.pluginFolderPath = pluginFolderPath

        if not os.path.exists(self.pluginFolderPath):
            logger.error(f'Plugin folder not found: {self.pluginFolderPath}')
            return
        
        self.pluginName = os.path.basename(self.pluginFolderPath)
        self.pluginMainFile = os.path.join(self.pluginFolderPath, f'{self.pluginName}.py')

        if not os.path.exists(self.pluginMainFile):
            logger.error(f'Plugin main file not found: {self.pluginMainFile}')
            return

        self.pluginModule = None

        try:
            spec = importlib.util.spec_from_file_location(self.pluginName, self.pluginMainFile)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)

            pluginID = getattr(plugin, 'PLUGIN_ID', '')
            if not Plugin.ValidatePluginId(pluginID):
                raise Exception(f'PLUGIN_ID not found for: {self.pluginMainFile}')
            
            pluginVersion = getattr(plugin, 'PLUGIN_VERSION', '')
            if not Plugin.ValidatePluginVersion(pluginVersion):
                raise Exception(f'PLUGIN_VERSION not found for: {self.pluginMainFile}')
            
            logger.info(f'Loaded plugin: {self.pluginName} @ {pluginVersion} ({pluginID})')
            self.pluginModule = plugin
        except:
            logger.exception(f'Failed to load plugin: {self.pluginMainFile}')
    
    @staticmethod
    def ValidatePluginId(pluginId: str) -> bool:
        # checks plugin id to be in domain-style format
        pattern = re.compile("(?:[a-z0-9](?:[a-z0-9]{0,61}[a-z0-9])?\\.)+[a-z0-9][a-z0-9]{0,61}[a-z0-9]")
        return pattern.match(pluginId) is not None
    
    @staticmethod
    def ValidatePluginVersion(pluginVersion: str) -> bool:
        # plugin version should be in XXX.XXX.XXXX format, where each part can be at least 1 digit long
        pattern = re.compile("(?:[0-9]{1,3}\.){2}[0-9]{1,4}")
        return pattern.match(pluginVersion) is not None

class PluginManager:
    def __init__(self, pluginsFolderPath: str) -> None:
        self.pluginsFolderPath = pluginsFolderPath

        if not os.path.exists(self.pluginsFolderPath):
            os.makedirs(self.pluginsFolderPath)
            logger.info(f'Created plugins folder: {self.pluginsFolderPath}')

    def LoadPlugins(self) -> bool:
        if not os.path.exists(self.pluginsFolderPath):
            logger.error(f'Plugins folder not found: {self.pluginsFolderPath}')
            return False
        
        for dir in os.scandir(self.pluginsFolderPath):
            if not dir.is_dir():
                continue
            pluginFolder = os.path.join(self.pluginsFolderPath, dir)
            plugin = Plugin(pluginFolder)