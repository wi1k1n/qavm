from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QWidget, QVBoxLayout, QLabel, QListWidgetItem, QListWidget, QHBoxLayout, QStackedWidget,
	QPushButton, QMessageBox, QTreeView, 
)
from PyQt6.QtGui import (
	QStandardItemModel, QStandardItem,
)

from qavm.manager_plugin import PluginManager, QAVMWorkspace
from qavm.manager_settings import SettingsManager

from qavm.qavmapi import BaseSettings, SoftwareBaseSettings
from qavm.qavmapi.utils import GetQAVMDataPath, OpenFolderInExplorer
import qavm.qavmapi.utils as qutils

from PyQt6.QtWidgets import QApplication

import qavm.logs as logs
logger = logs.logger

class PreferencesWindow(QWidget):
	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)

		self.setWindowTitle("QAVM - Settings")
		self.resize(800, 600)
		self.setMinimumHeight(300)

		# self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)  # this keeps the window on top even for other applications
		self.setWindowFlag(Qt.WindowType.Tool)  # the tool window stays on top of the main window but doesn't affect other applications

		app = QApplication.instance()
		self.settingsManager: SettingsManager = app.GetSettingsManager()
		self.pluginManager: PluginManager = app.GetPluginManager()

		self.contentWidget: QStackedWidget = QStackedWidget(self)

		self.menuWidget = QTreeView()
		self.menuModel = QStandardItemModel()
		self.menuModel.setHorizontalHeaderLabels(["Settings"])
		self.menuWidget.setModel(self.menuModel)
		self.menuWidget.selectionModel().selectionChanged.connect(self._onMenuSelectionChanged)

		# Add general QAVM settings
		generalSettingsItem = QStandardItem("QAVM")
		generalSettingsItem.setEditable(False)
		generalSettingsItem.setFlags(Qt.ItemFlag.ItemIsEnabled)
		self.menuModel.appendRow(generalSettingsItem)

		for (name, widget) in self.settingsManager.GetQAVMSettings().CreateWidgets(self.contentWidget):
			self.AddSettingsEntry(name, widget, generalSettingsItem)

		# Group settings by software handler
		workspace: QAVMWorkspace = app.GetWorkspace()
		swHandlersSet, _ = workspace.GetInvolvedSoftwareHandlers()
		for swHandler in swHandlersSet:
			if swSettings := self.settingsManager.GetSoftwareSettings(swHandler):
				softwareItem = QStandardItem(swHandler.GetName())
				softwareItem.setEditable(False)
				softwareItem.setFlags(Qt.ItemFlag.ItemIsEnabled)
				self.menuModel.appendRow(softwareItem)

				for (name, widget) in swSettings.CreateWidgets(self.contentWidget):
					self.AddSettingsEntry(name, widget, softwareItem)

		self.menuWidget.expandAll()
	
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

	def AddSettingsEntry(self, title: str, widget: QWidget, parentItem: QStandardItem):
		item = QStandardItem(title)
		item.setEditable(False)
		item.setData(widget, Qt.ItemDataRole.UserRole)  # Associate the widget with the item
		parentItem.appendRow(item)
		self.contentWidget.addWidget(widget)

	def _onMenuSelectionChanged(self, selected, deselected):
		if selectedIndexes := selected.indexes():
			if item := self.menuModel.itemFromIndex(selectedIndexes[0]):
				# Find the corresponding widget in the QStackedWidget
				widgetIndex = self.contentWidget.indexOf(item.data(Qt.ItemDataRole.UserRole))
				if widgetIndex != -1:
					self.contentWidget.setCurrentIndex(widgetIndex)

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_Escape:
			self.close()
			return
		super().keyPressEvent(event)

	def closeEvent(self, event):
		self.settingsManager.SaveQAVMSettings()
		
		swHandlers, _ = QApplication.instance().GetWorkspace().GetInvolvedSoftwareHandlers()
		for swHandler in swHandlers:
			self.settingsManager.SaveSoftwareSettings(swHandler)

		event.accept()