from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QWidget, QVBoxLayout, QLabel, QListWidgetItem, QListWidget, QHBoxLayout, QStackedWidget
)

from qavm.manager_plugin import PluginManager
from qavm.manager_settings import SettingsManager

from qavm.qavmapi import BaseSettings, SoftwareBaseSettings

import qavm.logs as logs
logger = logs.logger

class PreferencesWindowExample(QWidget):
	def __init__(self, app, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.app = app

		self.setWindowTitle("QAVM - Settings")
		self.resize(600, 600)
		self.setMinimumHeight(300)
		self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

		self.settingsManager: SettingsManager = self.app.GetSettingsManager()

		self.contentWidget: QStackedWidget = QStackedWidget(self)

		self.menuWidget = QListWidget()
		self.menuWidget.itemSelectionChanged.connect(self._onMenuSelectionChanged)
		self.AddSettingsEntry("Application", self.settingsManager.GetQAVMSettings())
		
		swSettings: SoftwareBaseSettings = self.settingsManager.GetSoftwareSettings()
		if type(swSettings) is not SoftwareBaseSettings:
			self.AddSettingsEntry(swSettings.GetName(), swSettings)
		
		# for mSettings in self.settingsManager.GetModuleSettings().values():
		# 	self.AddSettingsEntry(mSettings.GetName(), mSettings)

		self.menuWidget.setMinimumWidth(self.menuWidget.minimumSizeHint().width() + 20)
		self.menuWidget.setMaximumWidth(200)

		mainLayout = QHBoxLayout()
		mainLayout.addWidget(self.menuWidget, 1)
		mainLayout.addWidget(self.contentWidget, 3)
		self.setLayout(mainLayout)
	
	def AddSettingsEntry(self, title: str, settings: BaseSettings):
		def createMenuItem(text: str) -> QListWidgetItem:
			item: QListWidgetItem = QListWidgetItem(text)
			item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			item.setData(Qt.ItemDataRole.UserRole, settings)
			return item
		if w := settings.CreateWidget(self):
			self.menuWidget.addItem(createMenuItem(title))
			self.contentWidget.addWidget(w)
	
	def _onMenuSelectionChanged(self):
		# selectedItem: QListWidgetItem = self.menuWidget.currentItem()
		# logger.info(f'Selected menu item: {selectedItem.text()}')
		self.contentWidget.setCurrentIndex(self.menuWidget.currentRow())

	def closeEvent(self, event):
		logger.info('Saving settings on close')
		self.settingsManager.SaveQAVMSettings()
		self.settingsManager.SaveSoftwareSettings()