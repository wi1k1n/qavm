import json
from pathlib import Path
from typing import Any
from functools import partial

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QColor, QPainter, QBrush
from PyQt6.QtWidgets import (
	QWidget, QFormLayout, QCheckBox, QLineEdit, QApplication, QListWidget, QListWidgetItem,
	QVBoxLayout, QPushButton, QLabel, QFileDialog, QHBoxLayout, QTabWidget, QSizePolicy, 
)

import qavm.qavmapi.utils as utils
import qavm.qavmapi.gui as gui_utils

from qavm.qavmapi import BaseSettings, BaseSettingsContainer, BaseSettingsEntry, SoftwareBaseSettings
from qavm.manager_plugin import PluginManager, SoftwareHandler

import qavm.logs as logs
logger = logs.logger

class DeletableListWidget(QListWidget):
	def keyPressEvent(self, event: QKeyEvent) -> None:
		if event.key() == Qt.Key.Key_Delete:
			for item in self.selectedItems():
				self.takeItem(self.row(item))
		else:
			super().keyPressEvent(event)

# TODO: move this to gui utils
class CircleButton(QPushButton):
	def __init__(self, color: QColor, isBordered: bool = False, parent: QWidget | None = None):
		super().__init__(parent)
		self.setFixedSize(32, 32)
		self.color = color
		self.setCursor(Qt.CursorShape.PointingHandCursor)
		# self.setBordered(isBordered) # TODO: this doesn't work
		
	def paintEvent(self, event):
		painter = QPainter(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		brush = QBrush(self.color)
		painter.setBrush(brush)
		painter.setPen(Qt.PenStyle.NoPen)
		diameter = min(self.width(), self.height())
		painter.drawEllipse(0, 0, diameter, diameter)

	# def setBordered(self, bordered: bool):
	# 	if bordered:
	# 		self.setStyleSheet(f"border: 2px solid {self.color.name()}; border-radius: 16px;")
	# 	else:
	# 		self.setStyleSheet("border: none;")

class QAVMGlobalSettings(BaseSettings):
	CONTAINER_DEFAULTS: dict[str, Any] = {
		'selected_software_uid': '',
		'last_opened_tab': 0,
		'app_theme': gui_utils.GetDefaultTheme(),
		# searchSubfoldersDepth
		# hideOnClose
	}

	def GetSelectedSoftwareUID(self) -> str:
		app = QApplication.instance()
		if app.selectedSoftwareUID:
			return app.selectedSoftwareUID
		return self.GetSetting('selected_software_uid')

	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
		self.SetSetting('selected_software_uid', softwareUID)

	def GetAppTheme(self) -> str:
		return self.GetSetting('app_theme')
	
	def SetAppTheme(self, theme: str) -> None:
		gui_utils.SetTheme(theme)
		self.SetSetting('app_theme', theme)

	def CreateWidgets(self, parent: QWidget) -> list[tuple[str, QWidget]]:
		settingsWidget: QWidget = QWidget(parent)
		layout: QFormLayout = QFormLayout(settingsWidget)

		selectThemeWidget = self._createThemeSelectorWidget()
		layout.addRow('App Theme', selectThemeWidget)

		return [('Application', settingsWidget)]

	def _createThemeSelectorWidget(self) -> QWidget:
		self.tabWidget = QTabWidget()
		self.tabWidget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

		lightTab = QWidget()
		self.lightSwatchesLayout = QHBoxLayout()
		self.lightSwatchesLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
		lightTab.setLayout(self.lightSwatchesLayout)

		darkTab = QWidget()
		self.darkSwatchesLayout = QHBoxLayout()
		self.darkSwatchesLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
		darkTab.setLayout(self.darkSwatchesLayout)

		self._initSwatches()  # Fill swatches once

		self.tabWidget.addTab(lightTab, "Light")
		self.tabWidget.addTab(darkTab, "Dark")

		# Set active tab based on current theme
		isDarkMode, _ = self._parseThemeName(gui_utils.GetThemeName())
		self.tabWidget.setCurrentIndex(1 if isDarkMode else 0)

		themeSelectorWidget: QWidget = QWidget()
		layout = QVBoxLayout(themeSelectorWidget)
		layout.addWidget(self.tabWidget)
		return themeSelectorWidget

	def _initSwatches(self):
		themes: list[str] = gui_utils.GetThemesList()
		colorsByMode: dict[str, set[str]] = {'light': set(), 'dark': set()}

		for themeName in themes:
			isDark, color = self._parseThemeName(themeName)
			if QColor(color).isValid():
				mode = 'dark' if isDark else 'light'
				colorsByMode[mode].add(color)

		for mode, layout in [('light', self.lightSwatchesLayout), ('dark', self.darkSwatchesLayout)]:
			for colorName in sorted(colorsByMode[mode]):
				btn = CircleButton(QColor(colorName))
				btn.clicked.connect(partial(self.SetAppTheme, f"{mode}_{colorName}.xml"))
				btn.setToolTip(f'{colorName}')
				layout.addWidget(btn)

	def _parseThemeName(self, themeName: str) -> tuple[bool, str]:
		tokens = themeName.split('_', 1)
		if len(tokens) < 2:
			return (gui_utils.DEFAULT_THEME_MODE == 'dark', gui_utils.DEFAULT_THEME_COLOR)

		isDarkMode = tokens[0].lower() == 'dark'
		colorName = tokens[1].replace('.xml', '')
		if not QColor(colorName).isValid():
			return (isDarkMode, gui_utils.DEFAULT_THEME_COLOR)
		return (isDarkMode, colorName)


class SettingsManager:
	def __init__(self, app, prefsFolderPath: Path):
		self.app = app
		self.prefsFolderPath: Path = prefsFolderPath

		self.qavmGlobalSettings: QAVMGlobalSettings = QAVMGlobalSettings('qavm-global')
		self.softwareSettings: SoftwareBaseSettings = None

		# self.moduleSettings: dict[str, BaseSettings] = dict()

	def GetQAVMSettings(self) -> QAVMGlobalSettings:
		return self.qavmGlobalSettings
	
	def LoadQAVMSettings(self):
		self.prefsFolderPath.mkdir(parents=True, exist_ok=True)
		self.qavmGlobalSettings.Load()

	def SaveQAVMSettings(self):
		self.qavmGlobalSettings.Save()
	

	def GetSoftwareSettings(self) -> SoftwareBaseSettings:
		return self.softwareSettings
	
	def LoadSoftwareSettings(self):
		if not self.qavmGlobalSettings.GetSelectedSoftwareUID():
			raise Exception('No software selected')
		softwareHandler: SoftwareHandler = self.app.GetPluginManager().GetCurrentSoftwareHandler()
		self.softwareSettings = softwareHandler.GetSettings()
		self.softwareSettings.Load()

	def SaveSoftwareSettings(self):
		if not self.softwareSettings:
			raise Exception('No software settings loaded')
		self.softwareSettings.Save()
	
	# def LoadModuleSettings(self):
	# 	pluginManager: PluginManager = self.app.GetPluginManager()
	# 	settingsModules: list[tuple[str, str, SettingsHandler]] = pluginManager.GetSettingsHandlers()  # [pluginID, moduleID, SettingsHandler]
	# 	for pluginID, settingsID, settingsHandler in settingsModules:
	# 		moduleSettings: BaseSettings = settingsHandler.GetSettings()
	# 		moduleSettings.Load()
	# 		self.moduleSettings[f'{pluginID}#{settingsID}'] = moduleSettings
	
	# """ Returns dict of settings modules that are implemented in currently selected plugin: {moduleUID: BaseSettings}. The moduleUID is in form PLUGIN_ID#SettingsModuleID """
	# def GetModuleSettings(self) -> dict[str, BaseSettings]:
	# 	return self.moduleSettings