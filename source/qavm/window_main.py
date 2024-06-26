import os

from manager_plugin import PluginManager, SoftwareHandler
from manager_settings import SettingsManager

from qavmapi import BaseDescriptor, BaseSettings
import qavmapi_utils

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel

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

		self.setWindowTitle("QAVM")
		self.resize(1420, 840)
		self.setMinimumSize(350, 250)

		self.dialogsManager: DialogsManager = DialogsManager(self)

		layout: QVBoxLayout = QVBoxLayout()

		pluginManager: PluginManager = app.GetPluginManager()
		settingsManager: SettingsManager = app.GetSettingsManager()

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
		
		softwareDescs = list()

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
		
		print(softwareDescs)


		for swDesc in softwareDescs:
			label = QLabel(str(swDesc))
			layout.addWidget(label)

		widget: QWidget = QWidget()
		widget.setLayout(layout)

		self.setCentralWidget(widget)

		self.update()

		# self.createMenuBar()
		# self.createToolBar()
		# self.createStatusBar()

		self.update()