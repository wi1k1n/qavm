from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QWidget, QVBoxLayout, QLabel, QListWidgetItem, QListWidget, QHBoxLayout, QStackedWidget,
	QPushButton, QMessageBox, 
)

from qavm.manager_plugin import PluginManager
from qavm.manager_settings import SettingsManager

from qavm.qavmapi import BaseSettings, SoftwareBaseSettings
from qavm.qavmapi.utils import GetQAVMDataPath, OpenFolderInExplorer
import qavm.qavmapi.utils as qutils

import qavm.logs as logs
logger = logs.logger

class PreferencesWindow(QWidget):
	def __init__(self, app, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self.app = app

		self.setWindowTitle("QAVM - Settings")
		self.resize(800, 600)
		self.setMinimumHeight(300)

		# self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)  # this keeps the window on top even for other applications
		self.setWindowFlag(Qt.WindowType.Tool)  # the tool window stays on top of the main window but doesn't affect other applications

		self.settingsManager: SettingsManager = self.app.GetSettingsManager()

		self.contentWidget: QStackedWidget = QStackedWidget(self)

		self.menuWidget = QListWidget()
		self.menuWidget.itemSelectionChanged.connect(self._onMenuSelectionChanged)

		for (name, widget) in self.settingsManager.GetQAVMSettings().CreateWidgets(self.contentWidget):
			self.AddSettingsEntry(name, widget)
		
		swSettings: SoftwareBaseSettings = self.settingsManager.GetSoftwareSettings()
		for (name, widget) in swSettings.CreateWidgets(self.contentWidget):
			self.AddSettingsEntry(name, widget)
		
		# for mSettings in self.settingsManager.GetModuleSettings().values():
		# 	self.AddSettingsEntry(mSettings.GetName(), mSettings)

		minExtraWidth = 20
		if qutils.PlatformMacOS():
			minExtraWidth = 40
		self.menuWidget.setMinimumWidth(self.menuWidget.minimumSizeHint().width() + minExtraWidth)
		self.menuWidget.setMaximumWidth(300 if qutils.PlatformMacOS() else 200)
		
		mainContentLayout = QHBoxLayout()
		mainContentLayout.addWidget(self.menuWidget, 1)
		mainContentLayout.addWidget(self.contentWidget, 3)


		self.settingsBarLayout: QHBoxLayout = QHBoxLayout()
		qavmDataPath = GetQAVMDataPath()
		self.openQAVMSettingsButton = QPushButton("Open QAVM Data Folder")
		self.openQAVMSettingsButton.setToolTip("Open the folder where QAVM stores its data")
		self.openQAVMSettingsButton.clicked.connect(lambda: OpenFolderInExplorer(qavmDataPath))
		self.openQAVMSettingsButton.setFixedWidth(200)

		self.qavmSettingsPathLabel = QLabel(str(qavmDataPath.resolve().absolute()))
		self.qavmSettingsPathLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
		self.settingsBarLayout.addWidget(self.openQAVMSettingsButton)
		self.settingsBarLayout.addWidget(self.qavmSettingsPathLabel)

		mainLayout = QVBoxLayout()
		mainLayout.addLayout(mainContentLayout)
		mainLayout.addLayout(self.settingsBarLayout)

		self.setLayout(mainLayout)
	
	def AddSettingsEntry(self, title: str, widget: QWidget):
		def createMenuItem(text: str) -> QListWidgetItem:
			item: QListWidgetItem = QListWidgetItem(text)
			item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			# item.setData(Qt.ItemDataRole.UserRole, settings)
			return item
		
		self.menuWidget.addItem(createMenuItem(title))
		self.contentWidget.addWidget(widget)
	
	def _onMenuSelectionChanged(self):
		# selectedItem: QListWidgetItem = self.menuWidget.currentItem()
		# logger.info(f'Selected menu item: {selectedItem.text()}')
		self.contentWidget.setCurrentIndex(self.menuWidget.currentRow())

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Escape:
			self.close()
			return
		super().keyPressEvent(event)

	def closeEvent(self, event):
		# TODO: check if dirty settings and ask for confirmation
		reply = QMessageBox.question(self, "Save Preferences", "Do you want to save your preferences to disk?",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)

		if reply == QMessageBox.StandardButton.Yes:
			self.settingsManager.SaveQAVMSettings()
			self.settingsManager.SaveSoftwareSettings()
			event.accept()
		elif reply == QMessageBox.StandardButton.No:
			event.accept()
		else:  # Cancel
			event.ignore()