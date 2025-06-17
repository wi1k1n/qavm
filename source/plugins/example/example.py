"""
copyright
"""

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.example'
PLUGIN_VERSION = '0.1.0'
PLUGIN_NAME = 'Example Plugin'
PLUGIN_DEVELOPER = 'Ilya Mazlov (mazlov.i.a@gmail.com)'
PLUGIN_WEBSITE = 'https://github.com/wi1k1n/qavm'

import os, subprocess, re, json, sys, logging, cv2, pyperclip, re
import datetime as dt, numpy as np
from pathlib import Path
from functools import partial
from typing import Any, Iterator

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, SoftwareBaseSettings, BaseTableBuilder, BaseContextMenu,
	BaseCustomView,	QualifierIdentificationConfig, BaseSettingsContainer, BaseSettingsEntry,
	BaseMenuItems, 
)
from qavm.qavmapi.gui import StaticBorderWidget, ClickableLabel, DateTimeTableWidgetItem, RunningBorderWidget
from qavm.qavmapi.utils import (
	GetQAVMDataPath, GetQAVMCachePath, GetAppDataPath, GetHashString, GetPrefsFolderPath,
	PlatformWindows, PlatformMacOS, PlatformLinux, PlatformName,
	OpenFolderInExplorer, GetTempDataPath, GetHashFile, GetQAVMTempPath,
	StartProcess, StopProcess, IsProcessRunning, GetPathSymlinkTarget, GetPathJunctionTarget,
	GetFileBirthtime
)
from qavm.qavmapi.media_cache import MediaCache
from qavm.qavmapi.icon_extractor import GetIconFromExecutable

from PyQt6.QtCore import (
	Qt, QProcess, QSize, QRect, QPoint, QModelIndex, QTimer, QPropertyAnimation, pyqtSignal, pyqtProperty,
	QEasingCurve, QPointF
)
from PyQt6.QtGui import (
	QFont, QColor, QPixmap, QAction, QBrush, QPainter, QImage, QPainter, QLinearGradient, QGradient
)
from PyQt6.QtWidgets import (
	QWidget, QLabel, QVBoxLayout, QMessageBox, QFormLayout, QLineEdit, QCheckBox, QTableWidgetItem,
	QMenu, QWidgetAction, QLayout, QStyledItemDelegate, QStyleOptionViewItem, QApplication, QTableWidget,
	QScrollBar, QInputDialog, QTabWidget
)

"""
QAVM can be extended by plugins. Each plugin is represented by a folder with a python script that has the same name as the folder.

Each plugin can implement multiple modules. Modules can be of different types, e.g. software, settings, etc.
"""

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

LOGS_PATH = GetQAVMDataPath()/'qavm-example.log'
loggerFileHandler = logging.FileHandler(LOGS_PATH)
loggerFileHandler.setLevel(logging.ERROR)
loggerFileHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(loggerFileHandler)

class ExampleQualifier(BaseQualifier):
	def ProcessSearchPaths(self, searchPaths: list[str]) -> list[str]:
		# At this point the searchPaths from QAVM preferences can be adjusted.
		# For example, you can add some default paths to search for the software.
		return searchPaths
	
	def GetIdentificationConfig(self) -> QualifierIdentificationConfig:
		return super().GetIdentificationConfig()
	
	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> bool:
		if not currentPath.is_dir():
			return False
		
		# Should contain at least one .exe file
		exeFiles: list[Path] = list(currentPath.glob('*.exe'))
		if not exeFiles:
			return False

		return True

