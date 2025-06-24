import json
from pathlib import Path
from typing import Any
from functools import partial

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QKeyEvent, QColor, QPainter, QBrush
from PyQt6.QtWidgets import (
	QWidget, QFormLayout, QCheckBox, QLineEdit, QApplication, QListWidget, QListWidgetItem,
	QVBoxLayout, QPushButton, QLabel, QFileDialog, QHBoxLayout, QTabWidget, QSizePolicy, 
)

from qavm.manager_workspace import QAVMWorkspace

import qavm.qavmapi.utils as utils
import qavm.qavmapi.gui as gui_utils

from qavm.qavmapi import BaseSettings, BaseSettingsContainer, BaseSettingsEntry, SoftwareBaseSettings
from qavm.manager_plugin import PluginManager, SoftwareHandler

from qt_material import get_theme

import qavm.logs as logs
logger = logs.logger

# # TODO: move this to gui utils
# class CircleButton(QPushButton):
# 	def __init__(self, color: QColor, isBordered: bool = False, parent: QWidget | None = None):
# 		super().__init__(parent)
# 		self.setFixedSize(32, 32)
# 		self.color = color
# 		self.setCursor(Qt.CursorShape.PointingHandCursor)
# 		# self.setBordered(isBordered) # TODO: this doesn't work
		
# 	def paintEvent(self, event):
# 		painter = QPainter(self)
# 		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
# 		brush = QBrush(self.color)
# 		painter.setBrush(brush)
# 		painter.setPen(Qt.PenStyle.NoPen)
# 		diameter = min(self.width(), self.height())
# 		painter.drawEllipse(0, 0, diameter, diameter)

class ColorButton(QPushButton):
	def __init__(self, color: QColor, roundRadius: int, size: QSize = QSize(32, 32), parent=None):
		super().__init__(parent)

		self.color: QColor = color
		self.roundRadius: int = roundRadius

		self.isBordered: bool = False
		self.borderThickness: int = 2
		self.borderColor: str = 'black'
		
		self.setFixedSize(size)
		self.setStyleSheet(self._generateStyleSheet())
		self.setCursor(Qt.CursorShape.PointingHandCursor)

	def _generateStyleSheet(self) -> str:
		border = f"{self.borderThickness}px solid {self.borderColor}" if self.isBordered else "none"
		return f"""
			QPushButton {{
				background-color: {self.color.name()};
				border: {border};
				border-radius: {self.roundRadius}px;
			}}
		"""
	
	def SetBordered(self, bordered: bool):
		self.isBordered = bordered
		self.setStyleSheet(self._generateStyleSheet())

	def SetBorder(self, borderThickness: int = 2, borderColor: str = 'black'):
		self.borderThickness = borderThickness
		self.borderColor = borderColor
		self.setStyleSheet(self._generateStyleSheet())

	def SetColor(self, color: QColor):
		self.color = color
		self.setStyleSheet(self._generateStyleSheet())

	def SetRoundRadius(self, radius: int):
		self.roundRadius = radius
		self.setStyleSheet(self._generateStyleSheet())

