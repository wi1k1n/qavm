from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QPushButton, QSizePolicy, QMessageBox, QApplication,
	QTabWidget, QListWidget, QTreeWidget, QTreeWidgetItem, QHBoxLayout, QLabel, QListWidgetItem,
	QMenuBar, QMenu, QDialog, QCheckBox, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from functools import partial
from typing import Optional
import sys

from qavm.manager_plugin import PluginManager, QAVMPlugin, SoftwareHandler, UID, QAVMWorkspace
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings
from qavm.window_about import AboutDialog

import qavm.logs as logs
logger = logs.logger


class EditFavoritesDialog(QDialog):
	def __init__(self, pluginManager: PluginManager, qavmSettings: QAVMGlobalSettings, parent: QWidget | None = None):
		super().__init__(parent)
		self.pluginManager = pluginManager
		self.qavmSettings = qavmSettings
		self.setWindowTitle("Edit Favorites")
		self.setMinimumSize(500, 350)
		self.setModal(True)

		mainLayout = QVBoxLayout(self)

		scrollArea = QScrollArea()
		scrollArea.setWidgetResizable(True)
		scrollContent = QWidget()
		self.scrollLayout = QVBoxLayout(scrollContent)

		favoriteIDs: list[str] = self.qavmSettings.GetFavoriteWorkspaceIDs()
		self.checkboxes: list[tuple[QCheckBox, QAVMWorkspace]] = []

		for plugin in self.pluginManager.GetPlugins():
			for ws in plugin.GetWorkspaces():
				cb = QCheckBox(ws.GetName())
				cb.setToolTip(
					f'{plugin.GetName()}'
					f'\nVersion: {plugin.GetVersionStr()}'
					f'\nID: {ws.GetID()}'
				)
				cb.setChecked(ws.GetID() in favoriteIDs)
				self.scrollLayout.addWidget(cb)
				self.checkboxes.append((cb, ws))

		self.scrollLayout.addStretch()
		scrollArea.setWidget(scrollContent)
		mainLayout.addWidget(scrollArea)

		buttonLayout = QHBoxLayout()
		buttonLayout.addStretch()
		saveButton = QPushButton("Save")
		saveButton.clicked.connect(self._save)
		buttonLayout.addWidget(saveButton)
		mainLayout.addLayout(buttonLayout)

	def _save(self):
		favoriteIDs: list[str] = []
		for cb, ws in self.checkboxes:
			if cb.isChecked():
				favoriteIDs.append(ws.GetID())
		self.qavmSettings.SetFavoriteWorkspaceIDs(favoriteIDs)
		self.qavmSettings.Save()
		self.accept()


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

		self._setupMenuBar()

		self.tabWidget = QTabWidget(self)
		self.setCentralWidget(self.tabWidget)

		self.tabWidget.addTab(self._createFavoritesTab(), "Favorites")
		self.tabWidget.addTab(self._createPluginsTab(), "System Workspaces")

	def _setupMenuBar(self):
		menuBar: QMenuBar = self.menuBar()
		menuBar.setNativeMenuBar(True)

		fileMenu = QMenu("&File", self)
		editFavoritesAction = QAction("Edit &Favorites", self)
		editFavoritesAction.triggered.connect(self._showEditFavoritesDialog)
		fileMenu.addAction(editFavoritesAction)
		fileMenu.addSeparator()
		exitAction = QAction("E&xit", self)
		exitAction.triggered.connect(self.close)
		fileMenu.addAction(exitAction)
		menuBar.addMenu(fileMenu)

		helpMenu = QMenu("&Help", self)
		aboutAction = QAction("&About", self)
		aboutAction.triggered.connect(self._showAboutDialog)
		helpMenu.addAction(aboutAction)
		menuBar.addMenu(helpMenu)

	def _showEditFavoritesDialog(self):
		dialog = EditFavoritesDialog(self.pluginManager, self.qavmSettings, self)
		if dialog.exec() == QDialog.DialogCode.Accepted:
			self._refreshFavoritesTab()

	def _showAboutDialog(self):
		aboutDialog = AboutDialog(self, self.pluginManager)
		aboutDialog.exec()

	def _createFavoritesTab(self) -> QWidget:
		self.favoritesTab = QWidget()
		self.favoritesLayout = QVBoxLayout(self.favoritesTab)
		self._populateFavorites()
		return self.favoritesTab

	def _populateFavorites(self):
		favoriteIDs: list[str] = self.qavmSettings.GetFavoriteWorkspaceIDs()
		for plugin in self.pluginManager.GetPlugins():
			for ws in plugin.GetWorkspaces():
				if ws.GetID() not in favoriteIDs:
					continue
				button = QPushButton(ws.GetName())
				button.setToolTip(
					f'{plugin.GetName()}'
					f'\nVersion: {plugin.GetVersionStr()}'
					f'\nPlugin: {plugin.GetExecutablePath()}'
				)
				button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
				button.clicked.connect(partial(self.selectWorkspaceButtonClicked, ws))

				btnLayout = QHBoxLayout(button)
				btnLayout.setContentsMargins(8, 0, 8, 0)
				pluginLabel = QLabel(plugin.GetName())
				pluginLabel.setStyleSheet("font-style: italic; background: transparent;")
				pluginLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
				btnLayout.addWidget(pluginLabel, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
				btnLayout.addStretch()

				self.favoritesLayout.addWidget(button)

		if not favoriteIDs:
			emptyLabel = QLabel("No favorites yet. Use File > Edit Favorites to add some.")
			emptyLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
			self.favoritesLayout.addWidget(emptyLabel)

	def _refreshFavoritesTab(self):
		while self.favoritesLayout.count():
			item = self.favoritesLayout.takeAt(0)
			if widget := item.widget():
				widget.deleteLater()
		self._populateFavorites()

	def _createPluginsTab(self) -> QWidget:
		tab = QWidget()
		layout = QVBoxLayout(tab)

		for plugin in self.pluginManager.GetPlugins():
			for ws in plugin.GetWorkspaces():
				button = QPushButton(ws.GetName())
				button.setToolTip(
					f'{plugin.GetName()}'
					f'\nVersion: {plugin.GetVersionStr()}'
					f'\nPlugin: {plugin.GetExecutablePath()}'
				)
				button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
				button.clicked.connect(partial(self.selectWorkspaceButtonClicked, ws))

				btnLayout = QHBoxLayout(button)
				btnLayout.setContentsMargins(8, 0, 8, 0)
				pluginLabel = QLabel(plugin.GetName())
				pluginLabel.setStyleSheet("font-style: italic; background: transparent;")
				pluginLabel.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
				btnLayout.addWidget(pluginLabel, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
				btnLayout.addStretch()

				layout.addWidget(button)

		return tab

	# def createPresetsTab(self) -> QWidget:
	# 	swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()
		
	# 	items: list[QListWidgetItem] = []
	# 	for pluginID, softwareID, swHandler in swHandlers:
	# 		item: QListWidgetItem = QListWidgetItem(swHandler.GetName())
	# 		item.setToolTip(f'{pluginID}#{softwareID}')
	# 		item.setData(Qt.ItemDataRole.UserRole, swHandler)
	# 		items.append(item)

	# 	tab = QWidget()
	# 	layout = QHBoxLayout(tab)

	# 	# Left: Software Handlers list
	# 	self.swHandlersList = QListWidget()
	# 	for item in items:
	# 		self.swHandlersList.addItem(item)
	# 	self.swHandlersList.currentItemChanged.connect(lambda item: self.updatePresetTree(item.text(), item.data(Qt.ItemDataRole.UserRole)))
	# 	layout.addWidget(self.swHandlersList, 1)

	# 	# Right: Tree view
	# 	self.presetsTree = QTreeWidget()
	# 	self.presetsTree.setHeaderLabels(["Type", "Items"])
	# 	self.presetsTree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
	# 	layout.addWidget(self.presetsTree, 2)

	# 	return tab

	# def createCustomTab(self) -> QWidget:
	# 	tab = QWidget()
	# 	layout = QVBoxLayout(tab)

	# 	# Tree view for custom workspaces (you can populate this dynamically)
	# 	self.customTree = QTreeWidget()
	# 	self.customTree.setHeaderLabels(["ViewType", "View"])
	# 	self.customTree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
	# 	layout.addWidget(self.customTree)

	# 	swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()
	# 	treeData: dict = dict()  # 
	# 	for pluginID, softwareID, swHandler in swHandlers:
	# 		pluginSoftwareID: str = f'{pluginID}#{softwareID}'  # TODO: make it a function of UID class

	# 		swViewsData: dict = dict()
	# 		swViewsData['tiles'] = [UID.DataPathGetLastPart(viewID) for viewID in swHandler.GetTileBuilderClasses().keys() if viewID]
	# 		swViewsData['table'] = [UID.DataPathGetLastPart(viewID) for viewID in swHandler.GetTableBuilderClasses().keys() if viewID]
	# 		swViewsData['custom'] = [UID.DataPathGetLastPart(viewID) for viewID in swHandler.GetCustomViewClasses().keys() if viewID]
	# 		swViewsData['menuitems'] = [UID.DataPathGetLastPart(viewID) for viewID in swHandler.GetMenuItems().keys() if viewID]

	# 		treeData[swHandler.GetName()] = swViewsData
		
	# 	for swHandlerName, viewsData in treeData.items():
	# 		swHandlerItem = QTreeWidgetItem([swHandlerName, ''])
	# 		self.customTree.addTopLevelItem(swHandlerItem)
	# 		for viewType, views in viewsData.items():
	# 			viewTypeItem = QTreeWidgetItem([viewType, ''])
	# 			for view in views:
	# 				child = QTreeWidgetItem(['', view])
	# 				child.setCheckState(0, Qt.CheckState.Unchecked)
	# 				viewTypeItem.addChild(child)
	# 			swHandlerItem.addChild(viewTypeItem)
	# 			viewTypeItem.setExpanded(True)
	# 		swHandlerItem.setExpanded(True)


	# 	return tab

	# def updatePresetTree(self, presetName: str, swHandler: SoftwareHandler):
	# 	self.presetsTree.clear()
		
	# 	viewsData: dict = {
	# 		'tiles': list(swHandler.GetTileBuilderClasses().keys()),
	# 		'table': list(swHandler.GetTableBuilderClasses().keys()),
	# 		'custom': list(swHandler.GetCustomViewClasses().keys()),
	# 		'menuitems': list(swHandler.GetMenuItems().keys())
	# 	}
	# 	for key, items in viewsData.items():
	# 		parent = QTreeWidgetItem([key, ''])
	# 		for item in items:
	# 			child = QTreeWidgetItem(['', item])
	# 			child.setCheckState(0, Qt.CheckState.Unchecked)
	# 			parent.addChild(child)
	# 		self.presetsTree.addTopLevelItem(parent)
	# 		parent.setExpanded(True)

	def selectWorkspaceButtonClicked(self, workspace: QAVMWorkspace):
		self.qavmSettings.SetWorkspaceLast(workspace)
		self.qavmSettings.Save()  # TODO: should we save it here?

		self.dialogsManager.ShowWorkspace(workspace)
		self.close()