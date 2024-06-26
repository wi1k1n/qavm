import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QLabel, QTabWidget, QScrollArea
)

from manager_plugin import PluginManager, SoftwareHandler
from manager_settings import SettingsManager

from qavmapi import BaseDescriptor, BaseSettings
import qavmapi_utils
from utils_gui import FlowLayout, BubbleWidget, StaticBorderWidget

import logs
logger = logs.logger


# class SettingsWindowExample(QMainWindow):
# 	def __init__(self, app, parent: QWidget | None = None) -> None:
# 		super(MainWindow, self).__init__(parent)

# 		self.setWindowTitle("QAVM - Settings")
# 		self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint) # | Qt.WindowStaysOnTopHint) # https://pythonprogramminglanguage.com/pyqt5-window-flags/
# 		self.resize(400, 400)

class DialogsManager:
	def __init__(self, parent: QMainWindow) -> None:
		self.parent = parent
		
		# self.settings = SettingsWindowExample(self)

	def GetPreferencesWindow(self):
		return self.preferences

class MainWindow(QMainWindow):
	def __init__(self, app, parent: QWidget | None = None) -> None:
		super(MainWindow, self).__init__(parent)

		self.app = app

		self.setWindowTitle("QAVM")
		self.resize(1420, 840)
		self.setMinimumSize(350, 250)

		self.dialogsManager: DialogsManager = DialogsManager(self)

		layout: QVBoxLayout = QVBoxLayout()

		tabsWidget: QTabWidget = QTabWidget()

		tilesWidget = self._createTilesWidget(self._scanSoftware(), self)
		tabsWidget.addTab(tilesWidget, "Tiles")
		
		self.setCentralWidget(tabsWidget)
	
	
	def _createTilesWidget(self, descs: list[BaseDescriptor], parent: QWidget):
		tiles: list[QWidget] = list()

		for desc in descs:
			tile = self._createTileWidget(desc, QColor(100, 100, 100), parent)
			tiles.append(tile)

		flWidget = self._createFlowLayoutWithFromWidgets(self, tiles)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget, self)

		return scrollWidget
	def _createTileWidget(self, desc: BaseDescriptor, accentColor: QColor, parent: QWidget):
		descWidget = self._createDescWidget(desc, self)
		animatedBorderWidget = self._wrapWidgetInAnimatedBorder(descWidget, accentColor, self)
		return animatedBorderWidget
	def _createDescWidget(self, desc: BaseDescriptor, parent: QWidget):
		descWidget = QWidget(parent)

		parentBGColor = parent.palette().color(parent.backgroundRole())
		descWidget.setStyleSheet(f"background-color: {parentBGColor.name()};")
		# DEBUG # descWidget.setStyleSheet("background-color: rgb(200, 200, 255);")
		
		descLayout = QVBoxLayout(descWidget)
		descLayout.setContentsMargins(0, 0, 0, 0)
		descLayout.setSpacing(0)

		tileData: dict = desc.GetTileData()

		for key, value in tileData.items():
			label = QLabel(f'{key}: {value}')
			label.setFont(QFont('SblHebrew', 10))
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			# DEBUG # label.setStyleSheet("background-color: pink;")
			descLayout.addWidget(label)

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
	def _createFlowLayoutWithFromWidgets(self, parent, widgets: list[QWidget]):
		flWidget = QWidget(parent)
		flWidget.setMinimumWidth(50)

		flowLayout = FlowLayout(flWidget, margin=1, hspacing=0, vspacing=0)
		flowLayout.setSpacing(0)

		for widget in widgets:
			widget.setFixedWidth(widget.sizeHint().width())
			flowLayout.addWidget(widget)

		return flWidget
	def _wrapWidgetInScrollArea(self, widget, parent):
		scrollWidget = QScrollArea(parent)
		scrollWidget.setWidgetResizable(True)
		scrollWidget.setWidget(widget)
		return scrollWidget




	def _scanSoftware(self) -> list[BaseDescriptor]:
		pluginManager: PluginManager = self.app.GetPluginManager()
		settingsManager: SettingsManager = self.app.GetSettingsManager()

		softwareHandler: SoftwareHandler
		softwareHandler = pluginManager.GetSoftwareHandler(settingsManager.GetSelectedSoftwareUID())

		qualifier = softwareHandler.GetQualifierClass()()
		descriptorClass = softwareHandler.GetDescriptorClass()
		# tileBuilder = softwareHandler.GetTileBuilderClass()()
		settingsClass = softwareHandler.GetSettingsClass()
		if not settingsClass:
			settingsClass = BaseSettings

		searchPaths = settingsManager.GetSearchPaths()
		searchPaths = qualifier.ProcessSearchPaths(searchPaths)

		config = qualifier.GetIdentificationConfig()
		if not qavmapi_utils.ValidateQualifierConfig(config):
			raise Exception('Invalid Qualifier config')
		
		def getFileListIgnoreError(pathDir: str) -> list[str]:
			try:
				fileList: list[str] = [os.path.join(pathDir, f) for f in os.listdir(pathDir)]
				return list(filter(lambda f: os.path.isfile(f), fileList))
			except:
				logger.warning(f'Failed to get file list: {pathDir}')
			return list()
		
		def getDirListIgnoreError(pathDir: str) -> list[str]:
			try:
				dirList: list[str] = [os.path.join(pathDir, d) for d in os.listdir(pathDir)]
				return list(filter(lambda d: os.path.isdir(d), dirList))
			except:
				logger.warning(f'Failed to get dir list: {pathDir}')
			return list()
		
		def TryPassFileMask(dirPath: str, positiveFiles: list[str], negativeFiles: list[str]) -> bool:
			files = {os.path.relpath(fp, dirPath).casefold() for fp in getFileListIgnoreError(dirPath)}
			if len(positiveFiles) > len({f.casefold() for f in positiveFiles}.intersection(files)):
				return False
			if len({f.casefold() for f in negativeFiles}.intersection(files)):
				return False
			return True
		
		def GetFileContents(filePath: str) -> dict[str, str | bytes]:
			return dict()
		
		softwareDescs: list[BaseDescriptor] = list()

		MAX_DEPTH = 1  # TODO: make this a settings value
		currentDepthLevel: int = 0
		searchPathsList = set(searchPaths)
		while currentDepthLevel < MAX_DEPTH:
			subfoldersSearchPathsList = set()
			for searchPath in searchPathsList:
				dirs: set[str] = set(getDirListIgnoreError(searchPath))
				subdirs: set[str] = set()
				# for dir in dirs:
				for dir in sorted(dirs):
					passed = TryPassFileMask(dir, config['requiredFileList'], config['negativeFileList'])
					if not passed:
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue

					fileContents = GetFileContents(dir)
					if not qualifier.Identify(dir, fileContents):
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue
					softwareDescs.append(descriptorClass(dir, fileContents))
				subfoldersSearchPathsList.update(subdirs)
			searchPathsList = subfoldersSearchPathsList
			currentDepthLevel += 1
		
		return softwareDescs