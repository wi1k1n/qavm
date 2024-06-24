import os
from qavmapi import BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.cinema4d'
PLUGIN_VERSION = '0.1.0'

class C4DQualifier(BaseQualifier):
	def ProcessSearchPaths(self, searchPaths: list[str]) -> list[str]:
		return searchPaths
	
	def GetIdentificationConfig(self) -> dict:
		ret = dict()
		ret['requiredFileList'] = [
			'c4dpy.exe',
			'Cinema 4D.exe',
			'cineware.dll',
			'sdk.zip'
		]
		ret['negativeFileList'] = []
		ret['fileContentsList'] = []
		return ret
	
	def Identify(self, currentPath: str, fileContents: dict[str, str | bytes]) -> list[str]:
		return True

class C4DDescriptor(BaseDescriptor):
	def __init__(self, dirPath: str, fileContents: dict[str, str | bytes]):
		self.dirPath = dirPath

		self.buildString = ''  # from the build.txt
		self.majorVersion = ''  # R25 or 2024
		self.subversion = ''  # e.g. 106 for R26, 4.1 for 2024
		self.commitRef = ''  # e.g. CL363640.28201 for R25, db1a05477b8f_1095604919 for 2024
		self.buildLink = ''

		self.pluginList = list()
		self.redshiftVersion = ''
		self.redshiftPluginVersion = ''

		self.dateInstalled = ''
		self.dateBuild = ''  # date when the build was created

	def __str__(self):
		return f'C4D: {os.path.basename(self.dirPath)}'
	def __repr__(self):
		return self.__str__()

class C4DTileBuilder(BaseTileBuilder):
	pass

class C4DSettings(BaseSettings):
	pass




class C4DExampleQualifier(BaseQualifier):
	pass
class C4DExampleDescriptor(BaseDescriptor):
	pass
class C4DExampleTileBuilder(BaseTileBuilder):
	pass




def RegisterModuleSoftware():
	return [
		{
			'id': 'software',  # this is a unique id under the PLUGIN_ID domain
			'name': 'Cinema 4D',
			# 'description': 'Cinema 4D software module for QAVM',
			# 'author': 'wi1k1n',
			# 'author_email': 'vfpkjd@gmail.com',

			'qualifier': C4DQualifier,
			'descriptor': C4DDescriptor,
			'tile_builder': C4DTileBuilder,
			'settings': C4DSettings,
		},



		{
			'id': 'software.example',  # this is a unique id under the PLUGIN_ID domain
			'name': 'C4D - Example',
			# 'description': 'Cinema 4D software module for QAVM',
			# 'author': 'wi1k1n',
			# 'author_email': 'vfpkjd@gmail.com',

			'qualifier': C4DExampleQualifier,
			'descriptor': C4DExampleDescriptor,
			'tile_builder': C4DExampleTileBuilder,
		}
	]
