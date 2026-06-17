from __future__ import annotations
import uuid
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
	QApplication, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
	QLineEdit, QPushButton, QComboBox, QColorDialog, QScrollArea, QGroupBox,
	QMessageBox, QDialogButtonBox,
)

from qavm.manager_tags import TagsManager, BaseTagImpl, TagScope
from qavm.manager_plugin import PluginManager, QAVMWorkspace, SoftwareHandler

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


class TagEditorDialog(QDialog):
	""" Modal dialog to create or edit a tag (name, color, scopes). """
	def __init__(self, tag: BaseTagImpl | None = None, parent: QWidget | None = None) -> None:
		super().__init__(parent)

		app = QApplication.instance()
		self.tagsManager: TagsManager = app.GetTagsManager()
		self.pluginManager: PluginManager = app.GetPluginManager()
		self.workspace: QAVMWorkspace = app.GetWorkspace()

		self.editTag: BaseTagImpl | None = tag
		self.resultTag: BaseTagImpl | None = None
		self._color: str = tag.GetColor() if tag else '#3498db'

		self.setModal(True)
		self.setWindowTitle("Edit Tag" if tag else "New Tag")
		self.resize(640, 420)

		self._pluginOptions, self._softwareOptions, self._viewOptions = self._collectScopeOptions()

		mainLayout = QVBoxLayout(self)

		formLayout = QFormLayout()
		self.nameField: QLineEdit = QLineEdit(tag.GetName() if tag else '')
		self.nameField.setPlaceholderText("Tag name...")
		formLayout.addRow("Name:", self.nameField)

		colorRow = QHBoxLayout()
		self.colorButton: QPushButton = QPushButton("Pick Color…")
		self.colorButton.clicked.connect(self._pickColor)
		self.colorPreview: QLabel = QLabel()
		self.colorPreview.setFixedSize(48, 24)
		colorRow.addWidget(self.colorButton)
		colorRow.addWidget(self.colorPreview)
		colorRow.addStretch(1)
		formLayout.addRow("Color:", colorRow)
		mainLayout.addLayout(formLayout)
		self._updateColorPreview()

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

		buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
		buttonBox.accepted.connect(self.accept)
		buttonBox.rejected.connect(self.reject)
		mainLayout.addWidget(buttonBox)

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
		color = QColorDialog.getColor(initial, self, "Pick Tag Color")
		if color.isValid():
			self._color = color.name()
			self._updateColorPreview()

	def _updateColorPreview(self):
		self.colorPreview.setStyleSheet(f'background-color: {self._color}; border: 1px solid #555;')
		self.colorPreview.setToolTip(self._color)

	def GetResultTag(self) -> BaseTagImpl | None:
		return self.resultTag

	def accept(self) -> None:
		name: str = self.nameField.text().strip()
		if not name:
			QMessageBox.warning(self, "Invalid Tag", "Tag name cannot be empty.")
			return

		scopes: list[TagScope] = [row.GetScope() for row in self._scopeRows]

		if self.editTag is not None:
			self.editTag.name = name
			self.editTag.color = self._color
			self.editTag.tagScopes = scopes
			self.tagsManager.UpdateTag(self.editTag)
			self.resultTag = self.editTag
		else:
			newTag = BaseTagImpl(uuid.uuid4().hex, name, self._color, scopes)
			self.tagsManager.AddTag(newTag)
			self.resultTag = newTag

		super().accept()
