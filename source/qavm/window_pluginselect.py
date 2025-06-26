from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QPushButton, QSizePolicy, QMessageBox, QApplication,
	QTabWidget, QListWidget, QTreeWidget, QTreeWidgetItem, QHBoxLayout, QLabel, QListWidgetItem,

)
from PyQt6.QtCore import Qt
from functools import partial
from typing import Optional
import sys

from qavm.manager_plugin import PluginManager, QAVMPlugin, SoftwareHandler, UID, QAVMWorkspace
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

		swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()
		wsData: list[str] = []
		for pluginID, softwareID, swHandler in swHandlers:
			pluginSoftwareID: str = f'{pluginID}#{softwareID}'  # TODO: make it a function of UID class
			wsData.extend([f'{pluginSoftwareID}#{viewID}' for viewID in swHandler.GetTileBuilderClasses().keys()])
			wsData.extend([f'{pluginSoftwareID}#{viewID}' for viewID in swHandler.GetTableBuilderClasses().keys()])
			wsData.extend([f'{pluginSoftwareID}#{viewID}' for viewID in swHandler.GetCustomViewClasses().keys()])
			wsData.extend([f'{pluginSoftwareID}#{viewID}' for viewID in swHandler.GetMenuItems().keys()])
		
		self.workspace = QAVMWorkspace(wsData)

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
		swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()
		
		items: list[QListWidgetItem] = []
		for pluginID, softwareID, swHandler in swHandlers:
			item: QListWidgetItem = QListWidgetItem(swHandler.GetName())
			item.setToolTip(f'{pluginID}#{softwareID}')
			item.setData(Qt.ItemDataRole.UserRole, swHandler)
			items.append(item)

		tab = QWidget()
		layout = QHBoxLayout(tab)

		# Left: Software Handlers list
		self.swHandlersList = QListWidget()
		for item in items:
			self.swHandlersList.addItem(item)
		self.swHandlersList.currentItemChanged.connect(lambda item: self.updatePresetTree(item.text(), item.data(Qt.ItemDataRole.UserRole)))
		layout.addWidget(self.swHandlersList, 1)

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
		self.customTree.setHeaderLabels(["ViewType", "View"])
		self.customTree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		layout.addWidget(self.customTree)

		swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()
		treeData: dict = dict()  # 
		for pluginID, softwareID, swHandler in swHandlers:
			pluginSoftwareID: str = f'{pluginID}#{softwareID}'  # TODO: make it a function of UID class

			swViewsData: dict = dict()
			swViewsData['tiles'] = [UID.DataPathGetLastPart(viewID) for viewID in swHandler.GetTileBuilderClasses().keys() if viewID]
			swViewsData['table'] = [UID.DataPathGetLastPart(viewID) for viewID in swHandler.GetTableBuilderClasses().keys() if viewID]
			swViewsData['custom'] = [UID.DataPathGetLastPart(viewID) for viewID in swHandler.GetCustomViewClasses().keys() if viewID]
			swViewsData['menuitems'] = [UID.DataPathGetLastPart(viewID) for viewID in swHandler.GetMenuItems().keys() if viewID]

			treeData[swHandler.GetName()] = swViewsData
		
		for swHandlerName, viewsData in treeData.items():
			swHandlerItem = QTreeWidgetItem([swHandlerName, ''])
			self.customTree.addTopLevelItem(swHandlerItem)
			for viewType, views in viewsData.items():
				viewTypeItem = QTreeWidgetItem([viewType, ''])
				for view in views:
					child = QTreeWidgetItem(['', view])
					child.setCheckState(0, Qt.CheckState.Unchecked)
					viewTypeItem.addChild(child)
				swHandlerItem.addChild(viewTypeItem)
				viewTypeItem.setExpanded(True)
			swHandlerItem.setExpanded(True)


		return tab

	def updatePresetTree(self, presetName: str, swHandler: SoftwareHandler):
		self.presetsTree.clear()
		
		viewsData: dict = {
			'tiles': list(swHandler.GetTileBuilderClasses().keys()),
			'table': list(swHandler.GetTableBuilderClasses().keys()),
			'custom': list(swHandler.GetCustomViewClasses().keys()),
			'menuitems': list(swHandler.GetMenuItems().keys())
		}
		for key, items in viewsData.items():
			parent = QTreeWidgetItem([key, ''])
			for item in items:
				child = QTreeWidgetItem(['', item])
				child.setCheckState(0, Qt.CheckState.Unchecked)
				parent.addChild(child)
			self.presetsTree.addTopLevelItem(parent)
			parent.setExpanded(True)

	def selectPlugin(self, pluginSwUID: str):
		plugin: QAVMPlugin = self.pluginManager.GetPlugin(pluginSwUID)
		if not plugin:
			QMessageBox.warning(self, "Plugin Not Found", f"Plugin with UID '{pluginSwUID}' not found.", QMessageBox.StandardButton.Ok)
			logger.error(f'Plugin with UID {pluginSwUID} not found')
			return
		
		workspace = plugin.GetDefaultWorkspace()

		self.settingsManager.LoadWorkspaceSoftwareSettings(workspace)

		self.qavmSettings.SetWorkspaceLast(workspace)
		self.qavmSettings.Save()  # TODO: should we save it here?

		self.dialogsManager.ShowWorkspace(workspace)
		self.close()

	# def startMainWindow(self):
	# 	# self.settingsManager.LoadSoftwareSettings()
		
	# 	# app = QApplication.instance()
	# 	# app.ResetSoftwareDescriptions()
	# 	# self.dialogsManager.ResetPreferencesWindow()
	# 	# self.dialogsManager.ResetMainWindow()

	# 	self.dialogsManager.GetMainWindow().show()

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