import argparse
from typing import List, Type
from pathlib import Path

from qavm.manager_plugin import PluginManager, SoftwareHandler, QAVMWorkspace
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings
from qavm.manager_dialogs import DialogsManager
from qavm.manager_descriptor_data import DescriptorDataManager
from qavm.manager_tags import TagsManager

import qavm.qavmapi.utils as utils  # TODO: rename to qutils
import qavm.qavmapi.gui as gui_utils
from qavm.qavmapi import (
	BaseDescriptor, QualifierIdentificationConfig, BaseQualifier, SoftwareBaseSettings,

)
from qavm.utils_plugin_package import VerifyPlugin

from PyQt6.QtCore import (
	Qt, QEvent, 
)
from PyQt6.QtGui import (
    QIcon, 
)
from PyQt6.QtWidgets import (
	QApplication, QWidget
)

import qavm.logs as logs
logger = logs.logger

# Extensive PyQt tutorial: https://realpython.com/python-menus-toolbars/#building-context-or-pop-up-menus-in-pyqt
class QAVMApp(QApplication):
	def __init__(self, argv: List[str], args: argparse.Namespace) -> None:
		super().__init__(argv)
		
		self.setApplicationName('QAVM')
		self.setOrganizationName('wi1k.in.prod')
		self.setOrganizationDomain('wi1k.in')
		
		self.iconApp: QIcon = QIcon(str(Path('res/qavm_icon.png').resolve()))
		self.setWindowIcon(self.iconApp)
		
		self.installEventFilter(self)

		self.pluginsFolderPaths: set[Path] = {utils.GetDefaultPluginsFolderPath()}
		self.pluginPaths: set[Path] = set()  # Paths to individual plugins
		self.builtinPluginPaths: set[Path] = set()  # Paths to built-in plugins (i.e. unpacked plugins)
		self.softwareDescriptors: dict[SoftwareHandler, dict[str, list[BaseDescriptor]]] = dict()

		self.processArgs(args)

		logger.info(f'Plugins folder paths: {[str(p) for p in self.pluginsFolderPaths]}')
		logger.info(f'Extra individial plugin paths: {[str(p) for p in self.pluginPaths]}')
		
		self.dialogsManager: DialogsManager = DialogsManager()

		self.settingsManager: SettingsManager = SettingsManager(utils.GetPrefsFolderPath())
		self.settingsManager.LoadQAVMSettings()
		self.qavmSettings: QAVMGlobalSettings = self.settingsManager.GetQAVMSettings()

		if not args.ignoreBuiltinPlugins:
			self._verifyBuiltinPlugins(args)

		self.pluginManager: PluginManager = PluginManager(self.builtinPluginPaths.union(self.pluginPaths), self.GetPluginsFolderPaths())
		self.pluginManager.LoadPlugins()  # TODO: try/except here?

		self.descDataManager: DescriptorDataManager = DescriptorDataManager(utils.GetQAVMDescriptorDataFilepath())
		self.descDataManager.LoadData()

		self.tagsManager: TagsManager = TagsManager(utils.GetQAVMTagsDataFilepath(), self.descDataManager)
		self.tagsManager.LoadTags()

		gui_utils.SetTheme(self.settingsManager.GetQAVMSettings().GetAppTheme())  # TODO: move this to the QAVMGlobalSettings class?
		
		self.workspace: QAVMWorkspace = self.qavmSettings.GetWorkspaceLast()

		if self.workspace.IsEmpty():
			self.dialogsManager.GetPluginSelectionWindow().show()
		else:
			self.dialogsManager.ShowWorkspace(self.workspace)

	def GetPluginManager(self) -> PluginManager:
		return self.pluginManager
	
	def GetSettingsManager(self) -> SettingsManager:
		return self.settingsManager
	
	def GetDialogsManager(self) -> DialogsManager:
		return self.dialogsManager
	
	def GetDescriptorDataManager(self) -> DescriptorDataManager:
		return self.descDataManager
	
	def GetTagsManager(self) -> TagsManager:
		return self.tagsManager
	
	def GetWorkspace(self) -> QAVMWorkspace:
		return self.workspace
	
	def SetWorkspace(self, workspace: QAVMWorkspace) -> None:
		self.workspace = workspace
	
	def GetPluginsFolderPaths(self) -> list[Path]:
		""" Returns a list of paths to the plugins folders (i.e. folder, containing plugin folders). """
		return list(self.pluginsFolderPaths)
	
	def GetPluginPaths(self) -> list[Path]:
		""" Returns a set of paths to individual plugins (i.e. a folder, containing the plugin). """
		return list(self.pluginPaths)
	
	def GetSoftwareDescriptors(self, swHandler: SoftwareHandler) -> dict[str, list[BaseDescriptor]]:
		if swDescriptors := self.softwareDescriptors.get(swHandler, dict()):
			return swDescriptors
		
		self.softwareDescriptors[swHandler] = self.ScanSoftware(swHandler)
		return self.softwareDescriptors[swHandler]
	
	def ResetSoftwareDescriptors(self) -> None:
		self.softwareDescriptors = None
	
	def ScanSoftware(self, swHandler: SoftwareHandler) -> dict[str, list[BaseDescriptor]]:
		descs: dict[str, list[BaseDescriptor]] = dict()
		softwareSettings: SoftwareBaseSettings = self.settingsManager.GetSoftwareSettings(swHandler)
		searchPaths: list[Path] = softwareSettings.GetEvaluatedSearchPaths()
		for descDPath, (qualifier, descClass) in swHandler.GetDescriptorClasses().items():
			MAX_SCAN_DEPTH: int = 1
			descs[descDPath] = self._scanSoftwareDescriptor(qualifier, descClass, softwareSettings, searchPaths, scanDepth=MAX_SCAN_DEPTH)
		return descs

	def _scanSoftwareDescriptor(self,
							 qualifier: BaseQualifier,
							 descriptorClass: Type[BaseDescriptor],
							 softwareSettings: SoftwareBaseSettings,
							 searchPaths: list[Path],
							 scanDepth: int = 1
							 ) -> list[BaseDescriptor]:
		searchPaths = qualifier.ProcessSearchPaths(searchPaths)
		
		config: QualifierIdentificationConfig = qualifier.GetIdentificationConfig()
		
		def getDirListIgnoreError(pathDir: Path) -> list[Path]:
			try:
				return [d for d in pathDir.iterdir() if d.is_dir()]
			except:
				# logger.warning(f'Failed to get dir list: {pathDir}')
				pass
			return list()
		
		softwareDescs: list[BaseDescriptor] = list()

		currentDepthLevel: int = 0
		searchPathsList = set(searchPaths)
		while currentDepthLevel < scanDepth:
			subfoldersSearchPathsList = set()
			for searchPath in searchPathsList:
				dirs: set[Path] = set(getDirListIgnoreError(searchPath))
				subdirs: set[str] = set()
				for dir in sorted(dirs):
					passed = config.IdentificationMaskPasses(dir)
					if not passed:
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue

					fileContents: dict[str, str | bytes] = config.GetFileContents(dir)
					if not qualifier.Identify(dir, fileContents):
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue
					descriptor: BaseDescriptor = descriptorClass(dir, softwareSettings, fileContents)
					descData: dict = self.descDataManager.GetDescriptorData(descriptor)
					# descriptor.AttachDescriptorData(descData)
					softwareDescs.append(descriptor)
				subfoldersSearchPathsList.update(subdirs)
			searchPathsList = subfoldersSearchPathsList
			currentDepthLevel += 1
		
		return softwareDescs
	
	def processArgs(self, args: argparse.Namespace) -> None:
		# TODO: make these args globally accessible from everywhere
		logger.info(f'QAVMApp arguments: {vars(args)}')
		
		if args.pluginsFolder:
			self.pluginsFolderPaths = {Path(args.pluginsFolder)}
		if args.extraPluginsFolder:
			self.pluginsFolderPaths.update({Path(p) for p in args.extraPluginsFolder})
		
		if args.extraPluginPath:
			self.pluginPaths.update({Path(p) for p in args.extraPluginPath})

		# self.selectedSoftwareUID = args.selectedSoftwareUID

	def _loadVerificationKey(self) -> bytes:
		try:
			from qavm.generated.verification_key import VERIFICATION_KEY
			return VERIFICATION_KEY.encode('utf-8')
		except Exception as e:
			logger.error(f'Failed to load verification key: {e}')
			return b''

	# TODO: refactor this giant function
	def _verifyBuiltinPlugins(self, args: argparse.Namespace) -> None:
		if utils.PlatformWindows():
			builtinPluginsPath: Path = utils.GetQAVMRootPath() / 'builtin_plugins'
		elif utils.PlatformMacOS():
			builtinPluginsPath: Path = utils.GetQAVMRootPath() / '../Resources/builtin_plugins'
		if not builtinPluginsPath.is_dir():
			logger.error(f'Builtin plugins directory does not exist: {builtinPluginsPath}')
			return
		
		# Verify the plugin signature
		publicKey: bytes = self._loadVerificationKey()
		if not publicKey:
			logger.error('Public key for plugin verification is not available')
			return

		for pluginPath in builtinPluginsPath.iterdir():
			if not pluginPath.is_dir():
				continue

			logger.info(f'Verifying plugin signature: {pluginPath}')
			pluginSignaturePath: Path = pluginPath.parent / f'{pluginPath.name}.sig'
			if not pluginSignaturePath.exists():
				logger.error(f'Plugin signature not found: {pluginSignaturePath}')
				continue

			if not VerifyPlugin(pluginPath, pluginSignaturePath, publicKey):
				logger.error(f'Plugin verification failed: {pluginPath}')
				continue

			self.builtinPluginPaths.add(pluginPath.resolve().absolute())


	def eventFilter(self, obj, event):
		if utils.IsDebug():
			from qavm.debug_qtwidget_dump import QtHTMLDump
			if event.type() == QEvent.Type.KeyPress:
				if (event.key() == Qt.Key.Key_Q and event.modifiers() == (Qt.KeyboardModifier.ControlModifier)):
					activeWindow = QApplication.activeWindow()
					if not isinstance(activeWindow, QWidget):
						print("[QtHTMLDump] No active window to dump layout from.")
						return False
					print("[QtHTMLDump] Dumping layout of the active window (", activeWindow.objectName(), ") to HTML.")
					dumper = QtHTMLDump(activeWindow)
					dumper.save_to_file("layout_snapshot.html")
					return True
		return super().eventFilter(obj, event)