from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtWidgets import QWidget, QLabel, QTableWidgetItem, QMenu

from qavm.qavmapi import utils
from qavm.qavmapi.gui import GetThemeData

##############################################################################
#############################  ##############################
##############################################################################

class BaseSettings(QObject):
	tilesUpdateRequired = pyqtSignal()
	tablesUpdateRequired = pyqtSignal()

	def Load(self):
		pass
	def Save(self):
		pass
	def CreateWidget(self, parent):
		pass

	def GetName(self) -> str:  # TODO: should use the one from connected software handler?
		return 'BaseSettings'

##############################################################################
########################### QAVM Plugin: Software ############################
##############################################################################

# TODO: rename this and others to BaseSoftwareQualifier?
class BaseQualifier(object):
	def __init__(self):
		pass

	def ProcessSearchPaths(self, searchPaths: list[str]) -> list[str]:
		""" Search paths list can be modified here (e.g. if some regex adjustments are needed based on searchPaths themselves or some default source paths are to be added). """
		return searchPaths
	
	# TODO: Add support for subfolder file list
	def GetIdentificationConfig(self) -> dict:
		""" Sets the identification mask for the qualifier."""
		return {
			'requiredFileList': [],  # list of files that MUST be present
			'requiredDirList': [],  # list of directories that MUST be present
			'negativeFileList': [],  # list of files that MUST NOT be present
			'negativeDirList': [],  # list of directories that MUST NOT be present

			'fileContentsList': [],  # list of files to be read from the disk: tuples: (filename, isBinary, lengthLimit)
		}

	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> list[str]:
		return True

class BaseDescriptor(QObject):
	updated = pyqtSignal()

	def __init__(self, dirPath: Path, settings: BaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__()
		self.UID: str = utils.GetHashString(str(dirPath))
		self.dirPath: Path = dirPath
		self.dirType: str = self._retrieveDirType()  # '' - normal dir, 's' - symlink, 'j' - junction
		self.settings: BaseSettings = settings

	def __hash__(self) -> int:
		return hash(str(self.dirPath))

	def __str__(self):
		return 'BaseDescriptor'
	
	def __repr__(self):
		return self.__str__()
	
	def _retrieveDirType(self) -> str:
		dirType = ''
		if self.dirPath.is_symlink():
			dirType = 'S'
		elif self._isDirJunction(self.dirPath):
			dirType = 'J'
		return dirType
	
	def _isDirJunction(self, path: Path) -> bool:
		if not path.is_dir() or not utils.PlatformWindows():
			return False
		
		import ctypes
		FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
		attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
		return attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT) and not path.is_symlink()

class BaseContextMenu(QObject):
	def __init__(self, settings: BaseSettings):
		self.settings: BaseSettings = settings
	
	def CreateMenu(self, desc: BaseDescriptor) -> QMenu:
		return QMenu()

class BaseBuilder(QObject):
	def __init__(self, settings: BaseSettings, contextMenu: BaseContextMenu):
		self.settings: BaseSettings = settings
		self.contextMenu: BaseContextMenu = contextMenu
		self.themeData: dict[str, str | None] | None = GetThemeData()

class BaseTileBuilder(BaseBuilder):
	def CreateTileWidget(self, descriptor: BaseDescriptor, parent) -> QWidget:
		return QLabel(str(descriptor.dirPath), parent)

class BaseTableBuilder(BaseBuilder):	
	def GetTableCaptions(self) -> list[str]:
		return ['Path']
	
	def GetTableCellValue(self, desc: BaseDescriptor, col: int) -> str | QTableWidgetItem:
		return str(desc.dirPath)
	
	def GetItemDelegateClass(self) -> QTableWidgetItem.__class__:
		return QTableWidgetItem
	
	# TODO: change key from int to enum. Currently 0 - LMB, 1 - RMB, 2 - MMB
	def HandleClick(self, desc: BaseDescriptor, row: int, col: int, isDouble: bool, key: int, modifiers: Qt.KeyboardModifier):
		pass