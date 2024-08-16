"""
copyright
"""

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.cinema4d'
PLUGIN_VERSION = '0.1.0'

import os, subprocess, re, json, sys, logging, cv2
import datetime as dt, numpy as np
from pathlib import Path
from functools import partial
from typing import Any, Iterator

from qavm.qavmapi import (
	BaseQualifier, BaseDescriptor, BaseTileBuilder, BaseSettings, BaseTableBuilder, BaseContextMenu
)
from qavm.qavmapi.gui import StaticBorderWidget, ClickableLabel, DateTimeTableWidgetItem
import qavm.qavmapi.utils as utils
from qavm.qavmapi.media_cache import MediaCache

from PyQt6.QtCore import Qt, QProcess, QSize, QRect, QPoint
from PyQt6.QtGui import QFont, QColor, QPixmap, QAction, QBrush, QPainter, QImage
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

C4D_CACHEDATA_FILEPATH: Path = utils.GetQAVMCachePath()/'c4d/index.json'

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
			('resource/build.txt', False, 0)
		]
		return ret
	
	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> list[str]:
		if 'resource/version.h' not in fileContents:
			return False
		versionContent: str = fileContents['resource/version.h']
		isVersionValid: bool = '#define C4D_V1' in versionContent \
							and '#define C4D_V2' in versionContent \
							and '#define C4D_V3' in versionContent \
							and '#define C4D_V4' in versionContent  # TODO: improve using regex
		return isVersionValid

