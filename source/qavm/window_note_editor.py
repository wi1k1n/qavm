from PyQt6.QtWidgets import (
	QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QCheckBox, QPushButton
)
from PyQt6.QtCore import Qt

class NoteEditorDialog(QDialog):
	def __init__(self, parent: QWidget | None = None) -> None:
		super().__init__(parent)

		self.setWindowTitle("Edit Note")
		self.resize(400, 300)

		# Layouts
		mainLayout = QVBoxLayout()
		smallTextLayout = QHBoxLayout()

		# Small text field
		self.enableSmallTextCheckbox = QCheckBox("Enable small text")
		self.enableSmallTextCheckbox.setChecked(True)
		self.enableSmallTextCheckbox.stateChanged.connect(self._toggleSmallTextField)

		self.smallTextField = QTextEdit()
		self.smallTextField.setPlaceholderText("Enter small text...")
		self.smallTextField.setFixedHeight(50)

		smallTextLayout.addWidget(self.enableSmallTextCheckbox)
		smallTextLayout.addWidget(self.smallTextField)

		# Note field
		self.noteField = QTextEdit()
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
		mainLayout.addLayout(smallTextLayout)
		mainLayout.addWidget(QLabel("Note:"))
		mainLayout.addWidget(self.noteField)
		mainLayout.addLayout(buttonLayout)

		self.setLayout(mainLayout)

	def _toggleSmallTextField(self, state: int):
		"""Enable or disable the small text field based on the checkbox state."""
		self.smallTextField.setVisible(state == Qt.CheckState.Checked.value)

	def saveChanges(self):
		"""Save changes made in the editor."""
		smallText = self.smallTextField.toPlainText() if self.enableSmallTextCheckbox.isChecked() else None
		noteText = self.noteField.toHtml()  # Retrieve HTML-formatted text
		return {"smallText": smallText, "noteText": noteText}