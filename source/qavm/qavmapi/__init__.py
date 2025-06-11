from pathlib import Path
from typing import Any
from functools import partial
import json

from PyQt6.QtCore import (
	pyqtSignal, QObject, Qt, 
)
from PyQt6.QtWidgets import (
	QWidget, QLabel, QTableWidgetItem, QMenu, QStyledItemDelegate, QVBoxLayout, QListWidget, QSizePolicy,
	QListWidgetItem, QPushButton, QFileDialog, QTextEdit, QHBoxLayout, QStackedWidget, QTableWidgetItem, 
	QLineEdit, QComboBox, QApplication, QCheckBox, 
)
from PyQt6.QtGui import (
	QKeyEvent, QAction, 
)

from qavm.qavmapi import utils
from qavm.qavmapi.gui import GetThemeData, FolderPathsListWidget

# import qavm.logs as logs
# logger = logs.logger

##############################################################################
#############################  ##############################
##############################################################################

class BaseSettingsContainer(object):
	def __init__(self, settingsEntries: dict[str, Any] = dict()):
		self.settingsEntries: dict[str, Any] = settingsEntries

	def DumpToString(self) -> str:
		return json.dumps(self.settingsEntries)

	def InitializeFromString(self, dataStr: str) -> bool:
		try:
			data: dict = json.loads(dataStr)
			for key in self.settingsEntries.keys():
				if key not in data:
					return False
				self.settingsEntries[key] = data[key]
			return True
		except Exception as e:
			print(f'ERROR: Failed to parse settings data: {e}')  # TODO: use logger instead
			return False
		
	def Contains(self, key: str) -> bool:
		return key in self.settingsEntries
		
	def Get(self, key: str) -> Any:
		if key in self.settingsEntries:
			return self.settingsEntries[key]
		
		print(f'ERROR: Settings entry "{key}" not found in settingsEntries.')

	def Set(self, key: str, value: Any):
		if key in self.settingsEntries:
			self.settingsEntries[key] = value
			return
		
		print(f'ERROR: Settings entry "{key}" not found in settingsEntries. Adding it.')
		self.settingsEntries[key] = value
		
class BaseSettingsEntry(object):
	def __init__(self, defaultValue: Any, title: str, toolTip: str = '', isTileUpdateRequired: bool = False, isTableUpdateRequired: bool = False):
		self.defaultValue: Any = defaultValue
		self.title: str = title
		self.toolTip: str = toolTip
		self.isTileUpdateRequired: bool = isTileUpdateRequired
		self.isTableUpdateRequired: bool = isTableUpdateRequired

		self.value: Any = None
		self.isDirty: bool = False  # is set to True when the value is changed, but not saved yet

class BaseSettings(QObject):
	CONTAINER_QAVM_DEFAULTS: dict[str, Any] = dict()  # contains common per-software settings (e.g. search paths, etc.)
	CONTAINER_DEFAULTS: dict[str, Any] = dict()  # should be overridden by subclasses

	# SETTINGS_ENTRIES: dict[str, BaseSettingsEntry] = dict()
	
	settingChanged = pyqtSignal(str, object)  # (settingName, newValue)

	# TODO: these need to be refactored
	tilesUpdateRequired = pyqtSignal()  # is emitted when settings are changing something that requires tiles to be updated
	tablesUpdateRequired = pyqtSignal()  # same as tilesUpdateRequired, but for tables

	def __init__(self, prefName: str):
		super().__init__()

		self.container = self.InitializeContainer()
		self.prefFilePath: Path = utils.GetPrefsFolderPath() / f'{prefName}.json'

	def InitializeContainer(self) -> BaseSettingsContainer:
		""" Initializes the settings container with default values. """
		return BaseSettingsContainer({**self.CONTAINER_QAVM_DEFAULTS, **self.CONTAINER_DEFAULTS})

	def Load(self):
		if not self.prefFilePath.exists():
			print(f"Preferences file doesn't exist. Creating: {self.prefFilePath}")  # TODO: use logger instead
			self.Save()
		
		with open(self.prefFilePath, 'r') as f:
			if self.container is None:
				self.container = self.InitializeContainer()
			self.container.InitializeFromString(f.read())

	def Save(self):
		# self._syncContainerFromSettingsEntries(onlyDirty=False)
		if not self.prefFilePath.parent.exists():
			print(f"Preferences folder doesn't exist. Creating: {self.prefFilePath.parent}")  # TODO: use logger instead
			self.prefFilePath.parent.mkdir(parents=True, exist_ok=True)
		with open(self.prefFilePath, 'w') as f:
			f.write(self.container.DumpToString())

	def CreateWidgets(self, parent: QWidget) -> list[tuple[str, QWidget]]:
		""" Creates settings widgets (one per settings category). Returns a list of tuples, where each tuple contains the category name and the widget. """
		return [('BaseSettings', QWidget(parent))]  # BaseSettings does not provide a widget by default, subclasses should override this method
	
	def GetSetting(self, key: str) -> Any:
		if self.container.Contains(key):
			return self.container.Get(key)
		print(f'ERROR: Settings entry "{key}" not found in settingsEntries.')  # TODO: use logger instead

	def SetSetting(self, key: str, value: Any):
		if self.container.Contains(key):
			self.container.Set(key, value)
			self.settingChanged.emit(key, value)
			return
		print(f'ERROR: Unknown settings entry "{key}". Cannot set value.')  # TODO: use logger instead

