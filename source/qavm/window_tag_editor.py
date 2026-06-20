from __future__ import annotations
import uuid
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
	QApplication, QTextEdit, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
	QLineEdit, QPushButton, QComboBox, QColorDialog, QScrollArea, QGroupBox,
	QMessageBox, QDialogButtonBox,
)

from qavm.manager_tags import TagsManager, BaseTagImpl, TagScope
from qavm.manager_plugin import PluginManager, QAVMWorkspace, SoftwareHandler
from qavm.utils_gui import DistinguishableColorGenerator
from qavm.qavmapi.gui import PickContrastingTextColor

if TYPE_CHECKING:
	pass

import qavm.logs as logs
logger = logs.logger

EMPTY_OPTION_LABEL: str = '<all>'


class _ScopeRowWidget(QWidget):
	""" A single editable tag scope row: plugin / software / view selectors + remove button. """
	def __init__(self, pluginOptions: list[str], softwareOptions: list[str], viewOptions: list[str],
				 scope: TagScope | None, onRemove, parent: QWidget | None = None):
		super().__init__(parent)

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)

		self.pluginCombo: QComboBox = self._makeCombo(pluginOptions, scope.pluginID if scope else '')
		self.softwareCombo: QComboBox = self._makeCombo(softwareOptions, scope.softwareID if scope else '')
		self.viewCombo: QComboBox = self._makeCombo(viewOptions, scope.viewUID if scope else '')

		layout.addWidget(QLabel("Plugin:"))
		layout.addWidget(self.pluginCombo, 1)
		layout.addWidget(QLabel("Software:"))
		layout.addWidget(self.softwareCombo, 1)
		layout.addWidget(QLabel("View:"))
		layout.addWidget(self.viewCombo, 1)

		removeBtn = QPushButton("X")
		removeBtn.setFixedWidth(48)
		removeBtn.setToolTip("Remove this scope")
		removeBtn.clicked.connect(lambda: onRemove(self))
		layout.addWidget(removeBtn)

	def _makeCombo(self, options: list[str], current: str) -> QComboBox:
		combo = QComboBox(self)
		combo.setEditable(True)
		combo.addItem(EMPTY_OPTION_LABEL)
		for opt in options:
			if opt:
				combo.addItem(opt)
		if current:
			idx = combo.findText(current)
			if idx >= 0:
				combo.setCurrentIndex(idx)
			else:
				combo.setEditText(current)
		else:
			combo.setCurrentIndex(0)
		return combo

	def _comboValue(self, combo: QComboBox) -> str:
		text: str = combo.currentText().strip()
		if text == EMPTY_OPTION_LABEL:
			return ''
		return text

	def GetScope(self) -> TagScope:
		return TagScope(
			pluginID=self._comboValue(self.pluginCombo),
			softwareID=self._comboValue(self.softwareCombo),
			viewUID=self._comboValue(self.viewCombo),
		)

"""
# TODO: create markdown text edit widget that supports conventional markdown shortcuts
| Action        |                     Windows/Linux |                           macOS | Markdown inserted     |
| ------------- | --------------------------------: | ------------------------------: | --------------------- |
| Bold          |                          `Ctrl+B` |                         `Cmd+B` | `**text**`            |
| Italic        |                          `Ctrl+I` |                         `Cmd+I` | `*text*` or `_text_`  |
| Underline     |                          `Ctrl+U` |                         `Cmd+U` | Not standard Markdown |
| Link          |                          `Ctrl+K` |                         `Cmd+K` | `[text](url)`         |
| Inline code   |        `Ctrl+E` or `Ctrl+Shift+C` |        `Cmd+E` or `Cmd+Shift+C` | `` `code` ``          |
| Code block    |  `Ctrl+Shift+K` / editor-specific | `Cmd+Shift+K` / editor-specific | ` ``` `               |
| Heading       |                  `Ctrl+Alt+1/2/3` |                 `Cmd+Alt+1/2/3` | `#`, `##`, `###`      |
| Bullet list   |        `Ctrl+Shift+8` or `Ctrl+L` |        `Cmd+Shift+8` or `Cmd+L` | `- item`              |
| Numbered list |                    `Ctrl+Shift+7` |                   `Cmd+Shift+7` | `1. item`             |
| Quote         | `Ctrl+Shift+.` or editor-specific |                   `Cmd+Shift+.` | `> quote`             |
| Strikethrough |   `Alt+Shift+5` / editor-specific | `Cmd+Shift+X` / editor-specific | `~~text~~`            |
| Preview       |                    `Ctrl+Shift+V` |                   `Cmd+Shift+V` | rendered view         |

"""

