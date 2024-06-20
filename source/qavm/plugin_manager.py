import importlib.util, os, re

import logs
logger = logs.logger

class Plugin:
    def __init__(self, pluginFolderPath: str) -> None:
        self.pluginFolderPath = pluginFolderPath
        self.module = None
        
        self.ID = ''
        self.VersionMajor = 0
        self.VersionMinor = 0
        self.VersionPatch = 0

        if not os.path.exists(self.pluginFolderPath):
            logger.error(f'Plugin folder not found: {self.pluginFolderPath}')
            return
        
        self.pluginName = os.path.basename(self.pluginFolderPath)
        self.pluginMainFile = os.path.join(self.pluginFolderPath, f'{self.pluginName}.py')

        if not os.path.exists(self.pluginMainFile):
            logger.error(f'Plugin main file not found: {self.pluginMainFile}')
            return

        try:
            spec = importlib.util.spec_from_file_location(self.pluginName, self.pluginMainFile)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)

            Plugin.CheckSoftwareRegistration(plugin)
            pluginID = getattr(plugin, 'PLUGIN_ID', '')
            if not Plugin.ValidatePluginId(pluginID):
                raise Exception(f'PLUGIN_ID not found for: {self.pluginMainFile}')
            self.ID = pluginID
            
            pluginVersion = getattr(plugin, 'PLUGIN_VERSION', '')
            if not Plugin.ValidatePluginVersion(pluginVersion):
                raise Exception(f'PLUGIN_VERSION not found for: {self.pluginMainFile}')
            self.VersionMajor, self.VersionMinor, self.VersionPatch = [int(v) for v in pluginVersion.split('.')]
            
            logger.info(f'Loaded plugin: {self.pluginName} @ {pluginVersion} ({pluginID})')
            self.module = plugin
        except:
            logger.exception(f'Failed to load plugin: {self.pluginMainFile}')
    
    def IsValid(self) -> bool:
        return self.module is not None and self.ID

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

class PluginPackage:
    pass

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
        
        for dir in os.scandir(self.pluginsFolderPath):
            if not dir.is_dir():
                continue
            pluginFolder = os.path.join(self.pluginsFolderPath, dir)

            pluginPackage = PluginManager.LoadPluginPackage(pluginFolder)
            
            if not pluginPackage.IsValid():
                continue

            if plugin.ID in self.plugins:
                logger.error(f'Duplicate plugin ID found: {plugin.ID}')
                continue
            
            self.plugins[plugin.ID] = plugin
            
    @staticmethod
    def LoadPluginPackage(pluginFolderPath: str) -> Plugin:
        if not os.path.exists(pluginFolderPath):
            logger.error(f'Plugin folder not found: {pluginFolderPath}')
            return
        
        pluginPackageName = os.path.basename(pluginFolderPath)
        pluginMainFile = os.path.join(pluginFolderPath, f'{pluginPackageName}.py')

        if not os.path.exists(pluginMainFile):
            logger.error(f'Plugin main file not found: {pluginMainFile}')
            return

        try:
            spec = importlib.util.spec_from_file_location(pluginPackageName, pluginMainFile)
            pluginPackageModule = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pluginPackageModule)
            
            pluginPackage = PluginPackage(pluginPackageModule)

            pluginSoftware = PluginManager.LoadPluginSoftware(pluginPackageModule)
            
            logger.info(f'Loaded plugin package: {pluginPackageName} @ {pluginVersion} ({pluginID})')
            self.module = plugin
        except:
            logger.exception(f'Failed to load plugin: {pluginMainFile}')
    
    @staticmethod
    def LoadPluginSoftware(pluginPackage: object):
        pluginSoftwareRegisterFunc = getattr(pluginPackage, 'RegisterPluginSoftware', None)
        if pluginSoftwareRegisterFunc is None:
            return
        
        softwareRegDataList = pluginSoftwareRegisterFunc()

        for softwareRegData in softwareRegDataList:
            if not PluginManager.ValidateSoftwareRegData(softwareRegData):
                raise Exception(f'Invalid software registration data for: {pluginPackage.__name__}')
    
    @staticmethod
    def ValidateRegData(regData: dict) -> bool:
        
        pluginID = getattr(regData, 'id', '')
        if not Plugin.ValidatePluginId(pluginID):
            raise Exception(f'PLUGIN_ID not found for: {self.pluginMainFile}')
        self.ID = pluginID
        
        pluginVersion = getattr(plugin, 'PLUGIN_VERSION', '')
        if not Plugin.ValidatePluginVersion(pluginVersion):
            raise Exception(f'PLUGIN_VERSION not found for: {self.pluginMainFile}')
        self.VersionMajor, self.VersionMinor, self.VersionPatch = [int(v) for v in pluginVersion.split('.')]

        raise Exception(f'Invalid software registration data')
        return True
    
    @staticmethod
    def ValidateSoftwareRegData(regData: dict) -> bool:
        PluginManager.ValidateRegData(regData)
        
        return True