from typing import List

import qavm.logs as logs
logger = logs.logger

from qavm.manager_plugin import PluginManager, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMSettings
import qavm.qavmapi.utils as utils

from PyQt6.QtGui import (
    QFont
)
from PyQt6.QtWidgets import (
	QApplication
)

from qavm.window_main import MainWindow
from qavm.window_pluginselect import PluginSelectionWindow

# Extensive PyQt tutorial: https://realpython.com/python-menus-toolbars/#building-context-or-pop-up-menus-in-pyqt
class QAVMApp(QApplication):
	def __init__(self, argv: List[str]) -> None:
		super().__init__(argv)
		
		self.setApplicationName('QAVM')
		self.setOrganizationName('wi1k.in.prod')
		self.setOrganizationDomain('wi1k.in')
		
		self.settingsManager = SettingsManager(self, utils.GetPrefsFolderPath())
		self.settingsManager.LoadQAVMSettings()
		self.qavmSettings: QAVMSettings = self.settingsManager.GetQAVMSettings()

		self.pluginManager = PluginManager(self, utils.GetPluginsFolderPath())
		self.pluginManager.LoadPlugins()

		
		selectedSoftwareUID = self.qavmSettings.GetSelectedSoftwareUID()
		swHandlers: dict[str, SoftwareHandler] = {f'{pUID}#{sID}': swHandler for pUID, sID, swHandler in self.pluginManager.GetSoftwareHandlers()}  # {softwareUID: SoftwareHandler}

		if selectedSoftwareUID and selectedSoftwareUID not in swHandlers:
			logger.warning(f'Selected software plugin not found: {selectedSoftwareUID}')

		if selectedSoftwareUID in swHandlers:
			logger.info(f'Selected software plugin: {selectedSoftwareUID}')
			self.qavmSettings.SetSelectedSoftwareUID(selectedSoftwareUID)
			self.startMainWindow()
		elif len(swHandlers) == 1:
			logger.info(f'The only software plugin: {list(swHandlers.keys())[0]}')
			self.qavmSettings.SetSelectedSoftwareUID(list(swHandlers.keys())[0])
			self.startMainWindow()
		else:
			self.selectPluginWindow: PluginSelectionWindow = PluginSelectionWindow(self)
			self.selectPluginWindow.pluginSelected.connect(self.slot_PluginSelected)
			self.selectPluginWindow.show()
	
	def slot_PluginSelected(self, pluginUID: str, softwareID: str):
		logger.info(f'Selected software UID: {pluginUID}#{softwareID}')
		self.qavmSettings.SetSelectedSoftwareUID(f'{pluginUID}#{softwareID}')
		self.startMainWindow()
	
	""" Performs software-specific initialization and opens main window """
	def startMainWindow(self):
		self.settingsManager.LoadModuleSettings()
		
		self.mainWindow: MainWindow = MainWindow(self)
		self.mainWindow.show()

	def GetPluginManager(self) -> PluginManager:
		return self.pluginManager
	
	def GetSettingsManager(self) -> SettingsManager:
		return self.settingsManager