class TagEditorDialog(QDialog):
	""" Modal dialog to create or edit a tag (name, color, scopes). """
	def __init__(self, tag: BaseTagImpl | None = None, parent: QWidget | None = None,
				 existingTags: list[BaseTagImpl] | None = None, initialScope: TagScope | None = None) -> None:
		super().__init__(parent)

		app = QApplication.instance()
		self.tagsManager: TagsManager = app.GetTagsManager()
		self.pluginManager: PluginManager = app.GetPluginManager()
		self.workspace: QAVMWorkspace = app.GetWorkspace()

		self.editTag: BaseTagImpl | None = tag
		self.resultTag: BaseTagImpl | None = None
		if tag:
			self._color: str = tag.GetColor()
		else:
			# Auto-pick a color that is the most distinguishable from the currently visible tags.
			existingColors: list[QColor] = [QColor(t.GetColor()) for t in (existingTags or []) if t.GetColor()]
			self._color = DistinguishableColorGenerator().GenerateColor(existingColors).name()

		self.setModal(True)
		self.setWindowTitle(f'{"Edit" if tag else "Create"} Tag - [{tag.GetName() if tag else ""}]')
		self.resize(960, 320)

		self._pluginOptions, self._softwareOptions, self._viewOptions = self._collectScopeOptions()

		mainLayout = QVBoxLayout(self)

		formLayout = QFormLayout()
		nameRow = QHBoxLayout()
		self.nameField: QLineEdit = QLineEdit(tag.GetName() if tag else '')
		self.nameField.setPlaceholderText("Tag name...")
		nameRow.addWidget(self.nameField)
		self.colorButton: QPushButton = QPushButton()
		self.colorButton.setFixedWidth(96)
		self.colorButton.clicked.connect(self._pickColor)
		nameRow.addWidget(self.colorButton)
		formLayout.addRow("Name:", nameRow)
		self.descriptionField: QTextEdit = QTextEdit()
		self.descriptionField.setAcceptRichText(False)
		self.descriptionField.setPlainText(tag.GetDescription() if tag else '')
		self.descriptionField.setPlaceholderText("Optional description... (Markdown supported)")
		self.descriptionField.setFixedHeight(80)
		formLayout.addRow("Description:", self.descriptionField)
		mainLayout.addLayout(formLayout)
		self._updateColorButton()

		# Scopes section
		scopesGroup = QGroupBox("Scopes (empty list = global / applies everywhere)")
		scopesGroupLayout = QVBoxLayout(scopesGroup)

		self.scopesContainer: QWidget = QWidget()
		self.scopesLayout: QVBoxLayout = QVBoxLayout(self.scopesContainer)
		self.scopesLayout.setContentsMargins(0, 0, 0, 0)
		self.scopesLayout.addStretch(1)

		scrollArea = QScrollArea()
		scrollArea.setWidgetResizable(True)
		scrollArea.setWidget(self.scopesContainer)
		scopesGroupLayout.addWidget(scrollArea)

		addScopeBtn = QPushButton("+ Add Scope")
		addScopeBtn.clicked.connect(lambda: self._addScopeRow(None))
		scopesGroupLayout.addWidget(addScopeBtn)

		mainLayout.addWidget(scopesGroup, 1)

		self._scopeRows: list[_ScopeRowWidget] = []
		if tag:
			for scope in tag.GetScopes():
				self._addScopeRow(scope)
		elif initialScope is not None:
			# A brand new tag starts with a single scope that mirrors the current palette filter.
			self._addScopeRow(initialScope)

		buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
		buttonBox.accepted.connect(self.accept)
		buttonBox.rejected.connect(self.reject)

		buttonRow = QHBoxLayout()
		if self.editTag is not None:
			deleteButton = QPushButton("Delete")
			deleteButton.setStyleSheet('background-color: #943737; color: #ffffff;')
			deleteButton.clicked.connect(self._onDelete)
			buttonRow.addWidget(deleteButton)
		buttonRow.addStretch(1)
		buttonRow.addWidget(buttonBox)
		mainLayout.addLayout(buttonRow)

		QShortcut(QKeySequence('Ctrl+Return'), self, activated=self.accept)
		QShortcut(QKeySequence('Ctrl+Enter'), self, activated=self.accept)

	def _collectScopeOptions(self) -> tuple[list[str], list[str], list[str]]:
		pluginOptions: set[str] = set()
		softwareOptions: set[str] = set()
		viewOptions: set[str] = set()
		for pluginID, softwareID, swHandler in self.pluginManager.GetSoftwareHandlers():
			pluginOptions.add(pluginID)
			softwareOptions.add(softwareID)
			for dataPath in swHandler.GetTileBuilderClasses().keys():
				viewOptions.add(dataPath)
			for dataPath in swHandler.GetTableBuilderClasses().keys():
				viewOptions.add(dataPath)
			for dataPath in swHandler.GetCustomViewClasses().keys():
				viewOptions.add(dataPath)
		# Add common wildcard helpers for views
		viewOptions.update({'views/tiles/*', 'views/table/*', 'views/custom/*'})
		return sorted(pluginOptions), sorted(softwareOptions), sorted(viewOptions)

	def _addScopeRow(self, scope: TagScope | None):
		row = _ScopeRowWidget(self._pluginOptions, self._softwareOptions, self._viewOptions, scope, self._removeScopeRow)
		# Insert before the trailing stretch
		self.scopesLayout.insertWidget(self.scopesLayout.count() - 1, row)
		self._scopeRows.append(row)

	def _removeScopeRow(self, row: _ScopeRowWidget):
		if row in self._scopeRows:
			self._scopeRows.remove(row)
		self.scopesLayout.removeWidget(row)
		row.setParent(None)
		row.deleteLater()

	def _pickColor(self):
		initial = QColor(self._color) if self._color else QColor('#3498db')
		dialog = QColorDialog(initial, self)
		dialog.setWindowTitle("Pick Tag Color")
		dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
		
		# workaround for issue with values being clipped
		dialog.setStyleSheet("""
			QColorDialog QSpinBox,
			QColorDialog QDoubleSpinBox {
				padding-left: 2px;
				padding-right: 2px;
				min-width: 48px;
			}

			QColorDialog QLineEdit {
				padding-left: 2px;
				padding-right: 2px;
			}
		""")

		if dialog.exec():
			color = dialog.selectedColor()
			if color.isValid():
				self._color = color.name()
				self._updateColorButton()

	def _updateColorButton(self):
		bgColor: QColor = QColor(self._color)
		textColor: QColor = PickContrastingTextColor(bgColor)
		self.colorButton.setText(self._color)
		self.colorButton.setStyleSheet(f'background-color: {bgColor.name()}; color: {textColor.name()};')
		self.colorButton.setToolTip(self._color)

	def GetResultTag(self) -> BaseTagImpl | None:
		return self.resultTag

	def _onDelete(self) -> None:
		if self.editTag is None:
			return
		reply = QMessageBox.question(
			self, "Delete Tag",
			f"Delete tag '{self.editTag.GetName()}'?\nIt will be removed from all items it is assigned to.",
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)
		if reply != QMessageBox.StandardButton.Yes:
			return
		self.tagsManager.DeleteTag(self.editTag)
		self.resultTag = None
		self.reject()

	def accept(self) -> None:
		name: str = self.nameField.text().strip()
		if not name:
			QMessageBox.warning(self, "Invalid Tag", "Tag name cannot be empty.")
			return

		scopes: list[TagScope] = [row.GetScope() for row in self._scopeRows]
		description: str = self.descriptionField.toPlainText().strip()

		if self.editTag is not None:
			self.editTag.name = name
			self.editTag.color = self._color
			self.editTag.tagScopes = scopes
			self.editTag.description = description
			self.tagsManager.UpdateTag(self.editTag)
			self.resultTag = self.editTag
		else:
			newTag = BaseTagImpl(uuid.uuid4().hex, name, self._color, scopes, description=description)
			self.tagsManager.AddTag(newTag)
			self.resultTag = newTag

		super().accept()


def OpenTagEditorDialog(tag: BaseTagImpl, parent: QWidget | None = None) -> bool:
	""" Opens the modal tag editor for an existing tag and returns True if the user saved changes.

	Shared entry point so that every place that lets the user edit a tag (tags palette, table/tiles tag
	bubbles, ...) triggers the exact same persistence + propagation path (TagsManager.UpdateTag, which
	refreshes affected descriptors and emits tagsChanged). """

	# Ensure the dialog is parented to a top-level window. If caller passed a child
	# widget (e.g. a small cell widget), parenting to that widget can cause the
	# dialog to be embedded or clipped by the parent's layout on some platforms.
	# Use the caller's window() (top-level) when available, or fall back to the
	# application's active window.
	_dialogParent: QWidget | None = None
	if parent is not None:
		try:
			win = parent.window()
			if win is not None:
				_dialogParent = win
		except Exception:
			_dialogParent = None
	if _dialogParent is None:
		app = QApplication.instance()
		if app is not None and hasattr(app, 'activeWindow') and app.activeWindow() is not None:
			_dialogParent = app.activeWindow()

	dialog = TagEditorDialog(tag, _dialogParent)
	return bool(dialog.exec())
