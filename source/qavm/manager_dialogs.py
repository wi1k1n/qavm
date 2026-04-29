from qavm.window_pluginselect import WorkspaceManagerWindow
from qavm.window_main import MainWindow
from qavm.window_settings import PreferencesWindow
from qavm.window_note_editor import NoteEditorDialog
from qavm.manager_plugin import QAVMWorkspace

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
	QApplication, QWidget, QDialog, QVBoxLayout, QLabel, QProgressBar,
)

import qavm.logs as logs
logger = logs.logger


class WorkspaceLoadWorker(QThread):
	"""Worker thread that performs heavy workspace loading (settings + software scanning)."""
	progressChanged = pyqtSignal(str)

	def __init__(self, workspace: QAVMWorkspace, parent=None):
		super().__init__(parent)
		self.workspace = workspace

	def run(self):
		app = QApplication.instance()
		settingsManager = app.GetSettingsManager()

		self.progressChanged.emit("Loading workspace settings...")
		settingsManager.LoadWorkspaceSoftwareSettings(self.workspace)

		self.progressChanged.emit("Scanning software...")
		sfHandlers, _ = self.workspace.GetInvolvedSoftwareHandlers()
		for swHandler in sfHandlers:
			self.progressChanged.emit(f"Scanning: {swHandler.GetName()}...")
			app.LoadSoftwareDescriptors(swHandler)

		self.progressChanged.emit("Scanning finished")
		self.thread().wait(10)

class WorkspaceLoadProgressDialog(QDialog):
	"""Non-closable progress dialog shown while workspace is loading."""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Loading Workspace")
		self.setFixedSize(350, 100)
		self.setWindowFlags(self.windowFlags() & ~(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowContextHelpButtonHint))
		self.setModal(True)

		layout = QVBoxLayout(self)
		self.label = QLabel("Preparing workspace...")
		layout.addWidget(self.label)

		self.progressBar = QProgressBar()
		self.progressBar.setRange(0, 0)  # Indeterminate
		layout.addWidget(self.progressBar)

	def setStatus(self, text: str):
		self.label.setText(text)

	def closeEvent(self, event):
		event.ignore()


class DialogsManager:
	def __init__(self) -> None:
		self.selectPluginWindow: WorkspaceManagerWindow = None
		self.mainWindow: MainWindow = None
		self.windowPrefs: PreferencesWindow = None
		self._loadWorker: WorkspaceLoadWorker = None
		self._loadProgressDialog: WorkspaceLoadProgressDialog = None

	def ShowWorkspace(self, workspace: QAVMWorkspace):
		app = QApplication.instance()
		app.SetWorkspace(workspace)

		self._loadProgressDialog = WorkspaceLoadProgressDialog()
		self._loadProgressDialog.show()

		self._loadWorker = WorkspaceLoadWorker(workspace)
		self._loadWorker.progressChanged.connect(self._loadProgressDialog.setStatus)
		self._loadWorker.finished.connect(self._onWorkspaceLoaded)
		self._loadWorker.start()

	def _onWorkspaceLoaded(self):
		"""Called on main thread when background loading finishes."""
		self._loadWorker.deleteLater()
		self._loadWorker = None

		self.GetMainWindow().show()

		if self._loadProgressDialog:
			self._loadProgressDialog.close()
			self._loadProgressDialog.deleteLater()
			self._loadProgressDialog = None

	def ShowWorkspaceManager(self):
		self.ResetPreferencesWindow()
		self.ResetMainWindow()
		self.GetPluginSelectionWindow().show()

	def ShowPreferences(self):
		prefsWindow: QWidget = self.GetPreferencesWindow()
		prefsWindow.show()
		prefsWindow.activateWindow()

	def GetPluginSelectionWindow(self):
		if self.selectPluginWindow is None:
			self.selectPluginWindow: WorkspaceManagerWindow = WorkspaceManagerWindow()
		return self.selectPluginWindow
	
	def GetMainWindow(self):
		if self.mainWindow is None:
			self.mainWindow: MainWindow = MainWindow()
		return self.mainWindow
	
	def GetPreferencesWindow(self):
		if self.windowPrefs is None:
			self.windowPrefs = PreferencesWindow(self.GetMainWindow())
		return self.windowPrefs
	
	def ResetMainWindow(self):
		self._resetWindow(self.mainWindow)
		self.mainWindow = None

	def ResetPreferencesWindow(self):
		self._resetWindow(self.windowPrefs)
		self.windowPrefs = None

	def _resetWindow(self, window: QWidget):
		if not window:
			return
		window.close()
		window.deleteLater()