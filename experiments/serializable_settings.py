import json, sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QDialog, QLabel, QLineEdit, QFormLayout, QDialogButtonBox

class SettingsModel:
    def __init__(self):
        self.settings = self.load_settings()

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_settings(self):
        with open('settings.json', 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.presenter = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Settings")

        self.layout = QFormLayout()

        self.username_field = QLineEdit()
        self.layout.addRow("Username:", self.username_field)
        
        self.api_key_field = QLineEdit()
        self.layout.addRow("API Key:", self.api_key_field)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)

    def load_settings(self):
        self.username_field.setText(self.presenter.get_setting("username", ""))
        self.api_key_field.setText(self.presenter.get_setting("api_key", ""))

    def accept(self):
        self.presenter.set_setting("username", self.username_field.text())
        self.presenter.set_setting("api_key", self.api_key_field.text())
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.presenter = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Main Window")

        self.central_widget = QWidget()
        self.layout = QVBoxLayout()

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.show_settings_dialog)
        self.layout.addWidget(self.settings_button)

        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

    def show_settings_dialog(self):
        self.presenter.show_settings_dialog()

class MainPresenter:
    def __init__(self, model, main_view, settings_view):
        self.model = model
        self.main_view = main_view
        self.settings_view = settings_view

    def get_setting(self, key, default=None):
        return self.model.get_setting(key, default)

    def set_setting(self, key, value):
        self.model.set_setting(key, value)
        self.model.save_settings()

    def show_settings_dialog(self):
        self.settings_view.load_settings()
        self.settings_view.exec()

def main():
    app = QApplication(sys.argv)

    model = SettingsModel()
    main_view = MainWindow()
    settings_view = SettingsDialog()

    presenter = MainPresenter(model, main_view, settings_view)
    
    main_view.presenter = presenter
    settings_view.presenter = presenter

    main_view.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
