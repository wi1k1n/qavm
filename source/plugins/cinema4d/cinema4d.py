import os
from pathlib import Path
from qavmapi import BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings
from qavmapi.gui import StaticBorderWidget

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPixmap
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

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
			'resource/version.h',
			'sdk.zip',
		]
		ret['requiredDirList'] = [
			'corelibs',
			'resource',
		]
		ret['negativeFileList'] = []
		ret['negativeDirList'] = []

		ret['fileContentsList'] = [  # list of tuples: (filename, isBinary, lengthLimit)
			('resource/version.h', False, 0),
			('resource/build.txt', False, 0),
			('plugincache.txt', False, 0),
		]
		return ret
	
	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> list[str]:
		if 'resource/version.h' not in fileContents:
			return False
		versionContent: str = fileContents['resource/version.h']
		return '#define C4D_V1' in versionContent \
			and '#define C4D_V2' in versionContent \
			and '#define C4D_V3' in versionContent \
			and '#define C4D_V4' in versionContent  # TODO: improve using regex

class C4DDescriptor(BaseDescriptor):
	def __init__(self, dirPath: Path, fileContents: dict[str, str | bytes]):
		super().__init__(dirPath, fileContents)

		self.buildString = ''  # from the build.txt
		if 'resource/build.txt' in fileContents:
			self.buildString = fileContents['resource/build.txt']
		
		self.majorVersion = 'R2024'  # R25 or 2024
		self.subversion = '4.1'  # e.g. 106 for R26, 4.1 for 2024

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

class C4DTileBuilderDefault(BaseTileBuilder):
	def CreateTileWidget(self, descriptor: C4DDescriptor, parent) -> QWidget:
		descWidget = self._createDescWidget(descriptor, parent)
		animatedBorderWidget = self._wrapWidgetInAnimatedBorder(descWidget, QColor(Qt.GlobalColor.darkGreen), parent)
		return animatedBorderWidget
	
	def _createDescWidget(self, desc: C4DDescriptor, parent: QWidget):
		descWidget = QWidget(parent)

		parentBGColor = parent.palette().color(parent.backgroundRole())
		descWidget.setStyleSheet(f"background-color: {parentBGColor.name()};")
		# DEBUG # descWidget.setStyleSheet("background-color: rgb(200, 200, 255);")
		
		descLayout = QVBoxLayout(descWidget)
		descLayout.setContentsMargins(0, 0, 0, 0)
		descLayout.setSpacing(0)

		iconLabel = QLabel(parent)
		iconLabel.setScaledContents(True)
		pixMap: QPixmap = QPixmap('./res/icons/c4d-teal.png')
		iconLabel.setPixmap(pixMap)
		iconLabel.setFixedSize(64, 64)

		def createQLabel(text) -> QLabel:
			label = QLabel(text, parent)
			label.setFont(QFont('SblHebrew', 10))
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			# DEBUG # label.setStyleSheet("background-color: pink;")
			return label
		
		descLayout.addWidget(createQLabel(desc.buildString))
		# descLayout.addWidget(createQLabel(f'{desc.majorVersion} {desc.subversion}'))
		descLayout.addWidget(iconLabel, alignment=Qt.AlignmentFlag.AlignCenter)
		descLayout.addWidget(createQLabel(desc.dirPath.name))

		descWidget.setFixedSize(descWidget.minimumSizeHint())

		return descWidget
	
	def _wrapWidgetInAnimatedBorder(self, widget, accentColor: QColor, parent):
		tailColor = QColor(accentColor)
		tailColor.setAlpha(30)
		
		animBorderWidget = StaticBorderWidget(accentColor)
		animBorderLayout = animBorderWidget.layout()
		borderThickness = 5
		animBorderLayout.setContentsMargins(borderThickness, borderThickness, borderThickness, borderThickness)
		animBorderLayout.addWidget(widget)
		animBorderWidget.setFixedSize(animBorderWidget.minimumSizeHint())
		return animBorderWidget

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
			'tile_builders': {  # context: TileBuilder
				'': C4DTileBuilderDefault,  # default tile builder
			},
			'settings': C4DSettings,
		},



		# {
		# 	'id': 'software.example',  # this is a unique id under the PLUGIN_ID domain
		# 	'name': 'C4D - Example',
		# 	# 'description': 'Cinema 4D software module for QAVM',
		# 	# 'author': 'wi1k1n',
		# 	# 'author_email': 'vfpkjd@gmail.com',

		# 	'qualifier': C4DExampleQualifier,
		# 	'descriptor': C4DExampleDescriptor,
		# 	'tile_builders': {
		# 		'': C4DExampleTileBuilder,
		# 	},
		# }
	]
