import os, subprocess
from pathlib import Path
from functools import partial

from qavm.qavmapi import BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings
from qavm.qavmapi.gui import StaticBorderWidget, ClickableLabel
import qavm.qavmapi.utils as utils

from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QFont, QColor, QPixmap
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMessageBox

"""
QAVM can be extended by plugins. Each plugin is represented by a folder with a python script that has the same name as the folder.

Each plugin can implement multiple modules. Modules can be of different types, e.g. software, settings, etc.
"""

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.cinema4d'
PLUGIN_VERSION = '0.1.0'

class C4DQualifier(BaseQualifier):
	def ProcessSearchPaths(self, searchPaths: list[str]) -> list[str]:
		return searchPaths
	
	def GetIdentificationConfig(self) -> dict:
		ret = dict()
		ret['requiredFileList'] = [
			'resource/version.h',
			'resource/build.txt',
		]
		if utils.PlatformWindows():
			ret['requiredFileList'] = [
				'c4dpy.exe',
				'Cinema 4D.exe',
				'cineware.dll',
			]

		ret['requiredDirList'] = [
			'corelibs',
			'resource',
		]
		if utils.PlatformMacOS():
			ret['requiredDirList'].append('Cinema 4D.app')
			ret['requiredDirList'].append('c4dpy.app')
			ret['requiredDirList'].append('cineware.bundle')

		ret['negativeFileList'] = []
		ret['negativeDirList'] = []

		ret['fileContentsList'] = [  # list of tuples: (filename, isBinary, lengthLimit)
			('resource/version.h', False, 0),
			('resource/build.txt', False, 0),
			('plugincache.txt', False, 0),  # TODO: this is created by a backend plugin
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

		# From BaseDescriptor:
		# self.dirPath: Path

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

	def GetC4DExecutablePath(self) -> Path | None:
		if utils.PlatformWindows():
			if (c4d := self.dirPath/'Cinema 4D.exe').exists():
				return c4d
		elif utils.PlatformMacOS():
			if (c4d := self.dirPath/'Cinema 4D.app').exists():
				return c4d
		QMessageBox.warning(None, 'C4D Descriptor', 'Cinema 4D executable not found!')
		return None
	
	def __str__(self):
		return f'C4D: {os.path.basename(self.dirPath)}'
	
	def __repr__(self):
		return self.__str__()

class C4DTileBuilderDefault(BaseTileBuilder):
	def CreateTileWidget(self, descriptor: C4DDescriptor, parent) -> QWidget:
		descWidget: QWidget = self._createDescWidget(descriptor, parent)
		# return descWidget
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

		pixMap = None
		if desc.GetC4DExecutablePath().exists():
			imgBytes: bytes = utils.GetIconFromExecutable(desc.GetC4DExecutablePath())
			if imgBytes:
				pixMap = QPixmap()
				pixMap.loadFromData(imgBytes)
		if not pixMap:
			pixMap: QPixmap = QPixmap('./res/icons/c4d-teal.png')

		iconLabel = ClickableLabel(parent)
		iconLabel.setScaledContents(True)
		iconLabel.setPixmap(pixMap)
		iconLabel.setFixedSize(64, 64)
		iconLabel.clicked.connect(partial(self._iconClicked, desc))

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

	def _iconClicked(self, desc: C4DDescriptor):
		os.startfile(str(desc.GetC4DExecutablePath()), arguments='g_console=true')

class C4DSettings(BaseSettings):
	def CreateWidget(self, parent) -> QWidget:
		return QLabel('C4D Settings', parent)




##############################################################################################
##################### TESTING THINGS #########################################################
##############################################################################################
class C4DExampleQualifier(BaseQualifier):
	pass
class C4DExampleDescriptor(BaseDescriptor):
	pass
class C4DExampleTileBuilder(BaseTileBuilder):
	pass

class MyExampleSettings(BaseSettings):
	def __init__(self) -> None:
		super().__init__()
	def CreateWidget(self, parent):
		return None
##############################################################################################
##################### TESTING THINGS #########################################################
##############################################################################################




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



		{
			'id': 'software.example',  # this is a unique id under the PLUGIN_ID domain
			'name': 'C4D - Example',
			# 'description': 'Cinema 4D software module for QAVM',
			# 'author': 'wi1k1n',
			# 'author_email': 'vfpkjd@gmail.com',

			'qualifier': C4DExampleQualifier,
			'descriptor': C4DExampleDescriptor,
			'tile_builders': {
				'': C4DExampleTileBuilder,
			},
		}
	]

def RegisterModuleSettings():
	return [
		{
			'id': 'settings.example',  # this is a unique id under the PLUGIN_ID domain
			'name': 'My Example Settings',
			'settings': MyExampleSettings,
		},
	]
