##############################################################################
########################### QAVM Plugin: Software ############################
##############################################################################

class BaseSettings(object):
	pass

##############################################################################
########################### QAVM Plugin: Software ############################
##############################################################################

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
			'requiredFileList': [],
			'negativeFileList': [],
			'fileContentsList': [],
		}

	def Identify(self, currentPath: str, fileContents: dict[str, str | bytes]) -> list[str]:
		return True

class BaseDescriptor(object):
	def __init__(self, dirPath: str, fileContents: dict[str, str | bytes]):
		pass

	def __str__(self):
		return 'BaseDescriptor'
	
	def __repr__(self):
		return self.__str__()

class BaseTileBuilder(object):
	def __init__(self):
		pass

