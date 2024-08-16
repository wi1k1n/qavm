from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QWidget, QLabel, QTableWidgetItem, QMenu

from qavm.qavmapi import utils

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

class BaseDescriptor(object):
	def __init__(self, dirPath: Path, settings: BaseSettings, fileContents: dict[str, str | bytes]):
		self.UID: str = utils.GetHashString(str(dirPath))
		self.dirPath: Path = dirPath
		self.settings: BaseSettings = settings

	def __hash__(self) -> int:
		return hash(str(self.dirPath))

	def __str__(self):
		return 'BaseDescriptor'
	
	def __repr__(self):
		return self.__str__()

class BaseContextMenu(QObject):
	def __init__(self, settings: BaseSettings):
		self.settings: BaseSettings = settings
	
	def CreateMenu(self, desc: BaseDescriptor) -> QMenu:
		return QMenu()

class BaseBuilder(QObject):
	def __init__(self, settings: BaseSettings, contextMenu: BaseContextMenu):
		self.settings: BaseSettings = settings
		self.contextMenu: BaseContextMenu = contextMenu

class BaseTileBuilder(BaseBuilder):
	def CreateTileWidget(self, descriptor: BaseDescriptor, parent) -> QWidget:
		return QLabel(str(descriptor.dirPath), parent)

class BaseTableBuilder(BaseBuilder):	
	def GetTableCaptions(self) -> list[str]:
		return ['Path']
	
	def GetTableCellValue(self, desc: BaseDescriptor, col: int) -> str | QTableWidgetItem:
		return str(desc.dirPath)