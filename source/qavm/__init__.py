import sys, os
from functools import partial
from typing import List

# Tweak Windows app group for the custom icon to be used instead of Python one
try:
    from ctypes import windll  # Only exists on Windows.
    myappid = 'in.wi1k.tools.qavm'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

import logs
logger = logs.logger

from qavm_version import LoadVersionInfo
from plugin_manager import PluginManager, Plugin, SoftwareHandler
from settings_manager import SettingsManager
import utils

from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import (
    QObject, Qt, QEvent, pyqtSignal, QProcess, QPoint, QRect
)
from PyQt6.QtGui import (
    QIcon, QKeySequence, QPixmap, QFont, QCursor, QMouseEvent, QDropEvent,
    QDragEnterEvent, QKeyEvent, QCloseEvent
)
from PyQt6.QtWidgets import (
	QApplication, QLabel, QMainWindow, QMenu, QMenuBar, QStyle, QStyleHintReturn, QStyleOption,
	QToolBar, QWidget, QTabWidget, QLayout, QVBoxLayout, QHBoxLayout, QFrame,
	QScrollArea, QGroupBox, QTreeWidget, QTreeWidgetItem, QStatusBar, QProxyStyle, QMessageBox,
	QPushButton, QSizePolicy
)

from window_main import MainWindow

class PluginSelectionWindow(QMainWindow):
	pluginSelected = pyqtSignal(str, str)  # (pluginID, softwareID)

	def __init__(self, app, parent: QWidget | None = None) -> None:
		super(PluginSelectionWindow, self).__init__(parent)

		self.setWindowTitle("Select Software handler")
		self.resize(480, 240)

		layout: QVBoxLayout = QVBoxLayout()

		pluginManager: PluginManager = app.GetPluginManager()
		swHandlers: list[tuple[str, str, SoftwareHandler]] = pluginManager.GetSoftwareHandlers()  # [pluginID, softwareID, SoftwareHandler]

		for pluginUID, softwareID, softwareHandler in swHandlers:
			plugin: Plugin = pluginManager.GetPlugin(pluginUID)
			button = QPushButton(f'[{plugin.GetName()} @ {plugin.GetVersionStr()} ({pluginUID})] {softwareHandler.GetName()} ({softwareID})')
			button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
			button.clicked.connect(partial(self.selectPlugin, plugin.pluginID, softwareID))
			layout.addWidget(button)

		widget: QWidget = QWidget()
		widget.setLayout(layout)

		self.setCentralWidget(widget)

		self.update()
	
	def selectPlugin(self, pluginUID: str, softwareID: str):
		self.pluginSelected.emit(pluginUID, softwareID)
		self.close()

# Extensive PyQt tutorial: https://realpython.com/python-menus-toolbars/#building-context-or-pop-up-menus-in-pyqt
class QAVMApp(QApplication):
	def __init__(self, argv: List[str]) -> None:
		super().__init__(argv)
		
		self.setApplicationName('QAVM')
		self.setOrganizationName('wi1k.in.prod')
		self.setOrganizationDomain('wi1k.in')
		
		self.pluginManager = PluginManager(utils.GetPluginsFolderPath())
		self.pluginManager.LoadPlugins()

		self.settingsManager = SettingsManager(utils.GetPrefsFolderPath())
		self.settingsManager.LoadSettings()
		
		selectedSoftwareUID = self.settingsManager.GetSelectedSoftwareUID()
		swHandlers: dict[str, SoftwareHandler] = {f'{pUID}.{sID}': swHandler for pUID, sID, swHandler in self.pluginManager.GetSoftwareHandlers()}  # {softwareUID: SoftwareHandler}

		if selectedSoftwareUID and selectedSoftwareUID not in swHandlers:
			logger.warning(f'Selected software plugin not found: {selectedSoftwareUID}')

		if selectedSoftwareUID in swHandlers:
			logger.info(f'Selected software plugin: {selectedSoftwareUID}')
			self.startMainWindow()
		elif len(swHandlers) == 1:
			logger.info(f'The only software plugin: {list(swHandlers.keys())[0]}')
			self.startMainWindow()
		else:
			self.selectPluginWindow: PluginSelectionWindow = PluginSelectionWindow(self)
			self.selectPluginWindow.pluginSelected.connect(self.slot_PluginSelected)
			self.selectPluginWindow.show()
	
	def slot_PluginSelected(self, pluginUID: str, softwareID: str):
		logger.info(f'Selected software UID: {pluginUID}.{softwareID}')
		self.settingsManager.SetSelectedSoftwareUID(f'{pluginUID}.{softwareID}')
		self.startMainWindow()
	
	def startMainWindow(self):
		self.mainWindow: MainWindow = MainWindow()
		# self.mainWindow.hideToTraySignal.connect(self._hideToTray)

		# self.iconApp: QIcon = QIcon(OsPathJoin(IMAGES_FOLDER, 'icon.png'))
		# self.setWindowIcon(self.iconApp)
		
		font: QFont = self.font()
		# font.setPixelSize(16)
		self.setFont(font)

		# self.initTray()

		self.mainWindow.show()
		# self.mainWindow.FirstRunHandler()
	
	# def initTray(self):
	# 	actionExit: QAction = QAction('Exit')
	# 	actionExit.triggered.connect(sys.exit)
	# 	trayMenu: QMenu = QMenu()
	# 	trayMenu.addAction(actionExit)

	# 	self.trayIcon: QSystemTrayIcon = QSystemTrayIcon()
	# 	self.trayIcon.setIcon(self.iconApp)
	# 	self.trayIcon.setContextMenu(trayMenu)
	# 	self.trayIcon.activated.connect(self._activateFromTray)
	# 	self.trayIcon.setVisible(False)
	
	# def _activateFromTray(self, reason):
	# 	if reason != QSystemTrayIcon.ActivationReason.Context and self.mainWindow.isHidden():
	# 		self.mainWindow.show()
	# 		self.mainWindow.activateWindow()
	# 		self.trayIcon.setVisible(False)
	# 		# win.restoreState()

	# def _hideToTray(self):
	# 	self.trayIcon.setVisible(True)

	def GetPluginManager(self) -> PluginManager:
		return self.pluginManager
	def GetSettingsManager(self) -> SettingsManager:
		return self.settingsManager

if __name__ == "__main__":
	try:
		LoadVersionInfo(os.getcwd())
		app: QAVMApp = QAVMApp(sys.argv)
		sys.exit(app.exec())
	except Exception as e:
		logger.exception("QAVM application crashed")