class ExampleDescriptor(BaseDescriptor):
	def __init__(self, dirPath: Path, settings: SoftwareBaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__(dirPath, settings, fileContents)
		# There's already this info from the BaseDescriptor:
		# self.UID: str
		# self.dirPath: Path
		# self.settings: SoftwareBaseSettings
		# self.dirType: str  # '' - normal dir, 's' - symlink, 'j' - junction

		# This class is a representation of a single piece of software, which connects
		# together different parts of the plugin (e.g. TileBuilder, ContextMenu, etc.)
		self.execPaths: list[Path] = []

		if self.dirPath.is_dir():
			if not PlatformWindows():
				raise NotImplementedError('ExampleDescriptor is currently implemented only for Windows platform.')
			
			# Find the executable file in the directory
			self.execPaths = list(self.dirPath.glob('*.exe'))
			if self.execPaths:
				# Sort out with the following rules and take the first one:
				# being an .exe file
				# starting with capital ending with small letter
				# not having capital letters other than the first one
				# having space(s) in the middle
				# being the largest file
				self.execPaths.sort(key=lambda p: (p.name[0].isupper(), p.name[-1].islower(), p.name.islower(), ' ' in p.name, p.stat().st_size), reverse=True)
			else:
				logger.warning(f'No executable files found in {self.dirPath}')
	
	def GetExecutablePath(self) -> Path:
		return self.execPaths[0] if self.execPaths else Path()
	
	def __str__(self):
		return f'ExampleDescriptor: {os.path.basename(self.dirPath)}'
	
	def __repr__(self):
		return self.__str__()

class ExampleTileBuilder(BaseTileBuilder):
	def __init__(self, settings: SoftwareBaseSettings, contextMenu: BaseContextMenu):
		super().__init__(settings, contextMenu)
		# From BaseTileBuilder:
		# self.settings: SoftwareBaseSettings
		# self.contextMenu: BaseContextMenu
		# self.themeData: dict

	def CreateTileWidget(self, descriptor: ExampleDescriptor, parent) -> QWidget:
		descWidget: QWidget = self._createDescWidget(descriptor, parent)
		
		isProcessRunning: bool = IsProcessRunning(descriptor.UID)
		borderColor: QColor = QColor(Qt.GlobalColor.darkGreen) if isProcessRunning else QColor(self.themeData['secondaryDarkColor'])

		animatedBorderWidget = self._wrapWidgetInAnimatedBorder(descWidget, borderColor, isProcessRunning, parent)
		return animatedBorderWidget
	
	def _createDescWidget(self, desc: ExampleDescriptor, parent: QWidget):
		descWidget = QWidget(parent)

		secondaryDarkColor = self.themeData['secondaryDarkColor']
		descWidget.setStyleSheet(f"background-color: {secondaryDarkColor};")
		
		descLayout = QVBoxLayout(descWidget)
		margins: int = 5  # space from the inside labels to the border of the tile frame
		descLayout.setContentsMargins(margins, margins, margins, margins)
		descLayout.setSpacing(5)  # space between labels inside tile

		label = QLabel(str(desc.dirPath), parent)
		label.setFont(QFont('SblHebrew'))
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		descLayout.addWidget(label)

		toolTip: str = 'No executables found'
		if desc.execPaths:
			toolTip = 'Executables:\n'
			toolTip += '\n'.join([f'  {exePath.name}' for exePath in desc.execPaths])
		descWidget.setToolTip(toolTip)

		return descWidget
	
	def _wrapWidgetInAnimatedBorder(self, widget, accentColor: QColor, isAnimated: bool, parent):
		tailColor = QColor(accentColor)
		tailColor.setAlpha(30)
		
		if isAnimated:
			animBorderWidget = RunningBorderWidget(accentColor, tailColor, parent)
		else:
			animBorderWidget = StaticBorderWidget(accentColor, parent)
		
		animBorderLayout = animBorderWidget.layout()
		borderThickness = 5
		animBorderLayout.setContentsMargins(borderThickness, borderThickness, borderThickness, borderThickness)
		animBorderLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
		animBorderLayout.addWidget(widget)
		
		innerSize = widget.sizeHint()
		fullWidth = innerSize.width() + 2 * borderThickness
		fullHeight = innerSize.height() + 2 * borderThickness
		animBorderWidget.setFixedSize(QSize(fullWidth, fullHeight))

		return animBorderWidget

class ExampleTableBuilder(BaseTableBuilder):
	def GetTableCaptions(self) -> list[str]:
		return ['Folder name', 'Version', 'Path']
	
	def GetTableCellValue(self, desc: ExampleDescriptor, col: int) -> str | QTableWidgetItem:
		if col == 0:
			return desc.dirPath.name
		if col == 1:
			return "unknown"
		if col == 2:
			dirTypePrefix: str = f'({desc.dirType}) ' if desc.dirType else ''
			dirLinkTarget: str = ''
			if desc.dirType == 'S':
				dirLinkTarget = f' ( → {GetPathSymlinkTarget(desc.dirPath)})'
			elif desc.dirType == 'J':
				dirLinkTarget = f' ( → {GetPathJunctionTarget(desc.dirPath)})'
			return f'{dirTypePrefix}{str(desc.dirPath)}{dirLinkTarget}'
		return ''

class ExampleSettings(SoftwareBaseSettings):
	CONTAINER_DEFAULTS: dict[str, Any] = {
		'myExampleSetting': 'default value',  # Example setting
	}

	def CreateWidgets(self, parent: QWidget) -> list[tuple[str, QWidget]]:
		commonSettingsWidgets: list[tuple[str, QWidget]] = super().CreateWidgets(parent)

		tabsWidget: QTabWidget = QTabWidget(parent)
		if commonSettingsWidgets:
			tabsWidget.addTab(commonSettingsWidgets[0][1], commonSettingsWidgets[0][0])

		# Add more tabs if needed
		exampleSettingsWidget: QWidget = QLabel('This is an example settings tab.', parent)
		tabsWidget.addTab(exampleSettingsWidget, 'Example Settings')

		extraSettingsWidget: QWidget = QWidget(parent)
		extraSettingsLayout: QVBoxLayout = QVBoxLayout(extraSettingsWidget)
		extraSettingsLayout.setContentsMargins(10, 10, 10, 10)
		extraSettingsLayout.setSpacing(10)
		exampleLabel: QLabel = QLabel('This is an example extra settings tab.', extraSettingsWidget)
		exampleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		extraSettingsLayout.addWidget(exampleLabel)
		exampleLabel.setStyleSheet("color: darkblue; font-size: 16px; background-color: white;")
		exampleLabel.setMinimumHeight(50)

		return [
			('Example', tabsWidget),
			('Example Extra', extraSettingsWidget),
		]

	# def _settingChangedCheckbox(self, state, settingsEntry: list):
	# 	settingsEntry[0] = state == Qt.CheckState.Checked
	# 	self._emitVisualUpdateOnSettingsEntryChange(settingsEntry)

	# def _settingsChangedLineEdit(self, text, settingsEntry: list):
	# 	settingsEntry[0] = text
	# 	self._emitVisualUpdateOnSettingsEntryChange(settingsEntry)
	
	# def _emitVisualUpdateOnSettingsEntryChange(self, settingsEntry: list):
	# 	isTileUpdateRequired: bool = settingsEntry[3]
	# 	isTableUpdateRequired: bool = settingsEntry[4]
	# 	if isTileUpdateRequired:
	# 		self.tilesUpdateRequired.emit()
	# 	if isTableUpdateRequired:
	# 		self.tablesUpdateRequired.emit()

class ExampleContextMenu(BaseContextMenu):
	def CreateMenu(self, desc: ExampleDescriptor) -> QMenu:
		menu = QMenu()

		titleLabel: QLabel = QLabel(f'{desc.dirPath.name}')
		titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		titleLabel.setStyleSheet("font-style: italic;")
		titleLabel.setContentsMargins(0, 7, 0, 3)
		titleAction: QWidgetAction = QWidgetAction(menu)
		titleAction.setDefaultWidget(titleLabel)

		menu.addAction(titleAction)
		if path := desc.GetExecutablePath():
			menu.addAction(f'Run "{path.name}"', partial(self._run, desc))
			menu.addSeparator()
		menu.addAction('Open folder', partial(OpenFolderInExplorer, desc.dirPath))

		return menu

	def _run(self, desc: ExampleDescriptor, arguments: list[str] = []):
		StartProcess(desc.UID, desc.GetExecutablePath(), arguments)
		desc.updated.emit()

class ExampleMenuItems(BaseMenuItems):
	def GetMenus(self, parent) -> list[QMenu | QAction]:
		# This method can be used to create custom menus that can be added to the main QAVM window.
		# For example, you can create a menu with some actions related to the plugin.
		menu = QMenu('Example Plugin', parent)
		menu.addAction('Example Action 1', partial(self._exampleAction, 1))
		menu.addAction('Example Action 2', partial(self._exampleAction, 2))

		action = QAction('Example Action 3', parent, triggered=partial(self._exampleAction, 3))
		
		return [menu, action]
	
	def _exampleAction(self, id):
		QMessageBox.information(None, f'Example Action {id}', f'This is an example action {id} from the Example Plugin.')

class ExampleCustomView(BaseCustomView):
	def __init__(self, settings: SoftwareBaseSettings, parent=None):
		super().__init__(settings, parent)

		self.setMinimumSize(300, 200)

		layout = QVBoxLayout(self)
		label = QLabel('This is an example custom view widget.', self)
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(label)

		self.setLayout(layout)

def RegisterModuleSoftware():
	return [
		{
			'id': 'software.example1',  # this is a unique id under the PLUGIN_ID domain
			'name': 'Example',
			# 'description': 'Example software module for QAVM',
			# 'author': 'wi1k1n',
			# 'author_email': 'vfpkjd@gmail.com',

			'qualifier': ExampleQualifier,
			'descriptor': ExampleDescriptor,
			'settings': ExampleSettings,
			'menuitems': ExampleMenuItems,
			'tile_view': {
				'tile_builder': ExampleTileBuilder,
				'context_menu': ExampleContextMenu,
			},
			'table_view': {
				'table_builder': ExampleTableBuilder,
				'context_menu': ExampleContextMenu,
			},
			'custom_views': [
				{
					'name': 'My Custom View',
					'view_class': ExampleCustomView,  # This should be a BaseCustomView subclass
					# 'icon': 'example_icon.png',  # Path to the icon file relative to the plugin folder
				},
				{
					'name': 'Another Custom View',
					'view_class': ExampleCustomView,  # This can be the same or different widget
					# 'icon': 'another_icon.png',  # Path to the icon file relative to the plugin folder
				}
			]
		},
	]

def RegisterModuleSettings():
	return []