class QAVMGlobalSettings(BaseSettings):
	CONTAINER_DEFAULTS: dict[str, Any] = {
		'selected_software_uid': '',
		'last_opened_tab': 0,
		'app_theme': gui_utils.GetDefaultTheme(),
		'search_paths_global': [],
		# searchSubfoldersDepth
		# hideOnClose
		'workspace_last': {
			'views': [
				'in.wi1k.tools.qavm.plugin.example#software.example1.view.tiles.1',
				'in.wi1k.tools.qavm.plugin.example#software.example1.view.tiles.2',
				'in.wi1k.tools.qavm.plugin.example#software.example1.view.table.1',
				'in.wi1k.tools.qavm.plugin.example#software.example1.view.table.2',
				'in.wi1k.tools.qavm.plugin.example#software.example1.view.custom.1',
				'in.wi1k.tools.qavm.plugin.example#software.example1.view.custom.2',
			],
			'manuitems': [],
		},  # the workspace is a dict: {'view': [], 'menuitems': []}, where lists are the list of IDs
	}

	def GetSelectedSoftwareUID(self) -> str:
		app = QApplication.instance()
		if app.selectedSoftwareUID is None:  # That's the way to force no selected software UID
			return ''
		if app.selectedSoftwareUID:  # That's the way to force specific software UID
			return app.selectedSoftwareUID
		# If it's empty otherwise, get the selected software UID from settings
		return self.GetSetting('selected_software_uid')

	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
		self.SetSetting('selected_software_uid', softwareUID)

	def GetAppTheme(self) -> str:
		return self.GetSetting('app_theme')
	
	def SetAppTheme(self, theme: str) -> None:
		gui_utils.SetTheme(theme)
		self.SetSetting('app_theme', theme)

	def GetGlobalSearchPaths(self) -> list[str]:
		return self.GetSetting('search_paths_global')
	
	def SetGlobalSearchPaths(self, paths: list[str]) -> None:
		if not isinstance(paths, list):
			logger.error(f'Search paths must be a list, got {type(paths)}')
			return
		self.SetSetting('search_paths_global', paths)

	def GetWorkspaceLast(self) -> QAVMWorkspace:
		return QAVMWorkspace(self.GetSetting('workspace_last'))

	def CreateWidgets(self, parent: QWidget) -> list[tuple[str, QWidget]]:
		settingsWidget: QWidget = QWidget(parent)
		layout: QFormLayout = QFormLayout(settingsWidget)

		selectThemeWidget = self._createThemeSelectorWidget(parent)
		layout.addRow('App Theme', selectThemeWidget)

		searchPathsWidget = self._createSearchPathsWidget(parent)
		layout.addRow('Search Paths (Global)', searchPathsWidget)

		return [('Application', settingsWidget)]
	
	# TODO: This is very similar to the one in SoftwareBaseSettings, consider refactoring
	def _createSearchPathsWidget(self, parent: QWidget | None = None) -> QWidget:
		widget = QWidget(parent)
		layout = QVBoxLayout(widget)

		self.searchPathsWidget = gui_utils.FolderPathsListWidget()
		self.searchPathsWidget.itemChanged.connect(lambda _: self._updateSearchPathsSetting())
		self.searchPathsWidget.itemDeleted.connect(lambda _: self._updateSearchPathsSetting())
		self.searchPathsWidget.urlDropped.connect(self._searchPathFolderDropped)

		for path in self.GetSetting('search_paths_global'):
			self._addSearchPathToList(path)

		layout.addWidget(self.searchPathsWidget)

		addButton = QPushButton('Browse', widget)
		addButton.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
		addButton.clicked.connect(self._selectAndAddSearchPath)
		
		buttonLayout = QHBoxLayout()
		buttonLayout.addStretch()  # Pushes the button to the right
		buttonLayout.addWidget(addButton)
		layout.addLayout(buttonLayout)

		return widget

	def _selectAndAddSearchPath(self):
		""" Opens a file dialog to select a directory and adds it to the search paths. """
		dirPath = QFileDialog.getExistingDirectory(self.searchPathsWidget, 'Select Search Path')
		if dirPath:
			self._addSearchPathToList(dirPath)
			self._updateSearchPathsSetting()

	def _searchPathFolderDropped(self, path: str):
		if not Path(path).is_dir():
			return
		self._addSearchPathToList(path)
		self._updateSearchPathsSetting()
		
	def _addSearchPathToList(self, path: str):
		""" Adds a new search path to the QListWidget if it doesn't already exist. """
		if not path:
			return
		path = str(Path(path).resolve())
		if not any(self.searchPathsWidget.item(i).text() == path for i in range(self.searchPathsWidget.count())):
			item = QListWidgetItem(path)
			item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
			self.searchPathsWidget.addItem(item)

	def _updateSearchPathsSetting(self):
		""" Updates the search paths setting based on the current items in the QListWidget. """
		self.SetSetting('search_paths_global', [self.searchPathsWidget.item(i).text() for i in range(self.searchPathsWidget.count())])

	def _createThemeSelectorWidget(self, parent: QWidget | None = None) -> QWidget:
		self.tabWidget = QTabWidget(parent)
		self.tabWidget.setTabPosition(QTabWidget.TabPosition.North)
		self.tabWidget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

		lightTab = QWidget()
		self.lightSwatchesLayout = QHBoxLayout()
		self.lightSwatchesLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
		self.lightSwatchesLayout.setContentsMargins(0, 0, 0, 0)
		lightTab.setLayout(self.lightSwatchesLayout)

		darkTab = QWidget()
		self.darkSwatchesLayout = QHBoxLayout()
		self.darkSwatchesLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
		self.darkSwatchesLayout.setContentsMargins(0, 0, 0, 0)
		darkTab.setLayout(self.darkSwatchesLayout)

		self._initSwatches()  # Fill swatches once

		self.tabWidget.addTab(lightTab, "Light")
		self.tabWidget.addTab(darkTab, "Dark")

		# Set active tab based on current theme
		darkMode, _ = self._parseThemeName(gui_utils.GetThemeName())
		self.tabWidget.setCurrentIndex(1 if darkMode == 'dark' else 0)

		themeSelectorWidget: QWidget = QWidget()
		layout = QVBoxLayout(themeSelectorWidget)
		layout.addWidget(self.tabWidget)
		return themeSelectorWidget

	def _initSwatches(self):
		# themeName: (darkMode, color)
		themesParsed: dict[str, tuple[str, QColor]] = {
			themeName: self._parseThemeName(themeName) for themeName in gui_utils.GetThemesList()
		}
		
		self._swatchButtons: dict[str, ColorButton] = {}
		curThemeName: str = gui_utils.GetThemeName()

		for themeName, (darkMode, color) in themesParsed.items():
			if not color.isValid():
				continue
			layout = self.darkSwatchesLayout if darkMode == 'dark' else self.lightSwatchesLayout
			# btn = CircleButton(color)
			btn = ColorButton(color, roundRadius=5, size=QSize(20, 20))
			self._setSwatchBorder(btn, themeName == curThemeName)
			btn.clicked.connect(partial(self._onSwatchClicked, themeName))
			btn.setToolTip(f'{themeName}')
			layout.addWidget(btn)
			self._swatchButtons[themeName] = btn

	def _onSwatchClicked(self, themeName: str):
		self.SetAppTheme(themeName)
		for theme, btn in self._swatchButtons.items():
			self._setSwatchBorder(btn, themeName == theme)
	
	def _setSwatchBorder(self, button: ColorButton, isBordered: bool = True):
		if not isBordered:
			button.SetBordered(False)
			return
		
		curThemeName: str = gui_utils.GetThemeName()
		darkMode, _ = self._parseThemeName(curThemeName)
		borderColor = 'white' if darkMode == 'dark' else 'black'
		button.SetBordered(True)
		button.SetBorder(borderColor=borderColor)

	def _parseThemeName(self, themeName: str) -> tuple[str, QColor]:
		tokens = themeName.split('_', 1)
		if len(tokens) < 2:
			return (gui_utils.DEFAULT_THEME_MODE, QColor(gui_utils.DEFAULT_THEME_COLOR))
		
		darkMode = 'dark' if tokens[0].lower() == 'dark' else 'light'

		qtTheme = get_theme(themeName)
		if not isinstance(qtTheme, dict) or 'primaryColor' not in qtTheme:
			return (darkMode, QColor(gui_utils.DEFAULT_THEME_COLOR))

		color = QColor(qtTheme['primaryColor'])
		if not color.isValid():
			return (darkMode, QColor(gui_utils.DEFAULT_THEME_COLOR))
		return (darkMode, color)


