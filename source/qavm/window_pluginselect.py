from functools import partial

import logs
logger = logs.logger

from manager_plugin import PluginManager, Plugin, SoftwareHandler
from PyQt6.QtCore import (
	pyqtSignal
)
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QPushButton, QSizePolicy
)

class PluginSelectionWindow(QMainWindow):
	pluginSelected = pyqtSignal(str, str)  # (pluginID, softwareID)

	def __init__(self, app, parent: QWidget | None = None) -> None:
		super(PluginSelectionWindow, self).__init__(parent)

		self.setWindowTitle("Select Software handler")
		self.resize(480, 240)

		layout: QVBoxLayout = QVBoxLayout()

		pluginManager: PluginManager = app.GetPluginManager()
		swHandlers: list[tuple[str, str, SoftwareHandler]] = pluginManager.GetSoftwareHandlers()  # [pluginID, softwareID, SoftwareHandler]

		for pluginUID, softwareID, softwareHandler in swHandlers:
			plugin: Plugin = pluginManager.GetPlugin(pluginUID)
			button = QPushButton(f'[{plugin.GetName()} @ {plugin.GetVersionStr()} ({pluginUID})] {softwareHandler.GetName()} ({softwareID})')
			button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
			button.clicked.connect(partial(self.selectPlugin, plugin.pluginID, softwareID))
			layout.addWidget(button)

		widget: QWidget = QWidget()
		widget.setLayout(layout)

		self.setCentralWidget(widget)

		self.update()
	
	def selectPlugin(self, pluginUID: str, softwareID: str):
		self.pluginSelected.emit(pluginUID, softwareID)
		self.close()