class SoftwareBaseSettings(BaseSettings):
	""" Base class for software settings. Contains basic implementation for settings that are common for all software. """
	CONTAINER_QAVM_DEFAULTS: dict[str, Any] = {
		'search_paths': [],  # list of paths to search for software
		'include_global_search_paths': True,  # whether to include global search paths from QAVM settings
	}
	
	def CreateWidgets(self, parent: QWidget) -> list[tuple[str, QWidget]]:
		# Create a widget with QVBoxLayout and a QListWidget for search paths
		widget = QWidget(parent)
		layout = QVBoxLayout(widget)
		layout.setAlignment(Qt.AlignmentFlag.AlignTop)
		layout.addWidget(QLabel('Search paths:', widget))

		self.searchPathsWidget = FolderPathsListWidget()
		self.searchPathsWidget.itemChanged.connect(lambda _: self._updateSearchPathsSetting())
		self.searchPathsWidget.itemDeleted.connect(lambda _: self._updateSearchPathsSetting())
		self.searchPathsWidget.urlDropped.connect(self._searchPathFolderDropped)

		for path in self.GetSetting('search_paths'):
			self._addSearchPathToList(path)
		
		# This is a little dangerous, because the change may come from outside (even when the window is closed),
		qavmSettings: QAVMSettings = QApplication.instance().GetSettingsManager().GetQAVMSettings()
		qavmSettings.settingChanged.connect(self._updateSearchPathsEvaluatedWidget)
		# Hence, need to ensure it's disconnected when the widget is destroyed
		# qavmSettings.settingChanged.disconnect(self._updateSearchPathsEvaluatedWidget)
		self.searchPathsWidget.destroyed.connect(partial(qavmSettings.settingChanged.disconnect, self._updateSearchPathsEvaluatedWidget))

		layout.addWidget(self.searchPathsWidget)

		addButton = QPushButton('Browse', widget)
		addButton.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
		addButton.clicked.connect(self._selectAndAddSearchPath)
		
		includeGlobalCheckbox = QCheckBox('Include global search paths', widget)
		includeGlobalCheckbox.setToolTip('Include global search paths from QAVM settings')
		includeGlobalCheckbox.setChecked(self.GetSetting('include_global_search_paths'))
		includeGlobalCheckbox.stateChanged.connect(self._includeGlobalSearchPathsChanged)
		
		buttonLayout = QHBoxLayout()
		buttonLayout.addWidget(includeGlobalCheckbox)
		buttonLayout.addStretch()  # Pushes the button to the right
		buttonLayout.addWidget(addButton)
		layout.addLayout(buttonLayout)
		
		layout.addWidget(QLabel('Search paths evaluated:', widget))
		self.searchPathsEvaluated = QTextEdit(widget)
		self.searchPathsEvaluated.setReadOnly(True)
		self.searchPathsEvaluated.setMinimumHeight(64)
		self.searchPathsEvaluated.setFixedHeight(64)
		self.searchPathsEvaluated.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
		self.searchPathsEvaluated.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
		layout.addWidget(self.searchPathsEvaluated)
		
		self._updateSearchPathsEvaluatedWidget()

		return [('Common', widget)]
	
	def _selectAndAddSearchPath(self):
		""" Opens a file dialog to select a directory and adds it to the search paths. """
		dirPath = QFileDialog.getExistingDirectory(self.searchPathsWidget, 'Select Search Path')
		if dirPath:
			self._addSearchPathToList(dirPath)
			self._updateSearchPathsSetting()

	def _searchPathFolderDropped(self, path: str):
		if not Path(path).is_dir():
			return
		self._addSearchPathToList(path)
		self._updateSearchPathsSetting()

	def _addSearchPathToList(self, path: str):
		""" Adds a new search path to the QListWidget if it doesn't already exist. """
		if not path:
			return
		path = str(Path(path).resolve())
		if not any(self.searchPathsWidget.item(i).text() == path for i in range(self.searchPathsWidget.count())):
			item = QListWidgetItem(path)
			item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
			self.searchPathsWidget.addItem(item)

	def _updateSearchPathsSetting(self):
		""" Updates the search paths setting based on the current items in the QListWidget. """
		self.SetSetting('search_paths', [self.searchPathsWidget.item(i).text() for i in range(self.searchPathsWidget.count())])
		self._updateSearchPathsEvaluatedWidget()

	def _updateSearchPathsEvaluatedWidget(self):
		evaluatedPaths: list[str] = [str(p) for p in self.GetEvaluatedSearchPaths()]
		self.searchPathsEvaluated.setPlainText('\n'.join(evaluatedPaths))

	def _includeGlobalSearchPathsChanged(self, state: Qt.CheckState):
		""" Updates the search paths setting when the include global checkbox is changed. """
		self.SetSetting('include_global_search_paths', state == Qt.CheckState.Checked.value)
		self._updateSearchPathsEvaluatedWidget()

	def GetEvaluatedSearchPaths(self) -> list[Path]:
		""" Returns the evaluated search paths, which are a combination of global and software-specific search paths. """
		searchPathsGlobal = []
		if self.GetSetting('include_global_search_paths'):
			searchPathsGlobal = QApplication.instance().GetSettingsManager().GetQAVMSettings().GetGlobalSearchPaths()
		return [Path(p).resolve().absolute() for p in set(searchPathsGlobal + self.GetSetting('search_paths'))]