class SettingsManager:
	def __init__(self, prefsFolderPath: Path):
		self.prefsFolderPath: Path = prefsFolderPath

		self.qavmGlobalSettings: QAVMGlobalSettings = QAVMGlobalSettings('qavm-global')
		self.softwareSettings: dict[SoftwareHandler, SoftwareBaseSettings] = dict()

	def GetQAVMSettings(self) -> QAVMGlobalSettings:
		""" Returns the global QAVM settings. """
		return self.qavmGlobalSettings
	
	def LoadQAVMSettings(self):
		""" Loads the global QAVM settings. """
		self.prefsFolderPath.mkdir(parents=True, exist_ok=True)
		self.qavmGlobalSettings.Load()

	def SaveQAVMSettings(self):
		""" Saves the global QAVM settings. """
		self.qavmGlobalSettings.Save()

	def GetSoftwareSettings(self, swHandler: SoftwareHandler) -> SoftwareBaseSettings | None:
		return self.softwareSettings.get(swHandler, None)
	
	# def LoadSoftwareSettings(self):
	# 	if not self.qavmGlobalSettings.GetSelectedSoftwareUID():
	# 		raise Exception('No software selected')
	# 	softwareHandler: SoftwareHandler = self.app.GetPluginManager().GetCurrentSoftwareHandler()
	# 	self.softwareSettings = softwareHandler.GetSettings()
	# 	self.softwareSettings.Load()

	# def SaveSoftwareSettings(self):
	# 	if not self.softwareSettings:
	# 		raise Exception('No software settings loaded')
	# 	self.softwareSettings.Save()

	def LoadWorkspaceSoftwareSettings(self, workspace: QAVMWorkspace) -> None:
		""" Loads the software settings for the workspace views. """
		if not workspace or workspace.IsEmpty():
			return
		sfHandlers, notFoundPlugins = workspace.GetInvolvedSoftwareHandlers()
		for swHandler in sfHandlers:
			if not swHandler:
				continue
			self.softwareSettings[swHandler] = swHandler.GetSettings()
			self.softwareSettings[swHandler].Load()