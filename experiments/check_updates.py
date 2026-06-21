from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from packaging.version import Version, InvalidVersion

from PyQt6.QtCore import QObject, pyqtSignal, QUrl, QSettings
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.QtGui import QDesktopServices


APP_VERSION = "1.2.0"


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag_name: str
    name: str
    html_url: str
    body: str


class UpdateChecker(QObject):
    update_available = pyqtSignal(object)   # ReleaseInfo
    no_update_available = pyqtSignal()
    check_failed = pyqtSignal(str)

    def __init__(
        self,
        *,
        owner: str,
        repo: str,
        current_version: str,
        parent: QObject | None = None,
        check_interval_hours: int = 24,
    ):
        super().__init__(parent)

        self.owner = owner
        self.repo = repo
        self.current_version = current_version
        self.check_interval = timedelta(hours=check_interval_hours)

        self._network = QNetworkAccessManager(self)
        self._network.finished.connect(self._on_reply_finished)

        self._settings = QSettings("YourCompany", "YourApp")

    def check_now(self, *, force: bool = False) -> None:
        if not force and not self._should_check_now():
            return

        url = QUrl(
            f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"
        )

        request = QNetworkRequest(url)
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"X-GitHub-Api-Version", b"2022-11-28")
        request.setRawHeader(b"User-Agent", b"YourApp-UpdateChecker")

        self._network.get(request)

    def _should_check_now(self) -> bool:
        value = self._settings.value("updates/last_check_utc", "", str)

        if not value:
            return True

        try:
            last_check = datetime.fromisoformat(value)
        except ValueError:
            return True

        return datetime.now(timezone.utc) - last_check >= self.check_interval

    def _store_check_time(self) -> None:
        self._settings.setValue(
            "updates/last_check_utc",
            datetime.now(timezone.utc).isoformat(),
        )

    def _on_reply_finished(self, reply: QNetworkReply) -> None:
        self._store_check_time()

        status_code = reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute
        )

        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.check_failed.emit(reply.errorString())
            reply.deleteLater()
            return

        if status_code == 404:
            self.check_failed.emit("No GitHub releases found for this repository.")
            reply.deleteLater()
            return

        if status_code != 200:
            self.check_failed.emit(f"GitHub returned HTTP {status_code}.")
            reply.deleteLater()
            return

        import json

        try:
            data = json.loads(bytes(reply.readAll()).decode("utf-8"))
        except Exception as e:
            self.check_failed.emit(f"Could not parse GitHub response: {e}")
            reply.deleteLater()
            return

        tag_name = data.get("tag_name", "")
        remote_version = self._normalize_version(tag_name)

        if not remote_version:
            self.check_failed.emit(f"Release tag is not a valid version: {tag_name!r}")
            reply.deleteLater()
            return

        try:
            current = Version(self._normalize_version(self.current_version))
            remote = Version(remote_version)
        except InvalidVersion as e:
            self.check_failed.emit(f"Invalid version format: {e}")
            reply.deleteLater()
            return

        if remote > current:
            self.update_available.emit(
                ReleaseInfo(
                    version=remote_version,
                    tag_name=tag_name,
                    name=data.get("name") or tag_name,
                    html_url=data.get("html_url", ""),
                    body=data.get("body", ""),
                )
            )
        else:
            self.no_update_available.emit()

        reply.deleteLater()

    @staticmethod
    def _normalize_version(value: str) -> str:
        value = value.strip()

        # Common GitHub release tags: v1.2.3, V1.2.3
        if value.lower().startswith("releases/"):
            value = value[len("releases/"):]

        return value
    


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.update_checker = UpdateChecker(
            owner="wi1k1n",
            repo="qavm",
            current_version=APP_VERSION,
            parent=self,
        )

        self.update_checker.update_available.connect(self.on_update_available)
        self.update_checker.check_failed.connect(self.on_update_check_failed)

        # Automatic background check, max once per 24h.
        self.update_checker.check_now()

    def on_update_available(self, release: ReleaseInfo) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("Update available")
        msg.setIcon(QMessageBox.Icon.Information)

        msg.setText(
            f"A new version is available: {release.tag_name}\n\n"
            f"Current version: {APP_VERSION}"
        )

        msg.setInformativeText("Open the release page?")
        msg.setStandardButtons(
            QMessageBox.StandardButton.Open |
            QMessageBox.StandardButton.Cancel
        )

        result = msg.exec()

        if result == QMessageBox.StandardButton.Open:
            QDesktopServices.openUrl(QUrl(release.html_url))

    def on_update_check_failed(self, error: str) -> None:
        # For automatic checks, usually do not annoy the user.
        # Log it instead.
        print(f"Update check failed: {error}")

    def manual_check_for_updates(self) -> None:
        # Connect this to Help -> Check for Updates
        self.update_checker.check_now(force=True)
        
if __name__ == "__main__":
	import sys
	from PyQt6.QtWidgets import QApplication

	app = QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec())