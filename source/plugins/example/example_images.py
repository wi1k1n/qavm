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
	BaseCustomView,	QualifierIdentificationConfig, BaseMenuItem, QIConfigTargetType, 
)
from qavm.qavmapi.gui import (
	StaticBorderWidget, RunningBorderWidget, PathTableWidgetItem, NumberTableWidgetItem, 
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


class ExampleQualifierImages(BaseQualifier):
	def GetIdentificationConfig(self) -> QualifierIdentificationConfig:
		return QualifierIdentificationConfig(targetType=QIConfigTargetType.FILE)
	
	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> bool:
		return currentPath.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']

class ExampleDescriptorImages(BaseDescriptor):
	def __init__(self, path: Path, settings: SoftwareBaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__(path, settings, fileContents)
		# There's already this info from the BaseDescriptor:
		# self.UID: str
		# self.dirPath: Path
		# self.settings: SoftwareBaseSettings
		# self.dirType: str  # '' - normal dir, 's' - symlink, 'j' - junction

		self.fileSize: int = 0
		self.imageResolution: Optional[tuple[int, int]] = None  # (width, height) if image file

		if self.dirPath.is_file():
			self.fileSize = self.dirPath.stat().st_size
			if self.dirPath.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp']:
				if self.fileSize < 10 * 1024 * 1024:
					from PIL import Image
					logging.getLogger("PIL").setLevel(logging.WARNING)  # Suppress PIL warnings
					try:
						with Image.open(self.dirPath) as img:
							self.imageResolution = img.size  # (width, height)
					except Exception as e:
						logger.error(f'Error reading image {self.dirPath}: {e}')
						self.imageResolution = None

	def __str__(self):
		return f'{self.__class__.__name__}: {os.path.basename(self.dirPath)}'
	
	def __repr__(self):
		return self.__str__()
	
class ExampleContextMenuBase(object):
	def _getContextMenu(self, desc: ExampleDescriptorImages) -> QMenu:
		menu = QMenu()

		titleLabel: QLabel = QLabel(f'{desc.dirPath.name}')
		titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		titleLabel.setStyleSheet("font-style: italic;")
		titleLabel.setContentsMargins(0, 7, 0, 3)
		titleAction: QWidgetAction = QWidgetAction(menu)
		titleAction.setDefaultWidget(titleLabel)

		menu.addAction(titleAction)
		# if desc.targetPaths:
		# 	menu.addAction(f'Run "{desc.targetPaths[0].name}"', partial(self._run, desc))
		# 	menu.addSeparator()
		# menu.addAction('Open folder', partial(OpenFolderInExplorer, desc.dirPath))

		return menu

	# def _run(self, desc: ExampleDescriptorImages, arguments: list[str] = []):
	# 	if desc.targetPaths:
	# 		StartProcess(desc.UID, desc.targetPaths[0], arguments)
	# 		desc.updated.emit()

class ExampleTileBuilderImages(BaseTileBuilder, ExampleContextMenuBase):
	def __init__(self, settings: SoftwareBaseSettings):
		super().__init__(settings)
		# From BaseTileBuilder:
		# self.settings: SoftwareBaseSettings
		# self.themeData: dict

	def GetContextMenu(self, desc: ExampleDescriptorImages) -> QMenu | None:
		return self._getContextMenu(desc)
	
	def GetName(self) -> str:
		return '(Example) Tiles Images'

	def CreateTileWidget(self, descriptor: ExampleDescriptorImages, parent) -> QWidget:
		descWidget: QWidget = self._createDescWidget(descriptor, parent)
		
		isProcessRunning: bool = IsProcessRunning(descriptor.UID)
		borderColor: QColor = QColor(Qt.GlobalColor.darkGreen) if isProcessRunning else QColor(self.themeData['secondaryDarkColor'])

		animatedBorderWidget = self._wrapWidgetInAnimatedBorder(descWidget, borderColor, isProcessRunning, parent)
		return animatedBorderWidget
	
	def _createDescWidget(self, desc: ExampleDescriptorImages, parent: QWidget):
		descWidget = QWidget(parent)

		secondaryDarkColor = self.themeData['secondaryDarkColor']
		descWidget.setStyleSheet(f"background-color: {secondaryDarkColor};")
		
		descLayout = QVBoxLayout(descWidget)
		margins: int = 5  # space from the inside labels to the border of the tile frame
		descLayout.setContentsMargins(margins, margins, margins, margins)
		descLayout.setSpacing(5)  # space between labels inside tile

		# pathStr: str = str(desc.targetPaths[0]) if desc.targetPaths else 'No target file'
		resStr: str = f'{desc.imageResolution[0]}x{desc.imageResolution[1]}' if desc.imageResolution else 'unknown'
		label = QLabel(f'{desc.dirPath.name}<br>{desc.fileSize / 1024:.1f} KB<br>Resolution: {resStr}', parent)
		label.setFont(QFont('SblHebrew'))
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		descLayout.addWidget(label)

		# toolTip: str = 'No executables found'
		# if desc.targetPaths:
		# 	toolTip = 'Executables:\n'
		# 	toolTip += '\n'.join([f'  {exePath.name}' for exePath in desc.targetPaths])
		# descWidget.setToolTip(toolTip)

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


class ExampleTableBuilderImages(BaseTableBuilder):
	def GetName(self) -> str:
		return '(Example) Table Images'
	
	def GetTableCaptions(self) -> list[str]:
		return ['Name', 'Size', 'Resolution', 'Path']
	
	def GetTableCellValue(self, desc: ExampleDescriptorImages, col: int) -> str | QTableWidgetItem:
		if col == 0:
			return desc.dirPath.name
		elif col == 1:
			# return f'{desc.fileSize / 1024:.1f} KB'
			return NumberTableWidgetItem(desc.fileSize / 1024, '{} KB')
		elif col == 2:
			return f'{desc.imageResolution[0]}x{desc.imageResolution[1]}' if desc.imageResolution else 'unknown'
		elif col == 3:
			return PathTableWidgetItem(desc.dirPath)
		return ''

class ExampleSettingsImages(SoftwareBaseSettings):
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

		return [
			('Example', tabsWidget),
		]

REGISTRATION_DATA = [
	{
		'id': 'software.images',  # this is a unique id under the PLUGIN_ID domain
		'name': '(Example) Images',

		'descriptors': {
			'images': {
				'qualifier': ExampleQualifierImages,
				'descriptor': ExampleDescriptorImages,
			},
		},
		'views': {
			'tiles': {
				'images': ExampleTileBuilderImages,
			},
			'table': {
				'exe': ExampleTableBuilderImages,
			},
		},
		'settings': ExampleSettingsImages,
	}
]
WORKSPACES_DATA = {
	'Images': ['software.images#*'],
}