class C4DDescriptor(BaseDescriptor):
	_c4dCacheData: dict | None = None  # TODO: thread safety???

	def __init__(self, dirPath: Path, settings: BaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__(dirPath, settings, fileContents)

		# From BaseDescriptor:
		# self.UID: str
		# self.dirPath: Path
		# self.settings: BaseSettings

		if C4DDescriptor._c4dCacheData is None:
			C4DDescriptor._loadC4DCacheData()

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

		self.prefsDirPath: Path = self._retrieveC4DPrefsDirPath()

		self.dirName: str = self.dirPath.name
		self.dirNameAdjusted: str = self._adjustDirname()

		buildTxtPath: Path = self.dirPath/'resource/build.txt'
		self.dateInstalled = buildTxtPath.stat().st_birthtime
		self.dateModified = buildTxtPath.stat().st_mtime

		self.commitRef = ''  # e.g. CL363640.28201 for R25, db1a05477b8f_1095604919 for 2024
		self.buildLink = ''  # the link where the build was downloaded from

		self.backendPluginVersion: str = ''  # version of the backend plugin
		self.pluginList: list = list()
		self.redshiftIsPresent: bool = False
		self.redshiftCoreVersion: str = ''
		self.redshiftPluginVersion: str = ''

		self._loadBackendPluginData()

		self.dateBuild = ''  # date when the build was created
	
	@staticmethod
	def _loadC4DCacheData():
		if not C4D_CACHEDATA_FILEPATH.exists():
			C4DDescriptor._c4dCacheData = dict()
			C4D_CACHEDATA_FILEPATH.parent.mkdir(parents=True, exist_ok=True)
			with open(C4D_CACHEDATA_FILEPATH, 'w') as f:
				json.dump(C4DDescriptor._c4dCacheData, f)
			return
		
		with open(C4D_CACHEDATA_FILEPATH, 'r') as f:
			C4DDescriptor._c4dCacheData = json.load(f)  # TODO: proper validation?
			if not isinstance(C4DDescriptor._c4dCacheData, dict):
				print('Invalid c4d cache data file!')
				C4DDescriptor._c4dCacheData = dict()
	
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
	
	def _retrieveC4DPrefsDirPath(self) -> Path:
		if C4DDescriptor._c4dCacheData is None:
			C4DDescriptor._loadC4DCacheData()

		def guessAndStoreInCacheC4dPrefsFolder():
			maxonPrefsDirPath: Path = utils.GetAppDataPath()/'Maxon'
			expectedPrefsDirNameLeftPart: str = f'{self.dirPath.name}_'
			candidates: list[Path] = [f for f in maxonPrefsDirPath.iterdir() if f.is_dir() and f.name.startswith(expectedPrefsDirNameLeftPart)]
			if not candidates:
				logger.error(f'Failed to find Cinema 4D prefs folder for {self.dirPath}')
				return maxonPrefsDirPath/expectedPrefsDirNameLeftPart
			c4dPrefsDirPath: Path = candidates[0]

			C4DDescriptor._c4dCacheData[self.UID] = {
				'prefsPath': str(c4dPrefsDirPath),
				'cacheLastChange': dt.datetime.now().isoformat()
			}
			with open(C4D_CACHEDATA_FILEPATH, 'w') as f:
				json.dump(C4DDescriptor._c4dCacheData, f)
			return c4dPrefsDirPath

		
		if self.UID not in C4DDescriptor._c4dCacheData:
			return guessAndStoreInCacheC4dPrefsFolder()
		
		c4dCacheData: dict = C4DDescriptor._c4dCacheData[self.UID]
		if 'prefsPath' not in c4dCacheData:
			return guessAndStoreInCacheC4dPrefsFolder()
		
		return Path(c4dCacheData['prefsPath'])


	def _loadBackendPluginData(self):
		if not self.prefsDirPath.exists():
			logger.error(f'Prefs folder not found: {self.prefsDirPath}')
			return
		
		backendDataFilePath: Path = self.prefsDirPath/'qavm_data.json'
		if not backendDataFilePath.exists():
			return
		
		backendData: dict = dict()
		with open(backendDataFilePath, 'r') as f:
			backendData = json.loads(f.read())  # TODO: do proper validation here
		
		if 'qavm_backend_plugin_version' not in backendData:
			return
		
		self.backendPluginVersion = backendData['qavm_backend_plugin_version']
		if 'plugins' in backendData:
			pluginsData: dict = backendData['plugins']
			self.pluginList = [k for k in pluginsData.keys()]
			
			if 'redshift' in pluginsData:
				self.redshiftIsPresent = True
				if redshiftData := pluginsData['redshift']:
					self.redshiftCoreVersion = redshiftData.get('core_version', '')
					self.redshiftPluginVersion = redshiftData.get('plugin_version', '')
	
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

		#############################################################
		############# This part should be precomputed ###############
		#############################################################
		def cv2ToQImage(cv_img):
			height, width, channel = cv_img.shape
			bytes_per_line = 3 * width
			# Convert BGR (OpenCV) to RGB (QImage)
			return QImage(cv_img.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
		
		SPLASH_SIZE: QSize = QSize(128, 72)
		splashImage: QImage = QImage(SPLASH_SIZE, QImage.Format.Format_RGBA8888)
		if (splashC4DImagePath := self._getC4DSplashPixmap(desc)):
			img = cv2.imread(str(splashC4DImagePath))
			contrast, brightness = 0.8, 40  # contrast (1.0 - 3.0), brightness (0 - 100)
			imgAdjusted = cv2.convertScaleAbs(img, alpha=contrast, beta=brightness)
			splashImage = cv2ToQImage(imgAdjusted)
		else:
			splashImage.fill(QColor(Qt.GlobalColor.transparent))
		splashPixmap = QPixmap.fromImage(splashImage).scaled(SPLASH_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
		#############################################################
		#############################################################
		#############################################################
		
		ICONC4D_SIZE: QSize = QSize(32, 32)
		iconC4D: Path | None = None
		if self.settings['extractIcons'][0]:
			iconC4D = utils.GetIconFromExecutable(desc.GetC4DExecutablePath())  # TODO: this has to be done on initialization, preferable in a separate thread
		if iconC4D is None:
			iconC4D: Path = Path('./res/icons/c4d-teal.png')
		iconPixmap: QPixmap = QPixmap(str(iconC4D)).scaled(ICONC4D_SIZE, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

		iconLabelC4D = ClickableLabel(parent)

		redshiftLogoPath: Path | None = None
		if desc.backendPluginVersion:
			if desc.redshiftIsPresent:
				redshiftLogoPath = Path(__file__).parent/'res/redshift-logo.png'
				if desc.redshiftPluginVersion and desc.redshiftCoreVersion:
					iconLabelC4D.setToolTip(f'Redshift plugin version: {desc.redshiftPluginVersion}\nRedshift core version: {desc.redshiftCoreVersion}')
		else:
			redshiftLogoPath = Path(__file__).parent/'res/redshift-logo-question.png'

		if splashPixmap:
			painter = QPainter(splashPixmap)
			painter.drawPixmap(QRect(QPoint(), ICONC4D_SIZE), iconPixmap)

			if redshiftLogoPath is not None:
				RSLOGO_SIZE: QSize = QSize(16, 16)
				rsPixmap: QPixmap = QPixmap(str(redshiftLogoPath))
				rsLogoRect: QRect = QRect(QPoint(), RSLOGO_SIZE)
				rsLogoRect.moveTopRight(QPoint(SPLASH_SIZE.width(), 0))
				painter.drawPixmap(rsLogoRect, rsPixmap)

			painter.end()

			iconLabelC4D.setPixmap(splashPixmap)
		
		iconLabelC4D.clicked.connect(partial(self._iconClicked, desc))
		iconLabelC4D.setFixedSize(SPLASH_SIZE)
		

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
		descLayout.addWidget(iconLabelC4D, alignment=Qt.AlignmentFlag.AlignCenter)

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

	def _getC4DSplashPixmap(self, desc: C4DDescriptor) -> Path | None:
		mediaCache: MediaCache = MediaCache()
		
		mediaUID: str = f'{str(desc.GetC4DExecutablePath())}_splash-image-frame.png'
		if cachedPath := mediaCache.GetCachedPath(mediaUID):
			return cachedPath
		
		splashVideoPath: Path = desc.dirPath/'resource/modules/gui.module/images/splash.mp4'
		if not splashVideoPath.exists():
			return None
		splashFramePath: Path = self._extractVideoFrame(splashVideoPath, -1)
		if splashFramePath is None or not splashFramePath.exists():
			return None
		mediaCache.CacheMedia(mediaUID, splashFramePath)
		return splashFramePath
	
	def _extractVideoFrame(self, videoPath: Path, frameNum: int) -> Path | None:
		# Extracting video frame: https://stackoverflow.com/questions/33311153/python-extracting-and-saving-video-frames
		import cv2
		vidcap = cv2.VideoCapture(videoPath)
		if not vidcap.isOpened():
			return None
		
		frameCount: int = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
		vidcap.set(cv2.CAP_PROP_POS_FRAMES, frameCount - 2)
		success, image = vidcap.read()
		if not success:
			return None
		
		tempDirPath: Path = utils.GetQAVMTempPath()
		tempDirPath.mkdir(parents=True, exist_ok=True)
		tempPath: Path = tempDirPath/f'{utils.GetHashString(str(videoPath))}.jpg'

		cv2.imwrite(tempPath, image)
		
		return tempPath

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
		menu.addAction('Open prefs folder', partial(utils.OpenFolderInExplorer, desc.prefsDirPath))
		return menu
	
	def _run(self, desc: C4DDescriptor):
		self._runC4DExecutable(desc)
	def _runConsole(self, desc: C4DDescriptor):
		self._runC4DExecutable(desc, extraArgs='g_console=true')
	
	def _runC4DExecutable(self, desc: C4DDescriptor, extraArgs: str = ''):
		backendPluginPathStr: str = 'D:\\prj\\qavm\\source\\plugins\\cinema4d\\c4d-plugin'
		args: str = f'g_additionalModulePath="{backendPluginPathStr}" ' \
					f'qavm_c4dUID="{desc.UID}" ' \
					f'qavm_c4dCacheDataPath="{C4D_CACHEDATA_FILEPATH}" '
		os.startfile(str(desc.GetC4DExecutablePath()), arguments=args + ' ' + extraArgs)

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
