"""
copyright
"""
import os
import logging

from pathlib import Path
from functools import partial
from typing import Any, Optional

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, SoftwareBaseSettings, BaseTableBuilder,
	BaseCustomView,	QualifierIdentificationConfig, BaseMenuItem, 
)
from qavm.qavmapi.gui import (
	StaticBorderWidget, RunningBorderWidget, PathTableWidgetItem, 
)

from qavm.qavmapi.utils import (
	PlatformWindows, OpenFolderInExplorer, StartProcess, IsProcessRunning,
)

from PyQt6.QtCore import (
	Qt, QSize,
)
from PyQt6.QtGui import (
	QFont, QColor, QAction,
)
from PyQt6.QtWidgets import (
	QWidget, QLabel, QVBoxLayout, QMessageBox, QTableWidgetItem,
	QMenu, QWidgetAction, QLayout, QTabWidget
)

from utils import GetLogger
logger: logging.Logger = GetLogger(__name__)

class ExampleQualifierEXE(BaseQualifier):
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
	
class ExampleQualifierPNG(BaseQualifier):
	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> bool:
		return currentPath.is_dir() and any(list(currentPath.glob('*.png')))

class ExampleDescriptorBase(BaseDescriptor):
	def __init__(self, dirPath: Path, settings: SoftwareBaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__(dirPath, settings, fileContents)
		# There's already this info from the BaseDescriptor:
		# self.UID: str
		# self.dirPath: Path
		# self.settings: SoftwareBaseSettings
		# self.dirType: str  # '' - normal dir, 's' - symlink, 'j' - junction

		# This class is a representation of a single piece of software, which connects
		# together different parts of the plugin (e.g. TileBuilder, ContextMenu, etc.)
		self.targetPaths: list[Path] = []

		if self.dirPath.is_dir():
			if not PlatformWindows():
				raise NotImplementedError('Not implemented for non-Windows platforms.')
			
			# Find the executable file in the directory
			self.targetPaths = list(self.dirPath.glob(self._getGlobPattern()))
			if self.targetPaths:
				self._sortPaths()
			else:
				logger.warning(f'No target files found in {self.dirPath}')

	def _getGlobPattern(self) -> str:
		raise NotImplementedError('This method should be implemented in the subclass to return the glob pattern for the descriptor.')
	
	def _sortPaths(self):
		pass
	
	def __str__(self):
		return f'{self.__class__.__name__}: {os.path.basename(self.dirPath)}'
	
	def __repr__(self):
		return self.__str__()

class ExampleDescriptorEXE(ExampleDescriptorBase):
	def _getGlobPattern(self) -> str:
		return '*.exe'  # This is the pattern to find executable files in the directory
	
	def _sortPaths(self):
		# Sort out with the following rules and take the first one:
		# being an .exe file
		# starting with capital ending with small letter
		# not having capital letters other than the first one
		# having space(s) in the middle
		# being the largest file
		self.targetPaths.sort(key=lambda p: (p.name[0].isupper(), p.name[-1].islower(), p.name.islower(), ' ' in p.name, p.stat().st_size), reverse=True)
	
class ExampleDescriptorPNG(ExampleDescriptorBase):
	def _getGlobPattern(self) -> str:
		return '*.png'
	
class ExampleContextMenuBase(object):
	def _getContextMenu(self, desc: ExampleDescriptorEXE) -> QMenu:
		menu = QMenu()

		titleLabel: QLabel = QLabel(f'{desc.dirPath.name}')
		titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		titleLabel.setStyleSheet("font-style: italic;")
		titleLabel.setContentsMargins(0, 7, 0, 3)
		titleAction: QWidgetAction = QWidgetAction(menu)
		titleAction.setDefaultWidget(titleLabel)

		menu.addAction(titleAction)
		if desc.targetPaths:
			menu.addAction(f'Run "{desc.targetPaths[0].name}"', partial(self._run, desc))
			menu.addSeparator()
		menu.addAction('Open folder', partial(OpenFolderInExplorer, desc.dirPath))

		return menu

	def _run(self, desc: ExampleDescriptorEXE, arguments: list[str] = []):
		if desc.targetPaths:
			StartProcess(desc.UID, desc.targetPaths[0], arguments)
			desc.updated.emit()

class ExampleTileBuilderBoth(BaseTileBuilder, ExampleContextMenuBase):
	def __init__(self, settings: SoftwareBaseSettings):
		super().__init__(settings)
		# From BaseTileBuilder:
		# self.settings: SoftwareBaseSettings
		# self.themeData: dict

	def GetContextMenu(self, desc: BaseDescriptor) -> QMenu | None:
		return self._getContextMenu(desc)

	def GetName(self) -> str:
		return 'Example Tiles EXE/PNG'
	
	def ProcessDescriptors(self, descriptorType: str, descriptors: list[BaseDescriptor]) -> list[BaseDescriptor]:
		# This method is called to process the descriptors as an opportunity to filter them.
		return descriptors

	def CreateTileWidget(self, descriptor: ExampleDescriptorEXE, parent) -> QWidget:
		descWidget: QWidget = self._createDescWidget(descriptor, parent)
		
		isProcessRunning: bool = IsProcessRunning(descriptor.UID)
		borderColor: QColor = QColor(Qt.GlobalColor.darkGreen) if isProcessRunning else QColor(self.themeData['secondaryDarkColor'])

		animatedBorderWidget = self._wrapWidgetInAnimatedBorder(descWidget, borderColor, isProcessRunning, parent)
		return animatedBorderWidget
	
	def _createDescWidget(self, desc: ExampleDescriptorEXE, parent: QWidget):
		descWidget = QWidget(parent)

		secondaryDarkColor = self.themeData['secondaryDarkColor']
		descWidget.setStyleSheet(f"background-color: {secondaryDarkColor};")
		
		descLayout = QVBoxLayout(descWidget)
		margins: int = 5  # space from the inside labels to the border of the tile frame
		descLayout.setContentsMargins(margins, margins, margins, margins)
		descLayout.setSpacing(5)  # space between labels inside tile

		pathStr: str = str(desc.targetPaths[0]) if desc.targetPaths else 'No target file'
		label = QLabel(pathStr, parent)
		label.setFont(QFont('SblHebrew'))
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		descLayout.addWidget(label)

		toolTip: str = 'No executables found'
		if desc.targetPaths:
			toolTip = 'Executables:\n'
			toolTip += '\n'.join([f'  {exePath.name}' for exePath in desc.targetPaths])
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
	
class ExampleTileBuilderEXE(ExampleTileBuilderBoth):
	def GetName(self) -> str:
		return 'Example Tiles EXE'
	
	def GetSupportedDescriptorTypes(self, descriptorTypes: list[str]) -> list[str]:
		return ['exe']

class ExampleTileBuilderPNG(ExampleTileBuilderBoth):
	def GetName(self) -> str:
		return 'Example Tiles PNG'
	
	def GetSupportedDescriptorTypes(self, descriptorTypes: list[str]) -> list[str]:
		return ['png']

class ExampleTableBuilderEXE(BaseTableBuilder):
	def GetSupportedDescriptorTypes(self, descriptorTypes: list[str]) -> list[str]:
		return ['exe']
	
	def GetTableCaptions(self) -> list[str]:
		return ['Folder name', 'Version', 'Path']
	
	def GetTableCellValue(self, desc: ExampleDescriptorEXE, col: int) -> str | QTableWidgetItem:
		if col == 0:
			return desc.dirPath.name
		if col == 1:
			return "unknown"
		if col == 2:
			return PathTableWidgetItem(desc.dirPath)
		return ''
	
class ExampleTableBuilderPNG(ExampleTableBuilderEXE):
	def GetSupportedDescriptorTypes(self, descriptorTypes: list[str]) -> list[str]:
		return ['png']
	
	def GetTableCellValue(self, desc: ExampleDescriptorEXE, col: int) -> str | QTableWidgetItem:
		if col == 0:
			return '(dll) ' + desc.dirPath.name
		return super().GetTableCellValue(desc, col)

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

class ExampleMenuItemBase(BaseMenuItem):
	def _exampleAction(self, id):
		QMessageBox.information(None, f'Example Action {id}', f'This is an example action {id} from the Example Plugin.')

class ExampleMenuItem1(ExampleMenuItemBase):
	def GetMenu(self, parent) -> Optional[QMenu | QAction]:
		menu = QMenu('Example Plugin', parent)
		menu.addAction('Example Action 1', partial(self._exampleAction, 1))
		menu.addAction('Example Action 2', partial(self._exampleAction, 2))
		return menu
	
class ExampleMenuItem2(ExampleMenuItemBase):
	def GetMenu(self, parent) -> Optional[QMenu | QAction]:
		return QAction('Example Action 3', parent, triggered=partial(self._exampleAction, 3))

class ExampleCustomView1(BaseCustomView):
	def __init__(self, settings: SoftwareBaseSettings, parent=None):
		super().__init__(settings, parent)

		self.setMinimumSize(300, 200)

		layout = QVBoxLayout(self)
		label = QLabel('This is an example (1) custom view widget.', self)
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(label)

		self.setLayout(layout)

class ExampleCustomView2(BaseCustomView):
	def __init__(self, settings: SoftwareBaseSettings, parent=None):
		super().__init__(settings, parent)

		self.setMinimumSize(300, 200)

		layout = QVBoxLayout(self)
		label = QLabel('This is another example (2) custom view widget.', self)
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(label)

		self.setLayout(layout)


REGISTRATION_DATA = [
	{
		'id': 'software.first',  # this is a unique id under the PLUGIN_ID domain
		'name': 'Example First',

		'descriptors': {
			'exe': {
				'qualifier': ExampleQualifierEXE,
				'descriptor': ExampleDescriptorEXE,
			},
			'png': {
				'qualifier': ExampleQualifierPNG,
				'descriptor': ExampleDescriptorPNG,
			}
		},
		'views': {
			'tiles': {
				'exe': ExampleTileBuilderEXE,
				'png': ExampleTileBuilderPNG,
				'all': ExampleTileBuilderBoth,
			},
			'table': {
				'exe': ExampleTableBuilderEXE,
				'png': ExampleTableBuilderPNG,
				'both': ExampleTableBuilderEXE,
			},
			'custom': {
				'1': ExampleCustomView1,
				'2': ExampleCustomView2,
			}
		},
		'menuitems': {
			'1': ExampleMenuItem1,
			'2': ExampleMenuItem2,
		},
		'settings': ExampleSettings,
	}
]
WORKSPACES_DATA = {
	'First': ['software.first#*'],
}