##############################################################################
########################### QAVM Plugin: Software ############################
##############################################################################

class QualifierIdentificationConfig(object):
	def __init__(self, 
			  requiredFileList: list[str | list[str]] = [],
			  requiredDirList: list[str | list[str]] = [],
			  negativeFileList: list[str] = [],
			  negativeDirList: list[str] = [],
			  fileContentsList: list[tuple[str, bool, int]] = []):
		"""
		QualifierIdentificationConfig is used to define the identification mask for the qualifier.
		- requiredFileList: list of files that MUST be present in the directory
		- requiredDirList: list of directories that MUST be present in the directory
		- negativeFileList: list of files that MUST NOT be present in the directory
		- negativeDirList: list of directories that MUST NOT be present in the directory
		- fileContentsList: list of files to be read from the disk, each item is a tuple: (filename, isBinary, lengthLimit)

		The required can contain list entries, which will be treated as OR condition.
		For example, the following requiredFileList: ['file1.txt', ['file2.txt', 'file3.txt']]
		will match both ['file1.txt', 'file2.txt'] and ['file1.txt', 'file3.txt']
		"""
		self.requiredFileList = requiredFileList or []  # list of files that MUST be present
		self.requiredDirList = requiredDirList or []  # list of directories that MUST be present
		self.negativeFileList = negativeFileList or []  # list of files that MUST NOT be present
		self.negativeDirList = negativeDirList or []  # list of directories that MUST NOT be present

		self.fileContentsList = fileContentsList or []  # list of files to be read from the disk: tuples: (filename, isBinary, lengthLimit)

	def SetRequiredFileList(self, fileList: list[str | list[str]]):
		self.requiredFileList = fileList
	def SetRequiredDirList(self, dirList: list[str | list[str]]):
		self.requiredDirList = dirList
	def SetNegativeFileList(self, fileList: list[str]):
		self.negativeFileList = fileList
	def SetNegativeDirList(self, dirList: list[str]):
		self.negativeDirList = dirList
	def SetFileContentsList(self, fileContentsList: list[tuple[str, bool, int]]):
		self.fileContentsList = fileContentsList
	
	def GetRequiredFileList(self) -> list[str | list[str]]:
		return self.requiredFileList
	def GetRequiredDirList(self) -> list[str | list[str]]:
		return self.requiredDirList
	def GetNegativeFileList(self) -> list[str]:
		return self.negativeFileList
	def GetNegativeDirList(self) -> list[str]:
		return self.negativeDirList
	def GetFileContentsList(self) -> list[tuple[str, bool, int]]:
		return self.fileContentsList
	
	def IdentificationMaskPasses(self, dirPath: Path) -> bool:
		""" Checks if the directory path passes the file mask defined in this config. """
		for file in self.requiredFileList:
			if isinstance(file, list):
				if not any((dirPath / f).is_file() for f in file):
					return False
			elif not (dirPath / file).is_file():
				return False
		
		for folder in self.requiredDirList:
			if isinstance(folder, list):
				if not any((dirPath / f).is_dir() for f in folder):
					return False
			elif not (dirPath / folder).is_dir():
				return False
		
		for file in self.negativeFileList:
			if (dirPath / file).is_file():
				return False
		
		for folder in self.negativeDirList:
			if (dirPath / folder).is_dir():
				return False
			
		return True
	
	def GetFileContents(self, dirPath: Path) -> dict[str, str | bytes]:
		""" Reads the files from the disk and returns their contents as a dictionary. """
		fileContents = dict()
		for file, isBinary, lengthLimit in self.fileContentsList:
			try:
				with open(dirPath / file, 'rb' if isBinary else 'r') as f:
					fileContents[file] = f.read(lengthLimit if lengthLimit else -1)
			except Exception as e:
				# logger.warning(f'Failed to read file "{dirPath/file}": {e}')
				pass
		return fileContents

