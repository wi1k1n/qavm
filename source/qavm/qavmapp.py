from typing import List

import qavm.logs as logs
logger = logs.logger

from qavm.manager_plugin import PluginManager, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMSettings
from qavm.manager_dialogs import DialogsManager
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
		
		self.dialogsManager: DialogsManager = DialogsManager(self)

		self.settingsManager = SettingsManager(self, utils.GetPrefsFolderPath())
		self.settingsManager.LoadQAVMSettings()
		self.qavmSettings: QAVMSettings = self.settingsManager.GetQAVMSettings()

		self.pluginManager = PluginManager(self, utils.GetPluginsFolderPath())
		self.pluginManager.LoadPlugins()

		self.settingsManager.LoadModuleSettings()

		self.dialogsManager.GetPluginSelectionWindow().show()

	def GetPluginManager(self) -> PluginManager:
		return self.pluginManager
	
	def GetSettingsManager(self) -> SettingsManager:
		return self.settingsManager
	
	def GetDialogsManager(self) -> DialogsManager:
		return self.dialogsManager