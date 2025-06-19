import argparse
from typing import List
from pathlib import Path

import qavm.logs as logs
logger = logs.logger

from qavm.manager_plugin import PluginManager, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings
from qavm.manager_dialogs import DialogsManager
import qavm.qavmapi.utils as utils  # TODO: rename to qutils
import qavm.qavmapi.gui as gui_utils
import qavm.qavmapi_utils as qavmapi_utils
from qavm.qavmapi import BaseDescriptor, QualifierIdentificationConfig
from qavm.utils_plugin_package import VerifyPlugin

from PyQt6.QtCore import (
	Qt, QObject, QEvent, 
)
from PyQt6.QtGui import (
    QFont, QIcon, QKeySequence, 
)
from PyQt6.QtWidgets import (
	QApplication, 
)

from qavm.window_main import MainWindow
from qavm.window_pluginselect import PluginSelectionWindow

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QFile, QTextStream
from pathlib import Path

from PyQt6.QtWidgets import QWidget
from pathlib import Path
import html

from PyQt6.QtWidgets import (
	QWidget, QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
	QListWidget, QListWidgetItem, QTableWidget, QPlainTextEdit
)
from PyQt6.QtCore import Qt
from pathlib import Path
import html


class QtHTMLDump:
	def __init__(self, root_widget: QWidget):
		self.root = root_widget

	def _get_widget_content(self, widget: QWidget) -> str:
		"""Returns string representation of widget content, if applicable."""
		if isinstance(widget, QLabel):
			return f"Label: {html.escape(widget.text())}"
		elif isinstance(widget, QLineEdit):
			return f"LineEdit: {html.escape(widget.text())}"
		elif isinstance(widget, QTextEdit):
			return f"TextEdit: {html.escape(widget.toPlainText())}"
		elif isinstance(widget, QPlainTextEdit):
			return f"PlainTextEdit: {html.escape(widget.toPlainText())}"
		elif isinstance(widget, QComboBox):
			items = [widget.itemText(i) for i in range(widget.count())]
			current = widget.currentText()
			return f"ComboBox (current='{html.escape(current)}'): [{', '.join(map(html.escape, items))}]"
		elif isinstance(widget, QPushButton):
			return f"Button: {html.escape(widget.text())}"
		elif isinstance(widget, QListWidget):
			items = [widget.item(i).text() for i in range(widget.count())]
			return f"ListWidget: [{', '.join(map(html.escape, items))}]"
		elif isinstance(widget, QTableWidget):
			rows, cols = widget.rowCount(), widget.columnCount()
			cells = []
			for r in range(rows):
				row_items = []
				for c in range(cols):
					item = widget.item(r, c)
					text = item.text() if item else ""
					row_items.append(html.escape(text))
				cells.append(" | ".join(row_items))
			return f"TableWidget ({rows}x{cols}):<br>" + "<br>".join(cells)
		return ""

	def _dump_widget_tree(self, widget: QWidget, level: int = 0) -> str:
		indent = "  " * level
		rect = widget.geometry()
		obj_name = html.escape(widget.objectName() or "unnamed")
		class_name = widget.__class__.__name__
		visible = widget.isVisible()
		size_policy = widget.sizePolicy()
		layout = widget.layout()
		layout_name = layout.__class__.__name__ if layout else "None"

		visibility_class = "invisible" if not visible else ""
		content = self._get_widget_content(widget)

		html_block = (
			f"{indent}<div class='widget {visibility_class}' "
			f"data-class='{class_name}' "
			f"data-name='{obj_name}' "
			f"data-geometry='x:{rect.x()}, y:{rect.y()}, w:{rect.width()}, h:{rect.height()}'>\n"
			f"{indent}  <div class='header' onclick='toggle(this)'>"
			f"<strong>{class_name}</strong> (<code>{obj_name}</code>) — "
			f"<em>{rect.x()},{rect.y()},{rect.width()},{rect.height()}</em><br>"
			f"Layout: {layout_name}, SizePolicy: H={size_policy.horizontalPolicy().name}, V={size_policy.verticalPolicy().name}"
			f"</div>\n"
		)
		if content:
			html_block += f"{indent}  <div class='content'>{content}</div>\n"

		html_block += f"{indent}  <div class='children'>\n"
		for child in sorted(widget.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly), key=lambda c: c.objectName() or ""):
			html_block += self._dump_widget_tree(child, level + 1)
		html_block += f"{indent}  </div>\n{indent}</div>\n"
		return html_block

	def generate_html(self) -> str:
		html_header = """<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>Qt Layout Snapshot</title>
<style>
	body { font-family: sans-serif; font-size: 13px; background: #f0f0f0; color: #333; }
	.widget { border: 1px dashed #999; padding: 6px; margin: 6px; background: #fff; }
	.header { cursor: pointer; background: #e8e8e8; padding: 4px; }
	.children { margin-left: 20px; display: block; }
	.content { margin-left: 12px; color: #555; background: #fefefe; font-family: monospace; white-space: pre-wrap; }
	.invisible .header { color: #999; background: #f5f5f5; }
	code { background: #eee; padding: 0 4px; }
</style>
<script>
	function toggle(header) {
		const children = header.parentElement.querySelector('.children');
		if (children) children.style.display = children.style.display === 'none' ? 'block' : 'none';
	}
</script></head><body>
<h2>Layout Snapshot</h2>
"""
		html_body = self._dump_widget_tree(self.root)
		return f"{html_header}{html_body}</body></html>"

	def save_to_file(self, path: str | Path = "layout_snapshot.html"):
		path = Path(path)
		html = self.generate_html()
		path.write_text(html, encoding="utf-8")
		print(f"[QtHTMLDump] Snapshot saved to: {path.resolve()}")