class BaseQualifier(object):
	""" Base class for software qualifiers. Qualifier is used to identify the software (e.g. based on the directory contents) """
	def __init__(self):
		pass

	def ProcessSearchPaths(self, searchPaths: list[str]) -> list[str]:
		""" Search paths list can be modified here (e.g. if some regex adjustments are needed based on searchPaths themselves or some default source paths are to be added). """
		return searchPaths
	
	# TODO: Add support for subfolder file list
	def GetIdentificationConfig(self) -> QualifierIdentificationConfig:
		""" Sets the identification mask for the qualifier."""
		return QualifierIdentificationConfig()

	def Identify(self, currentPath: Path, fileContents: dict[str, str | bytes]) -> list[str]:
		return True

class BaseDescriptor(QObject):
	""" Base class for software descriptors. Descriptor is used to represent the software among other plugin parts, such as TileBuilder, TableBuilder, ContextMenu, etc. """
	updated = pyqtSignal()

	def __init__(self, dirPath: Path, settings: SoftwareBaseSettings, fileContents: dict[str, str | bytes]):
		super().__init__()
		self.UID: str = utils.GetHashString(str(dirPath))
		self.dirPath: Path = dirPath
		self.dirType: str = self._retrieveDirType()  # '' - normal dir, 's' - symlink, 'j' - junction
		self.settings: SoftwareBaseSettings = settings
	
	def GetExecutablePath(self) -> Path:
		return Path()

	def __hash__(self) -> int:
		return hash(str(self.dirPath))

	def __str__(self):
		return 'BaseDescriptor'
	
	def __repr__(self):
		return self.__str__()
	
	def _retrieveDirType(self) -> str:  # TODO: make it enum
		dirType = ''
		if utils.IsPathSymlink(self.dirPath):
			dirType = 'S'
		elif utils.IsPathJunction(self.dirPath):
			dirType = 'J'
		return dirType

class BaseContextMenu(QObject):
	def __init__(self, settings: SoftwareBaseSettings):
		super().__init__()
		self.settings: SoftwareBaseSettings = settings
	
	def CreateMenu(self, desc: BaseDescriptor) -> QMenu:
		return QMenu()

class BaseBuilder(QObject):
	def __init__(self, settings: SoftwareBaseSettings, contextMenu: BaseContextMenu):
		super().__init__()
		self.settings: SoftwareBaseSettings = settings
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
	
	def GetItemDelegateClass(self) -> QStyledItemDelegate.__class__:
		return QStyledItemDelegate
	
	# TODO: change key from int to enum. Currently 0 - LMB, 1 - RMB, 2 - MMB
	def HandleClick(self, desc: BaseDescriptor, row: int, col: int, isDouble: bool, key: int, modifiers: Qt.KeyboardModifier):
		pass

class BaseCustomView(QWidget):
	def __init__(self, settings: SoftwareBaseSettings, parent=None):
		super().__init__(parent)
		self.settings: SoftwareBaseSettings = settings

class BaseMenuItems(QObject):
	def __init__(self, settings: SoftwareBaseSettings):
		super().__init__()
		self.settings: SoftwareBaseSettings = settings

	def GetMenus(self, parent=None) -> list[QMenu | QAction]:
		""" Returns a list of QMenu objects to be added to the main menu. """
		return []