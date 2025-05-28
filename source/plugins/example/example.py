"""
copyright
"""

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.example'
PLUGIN_VERSION = '0.1.0'

import os, subprocess, re, json, sys, logging, cv2, pyperclip, re
import datetime as dt, numpy as np
from pathlib import Path
from functools import partial
from typing import Any, Iterator

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings, BaseTableBuilder, BaseContextMenu
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
	QScrollBar, QInputDialog
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
	
	def GetIdentificationConfig(self) -> dict:
		return super().GetIdentificationConfig()
	
	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> bool:
		return True

class ExampleDescriptor(BaseDescriptor):
	def __init__(self, dirPath: Path, settings: BaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__(dirPath, settings, fileContents)
		# There's already this info from the BaseDescriptor:
		# self.UID: str
		# self.dirPath: Path
		# self.settings: BaseSettings
		# self.dirType: str  # '' - normal dir, 's' - symlink, 'j' - junction

		# This class is a representation of a single piece of software, which connects
		# together different parts of the plugin (e.g. TileBuilder, ContextMenu, etc.)
	
	def GetExecutablePath(self) -> Path:
		# if PlatformWindows():
		# 	return self.dirPath/'Cinema 4D.exe'
		# elif PlatformMacOS():
		# 	return self.dirPath/'Cinema 4D.app'
		# elif PlatformLinux():
		# 	raise NotImplementedError('Linux is not supported yet')
		return super().GetExecutablePath()
	
	def __str__(self):
		return f'ExampleDescriptor: {os.path.basename(self.dirPath)}'
	
	def __repr__(self):
		return self.__str__()

class ExampleTileBuilder(BaseTileBuilder):
	def __init__(self, settings: BaseSettings, contextMenu: BaseContextMenu):
		super().__init__(settings, contextMenu)
		# From BaseTileBuilder:
		# self.settings: BaseSettings
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

		toolTip: str = str(desc.dirPath)
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

class ExampleSettings(BaseSettings):
	def __init__(self) -> None:
		super().__init__()

		self.settings: dict[str, list] = {  # key: (defaultValue, text, tooltip, isTileUpdateRequired, isTableUpdateRequired)
			'exampleCheckbox': 	[True, 'Example checkbox', 'This is an example checkbox setting', False, False],
		}

		self.prefFilePath: Path = GetPrefsFolderPath()/'example-preferences.json'
		if not self.prefFilePath.exists():
			logger.info(f'Example settings file not found, creating a new one. Path: {self.prefFilePath}')
			self.Save()
	
	def __getitem__(self, key: str) -> Any:
		return self.settings.get(key, None)
	
	def GetName(self) -> str:
		return 'Example'

	def Load(self):
		with open(self.prefFilePath, 'r') as f:
			try:
				data: dict = json.loads(f.read())
				for key in self.settings.keys():
					if key not in data:
						return logger.error(f'Missing key in preferences data: {key}')
					if type(data[key]) != type(self.settings[key][0]):
						logger.error(f'Incompatible preferences data type for #{key}!')
						return False
					self.settings[key][0] = data[key]
			except Exception as e:
				logger.exception(f'Failed to parse settings data: {e}')

	def Save(self):
		if not self.prefFilePath.parent.exists():
			logger.info(f"Example preferences folder doesn't exist. Creating: {self.prefFilePath.parent}")
			self.prefFilePath.parent.mkdir(parents=True, exist_ok=True)
		with open(self.prefFilePath, 'w') as f:
			data: dict[str, Any] = {key: val[0] for key, val in self.settings.items()}
			f.write(json.dumps(data))

	def CreateWidget(self, parent: QWidget) -> QWidget:
		settingsWidget: QWidget = QWidget(parent)
		formLayout: QFormLayout = QFormLayout(settingsWidget)

		# TODO: refactor this
		def addRowTyped(key: str):
			settingsEntry: list = self.settings[key]
			text: str = settingsEntry[1]
			value: Any = settingsEntry[0]
			tooltip: str = settingsEntry[2]

			textLabel = QLabel(text)
			textLabel.setToolTip(tooltip)
			if isinstance(value, bool):
				checkbox = QCheckBox()
				checkbox.setChecked(value)
				checkbox.checkStateChanged.connect(partial(self._settingChangedCheckbox, settingsEntry=settingsEntry))
				formLayout.addRow(textLabel, checkbox)
				return checkbox
			if isinstance(value, str):
				lineEdit = QLineEdit(value)
				lineEdit.textChanged.connect(partial(self._settingsChangedLineEdit, settingsEntry=settingsEntry))
				formLayout.addRow(textLabel, lineEdit)
				return lineEdit
			return None

		for key in self.settings.keys():
			if addRowTyped(key) is None:
				logger.info(f'Unknown value type for key: {key}')

		# formLayout.addRow('Adjust folder name', QCheckBox())

		return settingsWidget

	def _settingChangedCheckbox(self, state, settingsEntry: list):
		settingsEntry[0] = state == Qt.CheckState.Checked
		self._emitVisualUpdateOnSettingsEntryChange(settingsEntry)

	def _settingsChangedLineEdit(self, text, settingsEntry: list):
		settingsEntry[0] = text
		self._emitVisualUpdateOnSettingsEntryChange(settingsEntry)
	
	def _emitVisualUpdateOnSettingsEntryChange(self, settingsEntry: list):
		isTileUpdateRequired: bool = settingsEntry[3]
		isTableUpdateRequired: bool = settingsEntry[4]
		if isTileUpdateRequired:
			self.tilesUpdateRequired.emit()
		if isTableUpdateRequired:
			self.tablesUpdateRequired.emit()

class ExampleContextMenu(BaseContextMenu):
	def CreateMenu(self, desc: ExampleDescriptor) -> QMenu:
		menu = QMenu()

		titleLabel: QLabel = QLabel(f'{desc.dirPath.name}')
		titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		titleLabel.setContentsMargins(0, 7, 0, 3)
		titleAction: QWidgetAction = QWidgetAction(menu)
		titleAction.setDefaultWidget(titleLabel)

		menu.addAction(titleAction)
		menu.addAction('Example action', partial(self._run, desc))

		menu.addSeparator()
		menu.addAction('Open folder', partial(OpenFolderInExplorer, desc.dirPath))

		return menu

	def _run(self, desc: ExampleDescriptor):
		QMessageBox.information(None, "Example action", f'The example action was triggered for {desc.dirPath.name}')

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
			'tile_view': {
				'tile_builder': ExampleTileBuilder,
				'context_menu': ExampleContextMenu,
			},
			'table_view': {
				'table_builder': ExampleTableBuilder,
				'context_menu': ExampleContextMenu,
			},
		},
	]

def RegisterModuleSettings():
	return []