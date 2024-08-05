from functools import partial

import qavm.logs as logs
logger = logs.logger

from qavm.manager_plugin import PluginManager, QAVMPlugin, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMSettings

from PyQt6.QtCore import (
	pyqtSignal
)
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QPushButton, QSizePolicy
)

class PluginSelectionWindow(QMainWindow):
	# pluginSelected = pyqtSignal(str, str)  # (pluginID, softwareID)

	def __init__(self, app, parent: QWidget | None = None) -> None:
		super(PluginSelectionWindow, self).__init__(parent)

		self.app = app

		self.setWindowTitle("Select Software handler")
		self.resize(480, 240)

		layout: QVBoxLayout = QVBoxLayout()

		self.dialogsManager = self.app.GetDialogsManager()

		self.pluginManager: PluginManager = app.GetPluginManager()
		self.settingsManager: SettingsManager = self.app.GetSettingsManager()
		self.qavmSettings: QAVMSettings = self.settingsManager.GetQAVMSettings()

		swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()  # [pluginID, softwareID, SoftwareHandler]

		for pluginID, softwareID, softwareHandler in swHandlers:
			plugin: QAVMPlugin = self.pluginManager.GetPlugin(pluginID)
			button = QPushButton(f'[{plugin.GetName()} @ {plugin.GetVersionStr()} ({pluginID})] {softwareHandler.GetName()} ({softwareID})')
			button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
			button.clicked.connect(partial(self.selectPlugin, plugin.pluginID, softwareID))
			layout.addWidget(button)

		widget: QWidget = QWidget()
		widget.setLayout(layout)

		self.setCentralWidget(widget)

		self.update()

	def show(self):
		selectedSoftwareUID = self.qavmSettings.GetSelectedSoftwareUID()
		swHandlers: dict[str, SoftwareHandler] = {f'{pUID}#{sID}': swHandler for pUID, sID, swHandler in self.pluginManager.GetSoftwareHandlers()}  # {softwareUID: SoftwareHandler}

		if selectedSoftwareUID and selectedSoftwareUID not in swHandlers:
			logger.warning(f'Selected software plugin not found: {selectedSoftwareUID}')
			return super(PluginSelectionWindow, self).show()
			
		if selectedSoftwareUID in swHandlers:
			logger.info(f'Selected software plugin: {selectedSoftwareUID}')
			return self.startMainWindow()
		
		if len(swHandlers) == 1:
			logger.info(f'The only software plugin: {list(swHandlers.keys())[0]}')
			self.qavmSettings.SetSelectedSoftwareUID(list(swHandlers.keys())[0])
			return self.startMainWindow()

		super(PluginSelectionWindow, self).show()
	
	def selectPlugin(self, pluginUID: str, softwareID: str):
		# self.pluginSelected.emit(pluginUID, softwareID)
		self.qavmSettings.SetSelectedSoftwareUID(f'{pluginUID}#{softwareID}')
		
		# this is needed since we don't distinguish between initial load and running "select plugin" action
		self.qavmSettings.Save()  # TODO: doesn't sound super correct

		self.startMainWindow()
		self.close()

	def startMainWindow(self):
		self.settingsManager.LoadSoftwareSettings()
		
		self.app.ResetSoftwareDescriptions()
		self.dialogsManager.ResetPreferencesWindow()
		self.dialogsManager.ResetMainWindow()

		self.dialogsManager.GetMainWindow().show()