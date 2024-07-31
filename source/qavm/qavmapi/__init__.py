from pathlib import Path

from PyQt6.QtWidgets import QWidget, QLabel

##############################################################################
#############################  ##############################
##############################################################################

class BaseSettings(object):
	def Load(self):
		pass
	def Save(self):
		pass
	def CreateWidget(self, parent):
		pass

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
	def __init__(self, dirPath: Path, fileContents: dict[str, str | bytes]):
		self.dirPath: Path = dirPath

	def __str__(self):
		return 'BaseDescriptor'
	
	def __repr__(self):
		return self.__str__()

class BaseTileBuilder(object):
	def __init__(self):
		pass

	def CreateTileWidget(self, descriptor: BaseDescriptor, parent) -> QWidget:
		return QLabel(str(descriptor.dirPath), parent)