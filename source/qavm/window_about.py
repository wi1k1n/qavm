from PyQt6.QtWidgets import (
	QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QDialogButtonBox,
    
)
from PyQt6.QtGui import (
	QIcon, 
)
from PyQt6.QtCore import (
	Qt, 
)

from qavm.qavm_version import (
    GetQAVMVersionVariant, GetPackageVersion, GetBuildVersion, 
)

class AboutDialog(QDialog):
    def __init__(self, parent, pluginManager):
        super().__init__(parent)
        self.pluginManager = pluginManager
        self.setWindowTitle("About QAVM")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        mainLayout = QVBoxLayout(self)

        # === Top section: Icon + version info ===
        topLayout = QHBoxLayout()

        # App icon
        icon = QIcon("res/qavm_icon.png")  # Replace with your icon path or Qt resource
        pixmap = icon.pixmap(64, 64)
        iconLabel = QLabel()
        iconLabel.setPixmap(pixmap)
        iconLabel.setAlignment(Qt.AlignmentFlag.AlignTop)
        topLayout.addWidget(iconLabel)

        # Version info
        versionInfo = (
            f"<b>QAVM {GetQAVMVersionVariant()}</b><br>"
            f"Package: {GetPackageVersion()}<br>"
            f"Build: {GetBuildVersion()}<br><br>"
        )
        versionLabel = QLabel(versionInfo)
        versionLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        versionLabel.setTextFormat(Qt.TextFormat.RichText)
        versionLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        topLayout.addWidget(versionLabel)

        topLayout.addStretch()
        mainLayout.addLayout(topLayout)

        # === Scrollable plugin section ===
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        pluginContainer = QWidget()
        pluginLayout = QVBoxLayout(pluginContainer)

        for plugin in self.pluginManager.GetPlugins():
            pluginVersion: str = plugin.GetVersionStr()
            pluginVariant: str = plugin.GetPluginVariant()
            if pluginVariant:
                pluginVersion += f" ({pluginVariant})"
            pluginText = (
                f"<b>Plugin:</b> {plugin.GetName()}"
                f"<br><b>Version:</b> {pluginVersion}"
                f"<br><b>UID:</b> {plugin.GetUID()}"
                f"<br><b>Executable:</b> <code>{plugin.GetExecutablePath()}</code>"
                f"<br><b>Developer:</b> {plugin.GetPluginDeveloper()}"
                f"<br><b>Website:</b> <a href='{plugin.GetPluginWebsite()}'>{plugin.GetPluginWebsite()}</a>"
            )
            pluginLabel = QLabel()
            pluginLabel.setTextFormat(Qt.TextFormat.RichText)
            pluginLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            pluginLabel.setOpenExternalLinks(True)
            pluginLabel.setWordWrap(True)
            pluginLabel.setText(pluginText)
            pluginLayout.addWidget(pluginLabel)

        scrollArea.setWidget(pluginContainer)
        mainLayout.addWidget(scrollArea)

        # === OK Button ===
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttonBox.accepted.connect(self.accept)
        mainLayout.addWidget(buttonBox)