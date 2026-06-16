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
		self.resize(900, 600)
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
		self.menuWidget.clicked.connect(self._onMenuItemClicked)

		# Add general QAVM settings
		qavmWidgets: list[tuple[str, QWidget]] = [(n, w) for (n, w) in self.settingsManager.GetQAVMSettings().CreateWidgets(self.contentWidget) if w is not None]
		generalSettingsItem = self.AddSettingsEntrySelectable("QAVM", qavmWidgets)

		# Group settings by software handler
		workspace: QAVMWorkspace = app.GetWorkspace()
		swHandlersSet, _ = workspace.GetInvolvedSoftwareHandlers()
		for swHandler in sorted(swHandlersSet, key=lambda sh: sh.GetName()):
			if swSettings := self.settingsManager.GetSoftwareSettings(swHandler):
				allSwWidgets = list(swSettings.CreateWidgets(self.contentWidget))
				swSettingsWidgets: list[tuple[str, QWidget]] = [(n, s) for (n, s) in allSwWidgets if s is not None]
				if not swSettingsWidgets:
					continue  # Don't add software to the menu if it doesn't have any settings to show

				firstOriginalWidget = allSwWidgets[0][1] if allSwWidgets else None
				if firstOriginalWidget is not None:
					# First entry is directly associated with the software handler item (no named child)
					self.AddSettingsEntrySelectable(swHandler.GetName(), swSettingsWidgets)
				else:
					self.AddSettingsEntryContainer(swHandler.GetName(), swSettingsWidgets)

		# self.menuWidget.expandAll()
		self.menuWidget.expand(generalSettingsItem.index())
		self.menuWidget.selectionModel().select(generalSettingsItem.index(), self.menuWidget.selectionModel().SelectionFlag.ClearAndSelect)
	
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

	def AddSettingsEntrySelectable(self, title: str, widgets: list[tuple[str, QWidget]], parentItem: QStandardItem | None = None) -> QStandardItem:
		# The item itself is selectable and directly shows the first widget; remaining widgets are added as named children.
		item = QStandardItem(title)
		item.setEditable(False)
		item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
		firstWidget = widgets[0][1]
		item.setData(firstWidget, Qt.ItemDataRole.UserRole)  # Associate the first widget with the item
		self.contentWidget.addWidget(firstWidget)
		if parentItem is not None:
			parentItem.appendRow(item)
		else:
			self.menuModel.appendRow(item)
		for (name, widget) in widgets[1:]:
			self.AddSettingsEntry(name, widget, item)
		return item

	def AddSettingsEntryContainer(self, title: str, widgets: list[tuple[str, QWidget]], parentItem: QStandardItem | None = None) -> QStandardItem:
		# The item is a non-selectable container; all widgets are added as named children.
		item = QStandardItem(title)
		item.setEditable(False)
		item.setFlags(Qt.ItemFlag.ItemIsEnabled)
		if parentItem is not None:
			parentItem.appendRow(item)
		else:
			self.menuModel.appendRow(item)
		for (name, widget) in widgets:
			self.AddSettingsEntry(name, widget, item)
		return item

	def _onMenuSelectionChanged(self, selected, deselected):
		if selectedIndexes := selected.indexes():
			if item := self.menuModel.itemFromIndex(selectedIndexes[0]):
				# Find the corresponding widget in the QStackedWidget
				widgetIndex = self.contentWidget.indexOf(item.data(Qt.ItemDataRole.UserRole))
				if widgetIndex != -1:
					self.contentWidget.setCurrentIndex(widgetIndex)

	def _onMenuItemClicked(self, index):
		item = self.menuModel.itemFromIndex(index)
		if not item or item.parent() is not None:
			return  # Only handle root-level items

		# If this item has a directly associated widget, show it
		directWidget = item.data(Qt.ItemDataRole.UserRole)
		if directWidget is not None:
			widgetIndex = self.contentWidget.indexOf(directWidget)
			if widgetIndex != -1:
				self.contentWidget.setCurrentIndex(widgetIndex)
			return
		else:
			if item.hasChildren():
				self.menuWidget.expand(index)
				self.menuWidget.selectionModel().select(item.child(0).index(), self.menuWidget.selectionModel().SelectionFlag.ClearAndSelect)

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