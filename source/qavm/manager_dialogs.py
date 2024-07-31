from qavm.window_pluginselect import PluginSelectionWindow
from qavm.window_main import MainWindow
from qavm.window_settings import PreferencesWindowExample

import qavm.logs as logs
logger = logs.logger

class DialogsManager:
	def __init__(self, app) -> None:
		self.app = app

		self.selectPluginWindow: PluginSelectionWindow = PluginSelectionWindow(app)
		self.mainWindow: MainWindow = MainWindow(app)
		self.windowPrefs = PreferencesWindowExample(app)

	def GetPluginSelectionWindow(self):
		return self.selectPluginWindow
	
	def GetMainWindow(self):
		return self.mainWindow
	
	def GetPreferencesWindow(self):
		return self.windowPrefs