from __future__ import annotations

from datetime import datetime, timedelta, timezone

import markdown

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
	QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QPushButton, QMenu, QFrame,
)

from qavm.manager_settings import QAVMGlobalSettings
from qavm.manager_update import (
	UpdateReport, CoreUpdateInfo, PluginUpdateInfo, ComputeUpdateSignature, SNOOZE_SENTINEL_STARTUP,
)
from qavm.qavm_version import GetQAVMVersionVariant

import qavm.logs as logs
logger = logs.logger


class UpdateAvailableDialog(QDialog):
	"""
	Popup shown when an application and/or plugin update is available.

	Buttons:
	  - Snooze (with submenu: next startup / next day / next week / next month) — suppresses the popup for a while.
	  - Skip this update — suppresses the popup until any of the found versions changes.
	  - Dismiss — closes without changing any state.
	"""
	def __init__(self, report: UpdateReport, qavmSettings: QAVMGlobalSettings, parent: QWidget | None = None) -> None:
		super().__init__(parent)
		self._report = report
		self._settings = qavmSettings

		self.setWindowTitle('QAVM - Update available')
		self.setMinimumSize(560, 380)
		self.setModal(True)

		mainLayout = QVBoxLayout(self)

		# === Header ===
		headerLayout = QHBoxLayout()
		icon = QIcon('res/qavm_icon.png')
		iconLabel = QLabel()
		iconLabel.setPixmap(icon.pixmap(48, 48))
		iconLabel.setAlignment(Qt.AlignmentFlag.AlignTop)
		headerLayout.addWidget(iconLabel)

		headerLabel = QLabel('<b>Updates are available</b>')
		headerLabel.setTextFormat(Qt.TextFormat.RichText)
		headerLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
		headerLayout.addWidget(headerLabel)
		headerLayout.addStretch()
		mainLayout.addLayout(headerLayout)

		# === Scrollable content ===
		scrollArea = QScrollArea()
		scrollArea.setWidgetResizable(True)
		container = QWidget()
		contentLayout = QVBoxLayout(container)

		if report.core is not None:
			contentLayout.addWidget(self._createCoreSection(report.core))

		if report.core is not None and report.plugins:
			contentLayout.addWidget(self._createSeparator())

		for pluginUpdate in report.plugins:
			contentLayout.addWidget(self._createPluginSection(pluginUpdate))

		contentLayout.addStretch()
		scrollArea.setWidget(container)
		mainLayout.addWidget(scrollArea)

		# === Buttons ===
		mainLayout.addLayout(self._createButtonBar())

	# ----------------------------- Sections -----------------------------
	def _createSeparator(self) -> QFrame:
		line = QFrame()
		line.setFrameShape(QFrame.Shape.HLine)
		line.setFrameShadow(QFrame.Shadow.Sunken)
		return line

	def _createCoreSection(self, core: CoreUpdateInfo) -> QLabel:
		text = (
			f"<b>QAVM</b><br>"
			f"Current version: {GetQAVMVersionVariant()}<br>"
			f"New version: <b>{core.latest_version}</b>"
		)
		if core.html_url:
			text += f"<br><a href='{core.html_url}'>Download / release page</a>"
		if core.body:
			text += f"<br><br><i>{markdown.markdown(core.body)}</i>"
		return self._createRichLabel(text)

	def _createPluginSection(self, plugin: PluginUpdateInfo) -> QLabel:
		title = f' - {plugin.title}' if plugin.title else ''
		text = f"[Plugin] <b>{plugin.plugin_name}</b>{title}<br>"
		if plugin.current_version or plugin.latest_version:
			text += f"Current version: {plugin.current_version or '?'}<br>"
			text += f"New version: <b>{plugin.latest_version or '?'}</b>"
		if plugin.download_url:
			text += f"<br><a href='{plugin.download_url}'>Download / more info</a>"
		if plugin.message:
			text += f"<br>{markdown.markdown(plugin.message)}"
		if plugin.changelog:
			text += f"<br><br><i>{markdown.markdown(plugin.changelog)}</i>"
		return self._createRichLabel(text)

	def _createRichLabel(self, text: str) -> QLabel:
		label = QLabel()
		label.setTextFormat(Qt.TextFormat.RichText)
		label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
		label.setOpenExternalLinks(True)
		label.setWordWrap(True)
		label.setText(text)
		return label

	# ----------------------------- Buttons -----------------------------
	def _createButtonBar(self) -> QHBoxLayout:
		buttonLayout = QHBoxLayout()

		snoozeButton = QPushButton('Snooze')
		snoozeMenu = QMenu(snoozeButton)
		snoozeMenu.addAction('Next startup', lambda: self._onSnooze(SNOOZE_SENTINEL_STARTUP))
		snoozeMenu.addAction('Next day', lambda: self._onSnooze(timedelta(days=1)))
		snoozeMenu.addAction('Next week', lambda: self._onSnooze(timedelta(days=7)))
		snoozeMenu.addAction('Next month', lambda: self._onSnooze(timedelta(days=30)))
		snoozeButton.setMenu(snoozeMenu)
		buttonLayout.addWidget(snoozeButton)

		skipButton = QPushButton('Skip this update')
		skipButton.clicked.connect(self._onSkip)
		buttonLayout.addWidget(skipButton)

		buttonLayout.addStretch()

		dismissButton = QPushButton('Dismiss')
		dismissButton.setDefault(True)
		dismissButton.clicked.connect(self.accept)
		buttonLayout.addWidget(dismissButton)

		return buttonLayout

	def _onSnooze(self, duration) -> None:
		if duration == SNOOZE_SENTINEL_STARTUP:
			self._settings.SetUpdateCheckSnoozeUntil(SNOOZE_SENTINEL_STARTUP)
		elif isinstance(duration, timedelta):
			until = datetime.now(timezone.utc) + duration
			self._settings.SetUpdateCheckSnoozeUntil(until.isoformat())
		self._settings.Save()
		self.accept()

	def _onSkip(self) -> None:
		self._settings.SetUpdateCheckSkipSignature(ComputeUpdateSignature(self._report))
		self._settings.Save()
		self.accept()
