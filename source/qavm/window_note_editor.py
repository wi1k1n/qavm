from __future__ import annotations
from PyQt6.QtWidgets import (
	QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QCheckBox,
	QPushButton, QApplication, 
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QKeyEvent, QShortcut

from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorDataImpl
from qavm.qavmapi import BaseDescriptor

class NoteEditorDialog(QDialog):
	def __init__(self, desc: BaseDescriptor, parent: QWidget | None = None) -> None:
		super().__init__(parent)

		self.setWindowTitle("Edit Note")
		self.resize(400, 300)

		app = QApplication.instance()
		self.descDataManager: DescriptorDataManager = app.GetDescriptorDataManager()
		
		self.descriptor: BaseDescriptor = desc
		descData: DescriptorDataImpl = self.descDataManager.GetDescriptorData(self.descriptor)

		# Layouts
		mainLayout = QVBoxLayout()

		# allow inner class to reference the dialog instance
		parent_dialog = self

		# Custom text edits to handle Tab/Enter behaviour
		class _CustomTextEdit(QTextEdit):
			def __init__(self, *args, is_small: bool = False, **kwargs):
				super().__init__(*args, **kwargs)
				self.setAcceptRichText(False)
				self._is_small = is_small

			def keyPressEvent(self, event: QKeyEvent) -> None:
				key = event.key()
				mods = event.modifiers()
				# Handle Tab: move focus to next widget (use dialog's focus chain)
				if key == Qt.Key.Key_Tab and not (mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)):
					if parent_dialog is not None:
						parent_dialog.focusNextPrevChild(True)
					else:
						self.focusNextPrevChild(True)
					return

				# For the small text field: Enter should move focus to next field, Shift+Enter inserts newline
				if self._is_small and (key in (Qt.Key.Key_Return, Qt.Key.Key_Enter)):
					if mods & Qt.KeyboardModifier.ControlModifier:
						# Let global shortcut handle save; ignore here
						return
					if mods & Qt.KeyboardModifier.ShiftModifier:
						super().keyPressEvent(event)
						return
					# plain Enter -> move focus to the detailed note field
					if parent_dialog is not None and hasattr(parent_dialog, 'noteField'):
						parent_dialog.noteField.setFocus()
					else:
						self.focusNextPrevChild(True)
					return

				# Default behaviour
				super().keyPressEvent(event)

		self.smallTextField = _CustomTextEdit(is_small=True)
		self.smallTextField.setText(descData.noteSmall)
		self.smallTextField.setPlaceholderText("Enter visible text...")
		self.smallTextField.setFixedHeight(50)
		# Let Tab change focus by default
		self.smallTextField.setTabChangesFocus(True)

		mainLayout.addWidget(self.smallTextField)

		# Note field
		self.noteField = _CustomTextEdit()
		self.noteField.setText(descData.noteDetail)
		self.noteField.setPlaceholderText("Enter note...  (Markdown supported)")
		# Let Tab change focus by default
		self.noteField.setTabChangesFocus(True)

		# Buttons
		buttonLayout = QHBoxLayout()
		self.saveButton = QPushButton("Save")
		self.cancelButton = QPushButton("Cancel")
		self.saveButton.clicked.connect(self.accept)  # Accept dialog on Save
		self.cancelButton.clicked.connect(self.reject)  # Reject dialog on Cancel
		buttonLayout.addWidget(self.saveButton)
		buttonLayout.addWidget(self.cancelButton)

		# Add widgets to main layout
		mainLayout.addWidget(QLabel("Note:"))
		mainLayout.addWidget(self.noteField)
		mainLayout.addLayout(buttonLayout)

		self.setLayout(mainLayout)

		# Set explicit tab order to ensure rotation: small -> detailed -> save -> cancel -> small
		QWidget.setTabOrder(self.smallTextField, self.noteField)
		QWidget.setTabOrder(self.noteField, self.saveButton)
		QWidget.setTabOrder(self.saveButton, self.cancelButton)
		QWidget.setTabOrder(self.cancelButton, self.smallTextField)

		# Ctrl+Enter anywhere should trigger Save
		QShortcut(QKeySequence('Ctrl+Return'), self, activated=self.accept)
		QShortcut(QKeySequence('Ctrl+Enter'), self, activated=self.accept)
	
	def accept(self) -> None:
		"""Override accept to save changes before closing."""
		descData: DescriptorDataImpl = self.descDataManager.GetDescriptorData(self.descriptor)
		descData.noteSmall = self.smallTextField.toPlainText()
		descData.noteDetail = self.noteField.toPlainText()
		self.descDataManager.SetDescriptorData(self.descriptor, descData)
		self.descDataManager.SaveData()
		super().accept()