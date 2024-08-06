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

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings, BaseTableBuilder, BaseContextMenu
)
from qavm.qavmapi.gui import StaticBorderWidget, ClickableLabel, DateTimeTableWidgetItem
import qavm.qavmapi.utils as utils

from PyQt6.QtCore import Qt, QProcess
from PyQt6.QtGui import QFont, QColor, QPixmap, QAction
from PyQt6.QtWidgets import (
	QWidget, QLabel, QVBoxLayout, QMessageBox, QFormLayout, QLineEdit, QCheckBox, QTableWidgetItem,
	QMenu, QWidgetAction
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
		self.dirNameAdjusted: str = self._adjustDirname()

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
	def __init__(self, settings: BaseSettings, contextMenu: BaseContextMenu):
		super().__init__(settings, contextMenu)
		# From BaseTileBuilder:
		# self.settings: BaseSettings
		# self.contextMenu: BaseContextMenu

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
		
		iconPath: Path | None = None
		if self.settings['extractIcons'][0]:
			iconPath = utils.GetIconFromExecutable(desc.GetC4DExecutablePath())
		if iconPath is None:
			iconPath: Path = Path('./res/icons/c4d-teal.png')
		pixMap: QPixmap = QPixmap(str(iconPath))

		iconLabel = ClickableLabel(parent)
		iconLabel.setScaledContents(True)
		iconLabel.setPixmap(pixMap)
		iconLabel.setFixedSize(64, 64)
		iconLabel.clicked.connect(partial(self._iconClicked, desc))

		def createQLabel(text) -> QLabel:
			label = QLabel(text, parent)
			label.setFont(QFont('SblHebrew'))
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			# DEBUG # label.setStyleSheet("background-color: pink;")
			return label
			
		def timestampToStr(timestamp: int, frmt: str = '%d-%b-%y %H:%M:%S') -> str:
			return dt.datetime.fromtimestamp(timestamp).strftime(frmt)
		
		descLayout.addWidget(createQLabel(f'{desc.majorVersion}.{desc.subversion}'))
		dirNameLabel: str = desc.dirNameAdjusted if self.settings['adjustFolderName'][0] else desc.dirName
		descLayout.addWidget(createQLabel(dirNameLabel))
		descLayout.addWidget(createQLabel(f'Installed: {timestampToStr(desc.dateInstalled, "%d-%b-%y")}'))
		descLayout.addWidget(iconLabel, alignment=Qt.AlignmentFlag.AlignCenter)

		toolTip: str = f'Build {desc.buildString}' \
					+ '\n' + str(desc.dirPath) \
					+ f'\nInstalled: {timestampToStr(desc.dateInstalled)}' \
					f'\nModified: {timestampToStr(desc.dateModified)}'
		descWidget.setToolTip(toolTip)

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
		args: str = 'g_console=true' if self.settings['runWithConsole'][0] else ''
		os.startfile(str(desc.GetC4DExecutablePath()), arguments=args)


class C4DVersionTableWidgetItem(QTableWidgetItem):
	def __init__(self, versionH: list[int], verionStr: str):
		if len(versionH) != 4:
			raise ValueError('Invalid versionH length')
		self.versionH: list[int] = versionH
		self.versionStr: str = verionStr
		super().__init__(verionStr)

	def __lt__(self, other):
		if isinstance(other, C4DVersionTableWidgetItem):
			def convoluteVersion(v):
				return v[0] * 1000 + v[1] * 100 + v[2] * 10 + v[3]
			return convoluteVersion(self.versionH) < convoluteVersion(other.versionH)
		return super().__lt__(other)

class C4DTableBuilder(BaseTableBuilder):
	def GetTableCaptions(self) -> list[str]:
		return ['Folder name', 'Version', 'Installed date', 'Path']
	
	def GetTableCellValue(self, desc: C4DDescriptor, col: int) -> str | QTableWidgetItem:
		if col == 0:
			return desc.dirNameAdjusted if self.settings['adjustFolderName'][0] else desc.dirName
		if col == 1:
			return C4DVersionTableWidgetItem(desc.versionH, f'{desc.majorVersion}.{desc.subversion}')
		if col == 2:
			return DateTimeTableWidgetItem(dt.datetime.fromtimestamp(desc.dateInstalled), '%d-%b-%y %H:%M:%S')
		if col == 3:
			return str(desc.dirPath)
		return ''

class C4DSettings(BaseSettings):
	def __init__(self) -> None:
		super().__init__()

		self.settings: dict[str, list] = {  # key: (defaultValue, text, tooltip, isTileUpdateRequired)
			'adjustFolderName': 	[True, 'Adjust folder name', 'Replace folder name with human-readable one', True],
			'runWithConsole': 		[False, 'Run with console', 'Run Cinema 4D with console enabled', False],
			'extractIcons': 		[True, 'Extract icons', 'Use actual icons extracted from Cinema 4D executables', True],
		}

		self.prefFilePath: Path = utils.GetPrefsFolderPath()/'c4d-preferences.json'
		if not self.prefFilePath.exists():
			logger.info(f'C4D settings file not found, creating a new one. Path: {self.prefFilePath}')
			self.Save()
	
	def __getitem__(self, key: str) -> Any:
		return self.settings.get(key, None)
	
	def GetName(self) -> str:
		return 'Cinema 4D'

	def Load(self):
		with open(self.prefFilePath, 'r') as f:
			try:
				data: dict = json.loads(f.read())
				for key in self.settings.keys():
					if key not in data:
						return logger.error(f'Missing key in preferences data: {key}')
					if type(data[key]) != type(self.settings[key][0]):
						logger.error(f'Incompatible preferences data type for #{key}!')
						return False
					self.settings[key][0] = data[key]
			except Exception as e:
				logger.exception(f'Failed to parse settings data: {e}')

	def Save(self):
		if not self.prefFilePath.parent.exists():
			logger.info(f"C4D preferences folder doesn't exist. Creating: {self.prefFilePath.parent}")
			self.prefFilePath.parent.mkdir(parents=True, exist_ok=True)
		with open(self.prefFilePath, 'w') as f:
			data: dict[str, Any] = {key: val[0] for key, val in self.settings.items()}
			f.write(json.dumps(data))

	def CreateWidget(self, parent: QWidget) -> QWidget:
		settingsWidget: QWidget = QWidget(parent)
		formLayout: QFormLayout = QFormLayout(settingsWidget)

		# TODO: refactor this
		def addRowTyped(key: str):
			settingsEntry: list = self.settings[key]
			text: str = settingsEntry[1]
			value: Any = settingsEntry[0]
			tooltip: str = settingsEntry[2]
			isTileUpdateRequired: bool = settingsEntry[3]

			textLabel = QLabel(text)
			textLabel.setToolTip(tooltip)
			if isinstance(value, bool):
				checkbox = QCheckBox()
				checkbox.setChecked(value)
				checkbox.checkStateChanged.connect(partial(self._settingChangedCheckbox, settingsEntry=settingsEntry))
				formLayout.addRow(textLabel, checkbox)
				return checkbox
			if isinstance(value, str):
				lineEdit = QLineEdit(value)
				lineEdit.textChanged.connect(partial(self._settingsChangedLineEdit, settingsEntry=settingsEntry))
				formLayout.addRow(textLabel, lineEdit)
				return lineEdit
			return None

		for key in self.settings.keys():
			if addRowTyped(key) is None:
				logger.info(f'Unknown value type for key: {key}')

		# formLayout.addRow('Adjust folder name', QCheckBox())

		return settingsWidget

	def _settingChangedCheckbox(self, state, settingsEntry: list):
		settingsEntry[0] = state == Qt.CheckState.Checked
		if settingsEntry[3]:
			self.tilesUpdateRequired.emit()

	def _settingsChangedLineEdit(self, text, settingsEntry: list):
		settingsEntry[0] = text
		if settingsEntry[3]:
			self.tilesUpdateRequired.emit()

class C4DContextMenu(BaseContextMenu):
	def CreateMenu(self, desc: C4DDescriptor) -> QMenu:
		menu = QMenu()

		titleLabel: QLabel = QLabel(f'{desc.majorVersion}.{desc.subversion}')
		titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
		titleLabel.setContentsMargins(0, 7, 0, 3)
		titleAction: QWidgetAction = QWidgetAction(menu)
		titleAction.setDefaultWidget(titleLabel)

		menu.addAction(titleAction)
		menu.addAction('Run', partial(self._run, desc))
		menu.addAction('Run w/console', partial(self._runConsole, desc))
		menu.addSeparator()
		menu.addAction('Open folder', partial(utils.OpenFolderInExplorer, desc.dirPath))
		return menu
	
	def _run(self, desc: C4DDescriptor):
		os.startfile(str(desc.GetC4DExecutablePath()))
	def _runConsole(self, desc: C4DDescriptor):
		os.startfile(str(desc.GetC4DExecutablePath()), arguments='g_console=true')

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
		return QWidget(parent)
	
	def GetName(self) -> str:
		return 'Example Settings'
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
			'settings': C4DSettings,
			'tile_view': {
				'tile_builder': C4DTileBuilderDefault,
				'context_menu': C4DContextMenu,
			},
			'table_view': {
				'table_builder': C4DTableBuilder,
				'context_menu': C4DContextMenu,
			},
		},



		{
			'id': 'software.example',  # this is a unique id under the PLUGIN_ID domain
			'name': 'C4D - Example',
			# 'description': 'Cinema 4D software module for QAVM',
			# 'author': 'wi1k1n',
			# 'author_email': 'vfpkjd@gmail.com',

			'qualifier': C4DExampleQualifier,
			'descriptor': C4DExampleDescriptor,
			'tile_view': {
				'tile_builder': C4DExampleTileBuilder,
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
