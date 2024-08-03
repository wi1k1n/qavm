from qavm.window_pluginselect import PluginSelectionWindow
from qavm.window_main import MainWindow
from qavm.window_settings import PreferencesWindowExample

import qavm.logs as logs
logger = logs.logger

class DialogsManager:
	def __init__(self, app) -> None:
		self.app = app

		self.selectPluginWindow: PluginSelectionWindow = None
		self.mainWindow: MainWindow = None
		self.windowPrefs: PreferencesWindowExample = None

	def GetPluginSelectionWindow(self):
		if self.selectPluginWindow is None:
			self.selectPluginWindow: PluginSelectionWindow = PluginSelectionWindow(self.app)
		return self.selectPluginWindow
	
	def GetMainWindow(self):
		if self.mainWindow is None:
			self.mainWindow: MainWindow = MainWindow(self.app)
		return self.mainWindow
	def ResetMainWindow(self):
		self.mainWindow = None
	
	def GetPreferencesWindow(self):
		if self.windowPrefs is None:
			self.windowPrefs = PreferencesWindowExample(self.app)
		return self.windowPrefs
	def ResetPreferencesWindow(self):
		self.windowPrefs = None