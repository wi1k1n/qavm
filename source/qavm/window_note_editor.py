from __future__ import annotations
from PyQt6.QtWidgets import (
	QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QCheckBox,
	QPushButton, QApplication, 
)
from PyQt6.QtCore import Qt

from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorData
from qavm.qavmapi import BaseDescriptor

class NoteEditorDialog(QDialog):
	def __init__(self, desc: BaseDescriptor, parent: QWidget | None = None) -> None:
		super().__init__(parent)

		self.setWindowTitle("Edit Note")
		self.resize(400, 300)

		app = QApplication.instance()
		self.descDataManager: DescriptorDataManager = app.GetDescriptorDataManager()
		
		self.descriptor: BaseDescriptor = desc
		descData: DescriptorData = self.descDataManager.GetDescriptorData(self.descriptor)

		# Layouts
		mainLayout = QVBoxLayout()

		# Small text field
		self.enableSmallTextCheckbox = QCheckBox("Enable small text")
		self.enableSmallTextCheckbox.setChecked(True)
		self.enableSmallTextCheckbox.stateChanged.connect(self._toggleSmallTextField)

		self.smallTextField = QTextEdit()
		self.smallTextField.setText(descData.noteVisible)
		self.smallTextField.setPlaceholderText("Enter visible text...")
		self.smallTextField.setFixedHeight(50)

		mainLayout.addWidget(self.enableSmallTextCheckbox)
		mainLayout.addWidget(self.smallTextField)

		# Note field
		self.noteField = QTextEdit()
		self.noteField.setText(descData.note)
		self.noteField.setPlaceholderText("Enter note (supports basic HTML formatting)...")

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

	def _toggleSmallTextField(self, state: int):
		"""Enable or disable the small text field based on the checkbox state."""
		self.smallTextField.setVisible(state == Qt.CheckState.Checked.value)
	
	def accept(self) -> None:
		"""Override accept to save changes before closing."""
		descData: DescriptorData = self.descDataManager.GetDescriptorData(self.descriptor)
		descData.noteVisible = self.smallTextField.toPlainText()
		descData.note = self.noteField.toPlainText()
		self.descDataManager.SetDescriptorData(self.descriptor, descData)
		self.descDataManager.SaveData()
		super().accept()