# Extensive PyQt tutorial: https://realpython.com/python-menus-toolbars/#building-context-or-pop-up-menus-in-pyqt
class QAVMApp(QApplication):
	def __init__(self, argv: List[str], args: argparse.Namespace) -> None:
		super().__init__(argv)
		
		self.setApplicationName('QAVM')
		self.setOrganizationName('wi1k.in.prod')
		self.setOrganizationDomain('wi1k.in')
		
		self.iconApp: QIcon = QIcon(str(Path('res/qavm_icon.png').resolve()))
		self.setWindowIcon(self.iconApp)
		
		self.installEventFilter(self)

		self.pluginsFolderPaths: set[Path] = {utils.GetDefaultPluginsFolderPath()}
		self.pluginPaths: set[Path] = set()  # Paths to individual plugins
		self.builtinPluginPaths: set[Path] = set()  # Paths to built-in plugins (i.e. unpacked plugins)
		self.softwareDescriptions: list[BaseDescriptor] = None

		self.processArgs(args)

		logger.info(f'Plugins folder paths: {[str(p) for p in self.pluginsFolderPaths]}')
		logger.info(f'Extra individial plugin paths: {[str(p) for p in self.pluginPaths]}')
		
		self.dialogsManager: DialogsManager = DialogsManager(self)

		self.settingsManager = SettingsManager(self, utils.GetPrefsFolderPath())
		self.settingsManager.LoadQAVMSettings()
		self.qavmSettings: QAVMGlobalSettings = self.settingsManager.GetQAVMSettings()

		if not args.ignoreBuiltinPlugins:
			self._verifyBuiltinPlugins(args)

		self.pluginManager = PluginManager(self, self.builtinPluginPaths.union(self.pluginPaths), self.GetPluginsFolderPaths())
		self.pluginManager.LoadPlugins()

		# self.settingsManager.LoadModuleSettings()

		gui_utils.SetTheme(self.settingsManager.GetQAVMSettings().GetAppTheme())
		self.dialogsManager.GetPluginSelectionWindow().show()

	def GetPluginManager(self) -> PluginManager:
		return self.pluginManager
	
	def GetSettingsManager(self) -> SettingsManager:
		return self.settingsManager
	
	def GetDialogsManager(self) -> DialogsManager:
		return self.dialogsManager
	
	def GetPluginsFolderPaths(self) -> list[Path]:
		""" Returns a list of paths to the plugins folders (i.e. folder, containing plugin folders). """
		return list(self.pluginsFolderPaths)
	
	def GetPluginPaths(self) -> list[Path]:
		""" Returns a set of paths to individual plugins (i.e. a folder, containing the plugin). """
		return list(self.pluginPaths)
	
	def GetSoftwareDescriptions(self) -> list[BaseDescriptor]:
		if self.softwareDescriptions is None:
			self.softwareDescriptions = self.ScanSoftware()
		return self.softwareDescriptions
	
	def ResetSoftwareDescriptions(self) -> None:
		self.softwareDescriptions = None
	
	def ScanSoftware(self) -> list[BaseDescriptor]:
		qavmSettings = self.settingsManager.GetQAVMSettings()

		softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()
		if softwareHandler is None:
			raise Exception('No software handler found')

		qualifier = softwareHandler.GetQualifier()
		descriptorClass = softwareHandler.GetDescriptorClass()
		softwareSettings = softwareHandler.GetSettings()

		searchPaths = softwareSettings.GetEvaluatedSearchPaths()
		if not searchPaths:
			searchPaths = []
		searchPaths = qualifier.ProcessSearchPaths(searchPaths)

		config: QualifierIdentificationConfig = qualifier.GetIdentificationConfig()
		# if not qavmapi_utils.ValidateQualifierConfig(config):
		# 	raise Exception('Invalid Qualifier config')
		
		def getDirListIgnoreError(pathDir: str) -> list[Path]:
			try:
				return [d for d in Path(pathDir).iterdir() if d.is_dir()]
				# dirList: list[Path] = [Path(pathDir)/d for d in os.listdir(pathDir)]
				# return list(filter(lambda d: os.path.isdir(d), dirList))
			except:
				# logger.warning(f'Failed to get dir list: {pathDir}')
				pass
			return list()
		
		softwareDescs: list[BaseDescriptor] = list()

		MAX_DEPTH = 1  # TODO: make this a settings value
		currentDepthLevel: int = 0
		searchPathsList = set(searchPaths)
		while currentDepthLevel < MAX_DEPTH:
			subfoldersSearchPathsList = set()
			for searchPath in searchPathsList:
				dirs: set[Path] = set(getDirListIgnoreError(searchPath))
				subdirs: set[str] = set()
				# for dir in dirs:
				for dir in sorted(dirs):
					passed = config.IdentificationMaskPasses(dir)
					# passed = TryPassFileMask(dir, config)
					if not passed:
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue

					fileContents: dict[str, str | bytes] = config.GetFileContents(dir)
					# fileContents: dict[str, str | bytes] = GetFileContents(dir, config)
					if not qualifier.Identify(dir, fileContents):
						subdirs.update(set(getDirListIgnoreError(dir)))
						continue
					softwareDescs.append(descriptorClass(dir, softwareSettings, fileContents))
				subfoldersSearchPathsList.update(subdirs)
			searchPathsList = subfoldersSearchPathsList
			currentDepthLevel += 1
		
		return softwareDescs
	
	def processArgs(self, args: argparse.Namespace) -> None:
		# TODO: make these args globally accessible from everywhere
		logger.info(f'QAVMApp arguments: {vars(args)}')
		
		if args.pluginsFolder:
			self.pluginsFolderPaths = {Path(args.pluginsFolder)}
		if args.extraPluginsFolder:
			self.pluginsFolderPaths.update({Path(p) for p in args.extraPluginsFolder})
		
		if args.extraPluginPath:
			self.pluginPaths.update({Path(p) for p in args.extraPluginPath})

		self.selectedSoftwareUID = args.selectedSoftwareUID

	def _loadVerificationKey(self) -> bytes:
		try:
			from qavm.verification_key import VERIFICATION_KEY
			return VERIFICATION_KEY.encode('utf-8')
		except Exception as e:
			logger.error(f'Failed to load verification key: {e}')
			return b''

	# TODO: refactor this giant function
	def _verifyBuiltinPlugins(self, args: argparse.Namespace) -> None:
		if utils.PlatformWindows():
			builtinPluginsPath: Path = utils.GetQAVMRootPath() / 'builtin_plugins'
		elif utils.PlatformMacOS():
			builtinPluginsPath: Path = utils.GetQAVMRootPath() / '../Resources/builtin_plugins'
		if not builtinPluginsPath.is_dir():
			logger.error(f'Builtin plugins directory does not exist: {builtinPluginsPath}')
			return
		
		# Verify the plugin signature
		publicKey: bytes = self._loadVerificationKey()
		if not publicKey:
			logger.error('Public key for plugin verification is not available')
			return

		for pluginPath in builtinPluginsPath.iterdir():
			if not pluginPath.is_dir():
				continue

			logger.info(f'Verifying plugin signature: {pluginPath}')
			pluginSignaturePath: Path = pluginPath.parent / f'{pluginPath.name}.sig'
			if not pluginSignaturePath.exists():
				logger.error(f'Plugin signature not found: {pluginSignaturePath}')
				continue

			if not VerifyPlugin(pluginPath, pluginSignaturePath, publicKey):
				logger.error(f'Plugin verification failed: {pluginPath}')
				continue

			self.builtinPluginPaths.add(pluginPath.resolve().absolute())


	def eventFilter(self, obj, event):
		if event.type() == QEvent.Type.KeyPress:
			if (event.key() == Qt.Key.Key_Q and event.modifiers() == (Qt.KeyboardModifier.ControlModifier)):
				activeWindow = QApplication.activeWindow()
				if not isinstance(activeWindow, QWidget):
					print("[QtHTMLDump] No active window to dump layout from.")
					return False
				print("[QtHTMLDump] Dumping layout of the active window (", activeWindow.objectName(), ") to HTML.")
				dumper = QtHTMLDump(activeWindow)
				dumper.save_to_file("layout_snapshot.html")
				return True
		return super().eventFilter(obj, event)