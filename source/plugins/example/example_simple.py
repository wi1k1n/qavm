"""
copyright
"""
from pathlib import Path
from functools import partial
from typing import Optional

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, SoftwareBaseSettings, BaseTableBuilder,
)
from qavm.qavmapi.gui import (
	NumberTableWidgetItem, PathTableWidgetItem, 
)
from qavm.qavmapi.utils import OpenFolderInExplorer

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QLabel, QMessageBox, QTableWidgetItem, QMenu, QWidgetAction,
)

class SimpleQualifier(BaseQualifier):
	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> bool:
		return currentPath.is_dir() and len(list(currentPath.glob('*.*'))) > 0	

class SimpleDescriptor(BaseDescriptor):
	def __init__(self, dirPath: Path, settings: SoftwareBaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__(dirPath, settings, fileContents)

		self.filesCount: int = len(list(self.dirPath.glob('*.*')))
		self.foldersCount: int = len(list(self.dirPath.glob('*/')))

class ContextBase(object):
	def _getContextMenu(self, desc: BaseDescriptor) -> QMenu | None:
		menu = QMenu()

		titleLabel: QLabel = QLabel(f'{desc.dirPath.name}')
		titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		titleLabel.setStyleSheet("font-style: italic;")
		titleLabel.setContentsMargins(8, 7, 8, 7)
		
		titleAction: QWidgetAction = QWidgetAction(menu)
		titleAction.setDefaultWidget(titleLabel)

		menu.addAction(titleAction)
		menu.addSeparator()
		menu.addAction('Show info', partial(self._showDescriptor, desc))
		menu.addAction('Open folder', partial(OpenFolderInExplorer, desc.dirPath))

		return menu
	
	def _showDescriptor(self, desc: SimpleDescriptor):
		# This method can be used to show the descriptor in a custom way, e.g. open a dialog with details.
		QMessageBox.information(None, 'Descriptor Info', f'Directory: {desc.dirPath}\nFiles: {desc.filesCount}\nFolders: {desc.foldersCount}')
		desc.updated.emit()

class SimpleTableBuilder(BaseTableBuilder, ContextBase):
	def GetTableCaptions(self) -> list[str]:
		return ['Files count', 'Folders count', 'Path']
	
	def GetTableCellValue(self, desc: SimpleDescriptor, col: int) -> str | QTableWidgetItem:
		if col == 0:
			return NumberTableWidgetItem(desc.filesCount)
		if col == 1:
			return NumberTableWidgetItem(desc.foldersCount)
		if col == 2:
			return PathTableWidgetItem(desc.dirPath)
		return ''
	
	def GetContextMenu(self, desc: BaseDescriptor) -> Optional[QMenu]:
		return self._getContextMenu(desc)
	
class SimpleTileBuilder(BaseTileBuilder, ContextBase):
	def GetName(self) -> str:
		return 'Simple Tiles'
	
	def GetContextMenu(self, desc: BaseDescriptor) -> Optional[QMenu]:
		return self._getContextMenu(desc)
	
class SimpleSettings(SoftwareBaseSettings):
	pass


REGISTRATION_DATA = {
	'id': 'software.simple',
	'name': 'Example Simple',

	'descriptors': {
		'populatedfolders': {
			'qualifier': SimpleQualifier,
			'descriptor': SimpleDescriptor,
		}
	},
	'views': {
		'table': {'default': SimpleTableBuilder},
		'tiles': {'default': SimpleTileBuilder}
	},
	'settings': SimpleSettings,
}
WORKSPACES_DATA = {
	'Simple': ['software.simple#*'],
}