"""
copyright
"""

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.cinema4d'
PLUGIN_VERSION = '0.1.0'

import os, subprocess, re, json, sys, logging
import datetime as dt
from pathlib import Path
from functools import partial
from typing import Any, Iterator

from qavm.qavmapi import BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings
from qavm.qavmapi.gui import StaticBorderWidget, ClickableLabel
import qavm.qavmapi.utils as utils

from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QFont, QColor, QPixmap
from PyQt6.QtWidgets import (
	QWidget, QLabel, QVBoxLayout, QMessageBox, QFormLayout, QLineEdit, QCheckBox
)

"""
QAVM can be extended by plugins. Each plugin is represented by a folder with a python script that has the same name as the folder.

Each plugin can implement multiple modules. Modules can be of different types, e.g. software, settings, etc.
"""

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

LOGS_PATH = utils.GetQAVMDataPath()/'qavm-c4d.log'
loggerFileHandler = logging.FileHandler(LOGS_PATH)
loggerFileHandler.setLevel(logging.ERROR)
loggerFileHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(loggerFileHandler)


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
	def __init__(self, dirPath: Path, settings: BaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__(dirPath, settings, fileContents)

		# From BaseDescriptor:
		# self.dirPath: Path
		# self.settings: BaseSettings

		self.buildString = ''  # from the build.txt
		if 'resource/build.txt' in fileContents:
			self.buildString = fileContents['resource/build.txt']
		
		self.versionH: list[int] = [0, 0, 0, 0]  # from the version.h
		if 'resource/version.h' in fileContents:
			self.versionH = C4DDescriptor._parseVersionH(fileContents['resource/version.h'])
		
		self.majorVersion: str  # R25 or 2024
		self.subversion = ''  # e.g. 106 for R26, 4.1 for 2024
		OLDNAMING: bool = self.versionH[0] <= 26
		self.majorVersion: str = '{}{}'.format('R' if OLDNAMING else '', self.versionH[0])  # TODO: R or S?
		self.subversion: str = ('' if OLDNAMING else '.').join(map(str, self.versionH[1:4] if OLDNAMING else self.versionH[1:3]))

		self.dirName: str = self.dirPath.name
		if self.settings['adjustFolderName']:
			self.dirName = self._adjustDirname()

		buildTxtPath: Path = self.dirPath/'resource/build.txt'
		self.dateInstalled = buildTxtPath.stat().st_birthtime
		self.dateModified = buildTxtPath.stat().st_mtime

		self.commitRef = ''  # e.g. CL363640.28201 for R25, db1a05477b8f_1095604919 for 2024
		self.buildLink = ''

		self.pluginList = list()
		self.redshiftVersion = ''
		self.redshiftPluginVersion = ''

		self.dateBuild = ''  # date when the build was created
	
	@staticmethod
	def _parseVersionH(versionHContent: str) -> list[int]:
		def _safeCast(val, to_type, default=None):
			try: return to_type(val)
			except: return default
		
		C4V_VERSION_PART_PREFIX: str = '#define C4D_V'
		versionPartsArr: list[int] = [0, 0, 0, 0]
		lines: list[str] = versionHContent.splitlines()
		for line in lines:
			for i in range(4):
				curDefinePart: str = f'{C4V_VERSION_PART_PREFIX}{i + 1}'
				if line.startswith(curDefinePart):
					versionPartsArr[i] = _safeCast(line[len(curDefinePart):].strip(), int, -1)
					break
		return versionPartsArr
	
	def _adjustDirname(self) -> str:
		RAWFOLDERNAME_MAXLEN = 64
		folderName: str = self.dirPath.name
		
		if folderName.lower().startswith('maxon'): # customer installation
			return folderName
		
		commitHashPattern = re.compile('#[a-zA-Z0-9]{12}')
		if match := commitHashPattern.search(folderName): # it's a new notation with 12 symbol commit hash
			if folderName.startswith('C4D'): # it's installation
				tokens: list[str] = folderName.split(' ')
				if len(tokens) < 5: return folderName[RAWFOLDERNAME_MAXLEN]
				return f'{tokens[1]} {tokens[4][:9]}' # branch + commit hash
			# it's a package
			tokens: list[str] = folderName.split('_')
			if len(tokens) < 2: return folderName[RAWFOLDERNAME_MAXLEN]
			return f'{tokens[0]} {match.group()[:9]}'
		
		# it's an old notation with CL
		if folderName.startswith('C4D'): # it's installation
			tokens: list[str] = folderName.split(' ')
			if len(tokens) < 4: return folderName[RAWFOLDERNAME_MAXLEN]
			return f'{tokens[1]} CL{tokens[-1]}'
		
		# it's a package
		changeListPattern = re.compile('CL\\d{6}')
		if match := changeListPattern.search(folderName): # found CL###### token
			pos, _ = match.span()
			tokens: list[str] = [x for x in folderName[:pos].split('.') if x]
			if len(tokens) < 3: return folderName[RAWFOLDERNAME_MAXLEN]
			versionTokensNum = 2 # old R notation, e.g. 26.001
			if len(tokens[0]) == 4: # it's 202X notation
				if len(tokens) == 3: # it's 2023.000.branch naming scheme
					versionTokensNum = 2
				else: # it's 2023.0.0.branch naming scheme
					versionTokensNum = 3
			tokens = [''.join(tokens[:versionTokensNum]), '.'.join(tokens[versionTokensNum:])]
			return f'{tokens[1]} {match.group()}'
		return folderName[RAWFOLDERNAME_MAXLEN]

	def GetC4DExecutablePath(self) -> Path | None:
		if utils.PlatformWindows():
			if (c4d := self.dirPath/'Cinema 4D.exe').exists():
				return c4d
		elif utils.PlatformMacOS():
			if (c4d := self.dirPath/'Cinema 4D.app').exists():
				return c4d
		QMessageBox.warning(None, 'C4D Descriptor', 'Cinema 4D executable not found!')
		return None
	
	def __hash__(self) -> int:
		return super().__hash__() # TODO: should this be robust to dirPath (e.g. when c4d package is moved to another location)?
	
	def __str__(self):
		return f'C4D: {os.path.basename(self.dirPath)}'
	
	def __repr__(self):
		return self.__str__()

class C4DTileBuilderDefault(BaseTileBuilder):
	def __init__(self, settings: BaseSettings):
		super().__init__(settings)
		# From BaseTileBuilder:
		# self.settings: BaseSettings

	def CreateTileWidget(self, descriptor: C4DDescriptor, parent) -> QWidget:
		descWidget: QWidget = self._createDescWidget(descriptor, parent)
		# return descWidget
		animatedBorderWidget = self._wrapWidgetInAnimatedBorder(descWidget, QColor(Qt.GlobalColor.darkGreen), parent)
		return animatedBorderWidget
	
	def _createDescWidget(self, desc: C4DDescriptor, parent: QWidget):
		descWidget = QWidget(parent)

		parentBGColor = parent.palette().color(parent.backgroundRole())
		descWidget.setStyleSheet(f"background-color: {parentBGColor.name()};")
		# descWidget.setStyleSheet("background-color: rgb(200, 200, 255);") # DEBUG
		descWidget.setStyleSheet("background-color: rgb(50, 50, 50);") # DEBUG
		
		descLayout = QVBoxLayout(descWidget)
		margins: int = 5
		descLayout.setContentsMargins(margins, margins, margins, margins)
		descLayout.setSpacing(5)

		iconPath: Path | None = utils.GetIconFromExecutable(desc.GetC4DExecutablePath())
		if iconPath is None:
			iconPath: Path = Path('./res/icons/c4d-teal.png')
		pixMap: QPixmap = QPixmap(str(iconPath))

		iconLabel = ClickableLabel(parent)
		iconLabel.setScaledContents(True)
		iconLabel.setPixmap(pixMap)
		iconLabel.setFixedSize(64, 64)
		iconLabel.clicked.connect(partial(self._iconClicked, desc))

		def createQLabel(text, tooltip: str = '') -> QLabel:
			label = QLabel(text, parent)
			label.setFont(QFont('SblHebrew'))
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			label.setToolTip(tooltip)
			# DEBUG # label.setStyleSheet("background-color: pink;")
			return label
		def timestampToStr(timestamp: int, frmt: str = '%d-%b-%y %H:%M:%S') -> str:
			return dt.datetime.fromtimestamp(timestamp).strftime(frmt)
		
		descLayout.addWidget(createQLabel(f'{desc.majorVersion}.{desc.subversion}', f'Build {desc.buildString}'))
		descLayout.addWidget(createQLabel(desc.dirName, str(desc.dirPath)))
		descLayout.addWidget(createQLabel(f'Installed: {timestampToStr(desc.dateInstalled, "%d-%b-%y")}',
										f'Installed: {timestampToStr(desc.dateInstalled)}'
										f'\nModified: {timestampToStr(desc.dateModified)}'))
		descLayout.addWidget(iconLabel, alignment=Qt.AlignmentFlag.AlignCenter)

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

""" Helper wrapper class for C4D settings entries """
class C4DSettingsContainer:
	SETTINGS_ENTRIES: dict[str, list] = {  # key: [defaultValue, text, tooltip]
		'adjustFolderName': 	[True, 'Adjust folder name', 'Replace folder name with human-readable one'],
		'runWithConsole': 		[False, 'Run with console', 'Run Cinema 4D with console enabled'],
	}

	def __init__(self):
		super().__init__()
		for key, default in self.SETTINGS_ENTRIES.items():
			setattr(self, key, default)
	def DumpToString(self) -> str:
		data: dict = dict()
		for key in self.SETTINGS_ENTRIES.keys():
			data[key] = getattr(self, key)
		return json.dumps(data)
	def InitializeFromString(self, dataStr: str) -> bool:
		try:
			data: dict = json.loads(dataStr)
			for key in self.SETTINGS_ENTRIES.keys():
				if key not in data: return False
				if type(data[key]) != type(getattr(self, key)):
					logger.error(f'Incompatible preferences data type for #{key}!')
					return False
				setattr(self, key, data[key])
			return True
		except Exception as e:
			logger.exception(f'Failed to parse settings data: {e}')
			return False
	
	def __iter__(self) -> Iterator[str]:
		for key in C4DSettingsContainer.SETTINGS_ENTRIES.keys():
			yield key

class C4DSettings(BaseSettings):
	def __init__(self) -> None:
		super().__init__()
		self.container = C4DSettingsContainer()

		self.prefFilePath: Path = utils.GetPrefsFolderPath()/'c4d-preferences.json'
		if not self.prefFilePath.exists():
			logger.info(f'C4D settings file not found, creating a new one. Path: {self.prefFilePath}')
			self.Save()
	
	def __getitem__(self, key: str) -> Any:
		return getattr(self.container, key, None)

	def Load(self):
		with open(self.prefFilePath, 'r') as f:
			if not self.container.InitializeFromString(f.read()):
				logger.error('Failed to load C4D settings')

	def Save(self):
		if not self.prefFilePath.parent.exists():
			logger.info(f"C4D preferences folder doesn't exist. Creating: {self.prefFilePath.parent}")
			self.prefFilePath.parent.mkdir(parents=True, exist_ok=True)
		with open(self.prefFilePath, 'w') as f:
			f.write(self.container.DumpToString())

	def CreateWidget(self, parent: QWidget) -> QWidget:
		settingsWidget: QWidget = QWidget(parent)
		formLayout: QFormLayout = QFormLayout(settingsWidget)

		# TODO: refactor this
		def addRowTyped(text: str, value: Any, tooltip: str = ''):
			textLabel = QLabel(text)
			textLabel.setToolTip(tooltip)
			if isinstance(value, bool):
				checkbox = QCheckBox()
				checkbox.setChecked(value)
				formLayout.addRow(textLabel, checkbox)
				return checkbox
			if isinstance(value, str):
				lineEdit = QLineEdit(value)
				formLayout.addRow(textLabel, lineEdit)
				return lineEdit
			return None

		for key in self.container:
			val: list = getattr(self.container, key)
			if addRowTyped(val[1], val[0], val[2]) is None:
				logger.info(f'Unknown value type for key: {key}')

		# formLayout.addRow('Adjust folder name', QCheckBox())

		return settingsWidget




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
