from qavm.window_pluginselect import WorkspaceManagerWindow
from qavm.window_main import MainWindow
from qavm.window_settings import PreferencesWindow
from qavm.manager_plugin import QAVMWorkspace

from PyQt6.QtWidgets import (
	QApplication, QWidget, 
)

import qavm.logs as logs
logger = logs.logger

class DialogsManager:
	def __init__(self) -> None:
		self.selectPluginWindow: WorkspaceManagerWindow = None
		self.mainWindow: MainWindow = None
		self.windowPrefs: PreferencesWindow = None

	def ShowWorkspace(self, workspace: QAVMWorkspace):
		app = QApplication.instance()
		app.GetSettingsManager().LoadWorkspaceSoftwareSettings(workspace)
		app.SetWorkspace(workspace)
		self.GetMainWindow().show()

	def ShowWorkspaceManager(self):
		self.ResetPreferencesWindow()
		self.ResetMainWindow()
		self.GetPluginSelectionWindow().show()

	def ShowPreferences(self):
		prefsWindow: QWidget = self.GetPreferencesWindow()
		prefsWindow.show()
		prefsWindow.activateWindow()

	def GetPluginSelectionWindow(self):
		if self.selectPluginWindow is None:
			self.selectPluginWindow: WorkspaceManagerWindow = WorkspaceManagerWindow()
		return self.selectPluginWindow
	
	def GetMainWindow(self):
		if self.mainWindow is None:
			self.mainWindow: MainWindow = MainWindow()
		return self.mainWindow
	
	def GetPreferencesWindow(self):
		if self.windowPrefs is None:
			self.windowPrefs = PreferencesWindow(self.GetMainWindow())
		return self.windowPrefs
	
	def ResetMainWindow(self):
		self._resetWindow(self.mainWindow)
		self.mainWindow = None

	def ResetPreferencesWindow(self):
		self._resetWindow(self.windowPrefs)
		self.windowPrefs = None

	def _resetWindow(self, window: QWidget):
		if not window:
			return
		window.close()
		window.deleteLater()