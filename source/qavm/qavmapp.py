import argparse
from typing import List
from pathlib import Path

import qavm.logs as logs
logger = logs.logger

from qavm.manager_plugin import PluginManager, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMSettings
from qavm.manager_dialogs import DialogsManager
import qavm.qavmapi.utils as utils
import qavm.qavmapi_utils as qavmapi_utils
from qavm.qavmapi import BaseDescriptor

from PyQt6.QtGui import (
    QFont, QIcon
)
from PyQt6.QtWidgets import (
	QApplication
)

from qavm.window_main import MainWindow
from qavm.window_pluginselect import PluginSelectionWindow

# Extensive PyQt tutorial: https://realpython.com/python-menus-toolbars/#building-context-or-pop-up-menus-in-pyqt
class QAVMApp(QApplication):
	def __init__(self, argv: List[str], args: argparse.Namespace) -> None:
		super().__init__(argv)
		
		self.setApplicationName('QAVM')
		self.setOrganizationName('wi1k.in.prod')
		self.setOrganizationDomain('wi1k.in')
		
		self.iconApp: QIcon = QIcon(str(Path('res/qavm_icon.png').resolve()))
		self.setWindowIcon(self.iconApp)

		self.pluginPaths: set[Path] = {utils.GetDefaultPluginsFolderPath()}
		self.softwareDescriptions: list[BaseDescriptor] = None

		self.processArgs(args)
		
		self.dialogsManager: DialogsManager = DialogsManager(self)

		self.settingsManager = SettingsManager(self, utils.GetPrefsFolderPath())
		self.settingsManager.LoadQAVMSettings()
		self.qavmSettings: QAVMSettings = self.settingsManager.GetQAVMSettings()

		self.pluginManager = PluginManager(self, self.GetPluginPaths())
		self.pluginManager.LoadPlugins()

		self.settingsManager.LoadModuleSettings()

		self.dialogsManager.GetPluginSelectionWindow().show()

	def GetPluginManager(self) -> PluginManager:
		return self.pluginManager
	
	def GetSettingsManager(self) -> SettingsManager:
		return self.settingsManager
	
	def GetDialogsManager(self) -> DialogsManager:
		return self.dialogsManager
	
	def GetPluginPaths(self) -> list[Path]:
		return list(self.pluginPaths)
	
	def GetSoftwareDescriptions(self) -> list[BaseDescriptor]:
		if self.softwareDescriptions is None:
			self.softwareDescriptions = self.ScanSoftware()
		return self.softwareDescriptions
	
	def ResetSoftwareDescriptions(self) -> None:
		self.softwareDescriptions = None
	
	def ScanSoftware(self) -> list[BaseDescriptor]:
		qavmSettings = self.settingsManager.GetQAVMSettings()

		softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()
		if softwareHandler is None:
			raise Exception('No software handler found')

		qualifier = softwareHandler.GetQualifier()
		descriptorClass = softwareHandler.GetDescriptorClass()
		softwareSettings = softwareHandler.GetSettings()

		searchPaths = qavmSettings.GetSearchPaths()
		searchPaths = qualifier.ProcessSearchPaths(searchPaths)

		config = qualifier.GetIdentificationConfig()
		if not qavmapi_utils.ValidateQualifierConfig(config):
			raise Exception('Invalid Qualifier config')
		
		def getDirListIgnoreError(pathDir: str) -> list[Path]:
			try:
				return [d for d in Path(pathDir).iterdir() if d.is_dir()]
				# dirList: list[Path] = [Path(pathDir)/d for d in os.listdir(pathDir)]
				# return list(filter(lambda d: os.path.isdir(d), dirList))
			except:
				# logger.warning(f'Failed to get dir list: {pathDir}')
				pass
			return list()
		
		def TryPassFileMask(dirPath: Path, config: dict[str, list[str]]) -> bool:
			for file in config['requiredFileList']:
				if not (dirPath / file).is_file():
					return False
			for folder in config['requiredDirList']:
				if not (dirPath / folder).is_dir():
					return False
			for file in config['negativeFileList']:
				if (dirPath / file).is_file():
					return False
			for folder in config['negativeDirList']:
				if (dirPath / folder).is_dir():
					return False
			return True
		
		def GetFileContents(dirPath: Path, config: dict[str, list[str]]) -> dict[str, str | bytes]:
			fileContents = dict()
			for file, isBinary, lengthLimit in config['fileContentsList']:
				try:
					# TODO: use pathlib instead
					with open(dirPath/file, 'rb' if isBinary else 'r') as f:
						fileContents[file] = f.read(lengthLimit if lengthLimit else -1)
				except Exception as e:
					# logger.warning(f'Failed to read file "{os.path.join(dirPath, file)}": {e}')
					pass
			return fileContents
		
		softwareDescs: list[BaseDescriptor] = list()

		MAX_DEPTH = 1  # TODO: make this a settings value
		currentDepthLevel: int = 0
		searchPathsList = set(searchPaths)
		while currentDepthLevel < MAX_DEPTH:
			subfoldersSearchPathsList = set()
			for searchPath in searchPathsList:
				dirs: set[Path] = set(getDirListIgnoreError(searchPath))
				subdirs: set[str] = set()
				# for dir in dirs:
				for dir in sorted(dirs):
					passed = TryPassFileMask(dir, config)
					if not passed:
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue

					fileContents: dict[str, str | bytes] = GetFileContents(dir, config)
					if not qualifier.Identify(dir, fileContents):
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue
					softwareDescs.append(descriptorClass(dir, softwareSettings, fileContents))
				subfoldersSearchPathsList.update(subdirs)
			searchPathsList = subfoldersSearchPathsList
			currentDepthLevel += 1
		
		return softwareDescs
	
	def processArgs(self, args: argparse.Namespace) -> None:
		# TODO: make these args globally accessible from everywhere
		if args.pluginsFolder:
			self.pluginPaths.add(Path(args.pluginsFolder))

		self.selectedSoftwareUID = args.selectedSoftwareUID