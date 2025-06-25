from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QPushButton, QSizePolicy, QMessageBox, QApplication,
	QTabWidget, QListWidget, QTreeWidget, QTreeWidgetItem, QHBoxLayout, QLabel
)
from PyQt6.QtCore import Qt
from functools import partial
import sys

from qavm.manager_plugin import PluginManager, QAVMPlugin, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings
import qavm.logs as logs

logger = logs.logger


class WorkspaceManagerWindow(QMainWindow):
	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)

		self.setWindowTitle("Workspace Manager")
		self.resize(640, 400)

		app = QApplication.instance()
		self.dialogsManager = app.GetDialogsManager()
		self.pluginManager: PluginManager = app.GetPluginManager()
		self.settingsManager: SettingsManager = app.GetSettingsManager()
		self.qavmSettings: QAVMGlobalSettings = self.settingsManager.GetQAVMSettings()

		self.tabWidget = QTabWidget(self)
		self.setCentralWidget(self.tabWidget)

		self.tabWidget.addTab(self.createPluginsTab(), "Plugins")
		self.tabWidget.addTab(self.createPresetsTab(), "Presets")
		self.tabWidget.addTab(self.createCustomTab(), "Custom")

	def createPluginsTab(self) -> QWidget:
		tab = QWidget()
		layout = QVBoxLayout(tab)

		swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()

		for pluginID, softwareID, softwareHandler in swHandlers:
			plugin: QAVMPlugin = self.pluginManager.GetPlugin(pluginID)
			swUID: str = f'{pluginID}#{softwareID}'
			button = QPushButton(softwareHandler.GetName())
			button.setToolTip(
				f'{plugin.GetName()}'
				f'\nVersion: {plugin.GetVersionStr()}'
				f'\nSWUID: {swUID}'
				f'\nPlugin: {plugin.GetExecutablePath()}'
			)
			button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
			button.clicked.connect(partial(self.selectPlugin, swUID))
			layout.addWidget(button)

		return tab

	def createPresetsTab(self) -> QWidget:
		tab = QWidget()
		layout = QHBoxLayout(tab)

		# Left: Presets list
		self.presetsList = QListWidget()
		self.presetsList.addItems(["Default", "Everything"])
		self.presetsList.currentTextChanged.connect(self.updatePresetTree)
		layout.addWidget(self.presetsList, 1)

		# Right: Tree view
		self.presetsTree = QTreeWidget()
		self.presetsTree.setHeaderLabels(["Type", "Items"])
		self.presetsTree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		layout.addWidget(self.presetsTree, 2)

		return tab

	def createCustomTab(self) -> QWidget:
		tab = QWidget()
		layout = QVBoxLayout(tab)

		# Tree view for custom workspaces (you can populate this dynamically)
		self.customTree = QTreeWidget()
		self.customTree.setHeaderLabels(["Type", "Items"])
		layout.addWidget(self.customTree)

		# Example: populate from settings or leave empty
		# self.populateCustomTree()

		return tab

	def updatePresetTree(self, presetName: str):
		self.presetsTree.clear()

		presets_data = {
			'Default': {
				'views': ['exe', 'png'],
				'table': ['1'],
				'custom': ['2'],
			},
			'Everything': {
				'views': ['exe', 'png', 'all'],
				'table': ['1', '2'],
				'custom': ['1', '2'],
			},
		}

		if presetName not in presets_data:
			return

		for key, items in presets_data[presetName].items():
			parent = QTreeWidgetItem([key, ''])
			for item in items:
				child = QTreeWidgetItem(['', item])
				child.setCheckState(0, Qt.CheckState.Unchecked)
				parent.addChild(child)
			self.presetsTree.addTopLevelItem(parent)
			parent.setExpanded(True)

	def selectPlugin(self, swUID: str):
		# # self.pluginSelected.emit(pluginUID, softwareID)
		# self.qavmSettings.SetSelectedSoftwareUID(swUID)
		
		# # this is needed since we don't distinguish between initial load and running "select plugin" action
		# self.qavmSettings.Save()  # TODO: doesn't sound super correct

		self.startMainWindow()
		self.close()

	def startMainWindow(self):
		# self.settingsManager.LoadSoftwareSettings()
		
		# app = QApplication.instance()
		# app.ResetSoftwareDescriptions()
		# self.dialogsManager.ResetPreferencesWindow()
		# self.dialogsManager.ResetMainWindow()

		self.dialogsManager.GetMainWindow().show()

	# def show(self):
	# 	# selectedSoftwareUID = self.qavmSettings.GetSelectedSoftwareUID()
	# 	# swHandlers: dict[str, SoftwareHandler] = {f'{pUID}#{sID}': swHandler for pUID, sID, swHandler in self.pluginManager.GetSoftwareHandlers()}  # {softwareUID: SoftwareHandler}

	# 	# if not swHandlers:
	# 	# 	QMessageBox.warning(self, "No Software Handlers", "No software handlers found. Please install at least one plugin with a software handler.", QMessageBox.StandardButton.Ok)
	# 	# 	logger.warning('No software handlers found')
	# 	# 	sys.exit(0)

	# 	# if selectedSoftwareUID and selectedSoftwareUID not in swHandlers:
	# 	# 	logger.warning(f'Selected software plugin not found: {selectedSoftwareUID}')
	# 	# 	return super(PluginSelectionWindow, self).show()
			
	# 	# if selectedSoftwareUID in swHandlers:
	# 	# 	logger.info(f'Selected software plugin: {selectedSoftwareUID}')
	# 	# 	return self.startMainWindow()
		
	# 	# if len(swHandlers) == 1:
	# 	# 	logger.info(f'The only software plugin: {list(swHandlers.keys())[0]}')
	# 	# 	self.qavmSettings.SetSelectedSoftwareUID(list(swHandlers.keys())[0])
	# 	# 	return self.startMainWindow()

	# 	super(PluginSelectionWindow, self).show()