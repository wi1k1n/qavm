from __future__ import annotations
import html
import uuid
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
	QApplication, QTextEdit, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
	QLineEdit, QPushButton, QComboBox, QColorDialog, QScrollArea, QGroupBox,
	QMessageBox, QDialogButtonBox,
)

from qavm.manager_tags import TagsManager, BaseTagImpl, TagScope, TAG_SCOPE_VIEWS_ENABLED
from qavm.manager_plugin import PluginManager, QAVMWorkspace, SoftwareHandler
from qavm.utils_gui import DistinguishableColorGenerator
from qavm.qavmapi.gui import PickContrastingTextColor, HoverFadeTooltipMixin

if TYPE_CHECKING:
	pass

import qavm.logs as logs
logger = logs.logger

EMPTY_OPTION_LABEL: str = '<all>'


class _ScopeCombo(HoverFadeTooltipMixin, QComboBox):
	""" Combobox that displays plugin/software names while storing their IDs, and shows the selected ID
	as an app-style hover FadeTooltip (via HoverFadeTooltipMixin). """
	def __init__(self, options: list[tuple[str, str]], current: str, parent: QWidget | None = None):
		super().__init__(parent)
		self._InitHoverTooltip()

		self.addItem(EMPTY_OPTION_LABEL, '')
		for optID, optName in options:
			if optID:
				self.addItem(optName, optID)
		self._selectValue(current)

	def _selectValue(self, value: str) -> None:
		if not value:
			self.setCurrentIndex(0)
			return
		idx: int = self.findData(value)
		if idx < 0:
			# The stored ID refers to an unloaded plugin/software: keep it selectable by showing the raw ID.
			self.addItem(value, value)
			idx = self.count() - 1
		self.setCurrentIndex(idx)

	def GetValue(self) -> str:
		return self.currentData() or ''

	def enterEvent(self, event):
		self._ScheduleTooltip()
		super().enterEvent(event)

	def _GetTooltipHtml(self) -> str | None:
		value: str = self.currentData() or ''
		if not value:
			return None
		return f'<div>{html.escape(value)}</div>'


class _ScopeRowWidget(QWidget):
	""" A single editable tag scope row: plugin / software / (view) selectors + remove button.
	Combos display plugin/software names but store their IDs (shown as hover tooltips). The view selector
	is only shown when TAG_SCOPE_VIEWS_ENABLED is set; otherwise the scope's viewUID is preserved as-is. """
	def __init__(self, pluginOptions: list[tuple[str, str]], softwareOptions: list[tuple[str, str]],
				 viewOptions: list[tuple[str, str]], scope: TagScope | None, onRemove,
				 parent: QWidget | None = None):
		super().__init__(parent)

		# When view scoping is hidden, keep whatever viewUID the scope already had (default '' = all views).
		self._preservedViewUID: str = scope.viewUID if scope else ''

		layout = QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)

		self.pluginCombo: _ScopeCombo = _ScopeCombo(pluginOptions, scope.pluginID if scope else '')
		self.softwareCombo: _ScopeCombo = _ScopeCombo(softwareOptions, scope.softwareID if scope else '')

		layout.addWidget(QLabel("Plugin:"))
		layout.addWidget(self.pluginCombo, 1)
		layout.addWidget(QLabel("Software:"))
		layout.addWidget(self.softwareCombo, 1)

		self.viewCombo: _ScopeCombo | None = None
		if TAG_SCOPE_VIEWS_ENABLED:
			self.viewCombo = _ScopeCombo(viewOptions, scope.viewUID if scope else '')
			layout.addWidget(QLabel("View:"))
			layout.addWidget(self.viewCombo, 1)

		removeBtn = QPushButton("X")
		removeBtn.setFixedWidth(48)
		removeBtn.setToolTip("Remove this scope")
		removeBtn.clicked.connect(lambda: onRemove(self))
		layout.addWidget(removeBtn)

	def GetScope(self) -> TagScope:
		return TagScope(
			pluginID=self.pluginCombo.GetValue(),
			softwareID=self.softwareCombo.GetValue(),
			viewUID=self.viewCombo.GetValue() if self.viewCombo is not None else self._preservedViewUID,
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

	def _collectScopeOptions(self) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
		""" Returns (pluginOptions, softwareOptions, viewOptions), each a list of (id, displayName) tuples
		sorted by display name. Plugin/software show human-friendly names; views have no separate name. """
		pluginOptions: dict[str, str] = {}
		softwareOptions: dict[str, str] = {}
		viewOptions: dict[str, str] = {}
		for pluginID, softwareID, swHandler in self.pluginManager.GetSoftwareHandlers():
			plugin = self.pluginManager.GetPlugin(pluginID)
			pluginOptions[pluginID] = plugin.GetName() if plugin else pluginID
			softwareOptions[softwareID] = swHandler.GetName()
			for dataPath in swHandler.GetTileBuilderClasses().keys():
				viewOptions[dataPath] = dataPath
			for dataPath in swHandler.GetTableBuilderClasses().keys():
				viewOptions[dataPath] = dataPath
			for dataPath in swHandler.GetCustomViewClasses().keys():
				viewOptions[dataPath] = dataPath
		
		# Add common wildcard helpers for views
		for wildcard in ('views/tiles/*', 'views/table/*', 'views/custom/*'):
			viewOptions.setdefault(wildcard, wildcard)

		activePluginID, activeSoftwareID = self.parent()._getActiveContext()
		# Apply visual prefix to active plugin/software names (avoid double-prefixing).
		if activePluginID and activePluginID in pluginOptions:
			if not pluginOptions[activePluginID].startswith('* '):
				pluginOptions[activePluginID] = '* ' + pluginOptions[activePluginID]
		if activeSoftwareID and activeSoftwareID in softwareOptions:
			if not softwareOptions[activeSoftwareID].startswith('* '):
				softwareOptions[activeSoftwareID] = '* ' + softwareOptions[activeSoftwareID]
		def _sortedByName(options: dict[str, str]) -> list[tuple[str, str]]:
			return sorted(options.items(), key=lambda kv: kv[1].lower())
		return _sortedByName(pluginOptions), _sortedByName(softwareOptions), _sortedByName(viewOptions)

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
