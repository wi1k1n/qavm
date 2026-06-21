from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from PyQt6.QtCore import QObject, QThread, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from qavm.manager_plugin import PluginManager, QAVMPlugin
from qavm.manager_settings import QAVMGlobalSettings
from qavm.qavm_version import GetQAVMVersion

import qavm.logs as logs
logger = logs.logger

# QAVM core update source (GitHub releases of wi1k1n/qavm).
GITHUB_OWNER: str = 'wi1k1n'
GITHUB_REPO: str = 'qavm'

WEEKLY_INTERVAL: timedelta = timedelta(days=7)

# Sentinel stored in 'update_check_snooze_until' meaning "remind me again on the next startup".
SNOOZE_SENTINEL_STARTUP: str = 'startup'


@dataclass(frozen=True)
class CoreUpdateInfo:
	""" Information about an available QAVM core update. """
	current_version: str
	latest_version: str
	tag_name: str
	name: str
	html_url: str
	body: str


@dataclass(frozen=True)
class PluginUpdateInfo:
	""" Information about an available plugin update, as reported by a plugin's CheckForUpdates(). """
	plugin_uid: str
	plugin_name: str
	current_version: str
	latest_version: str
	download_url: str
	title: str
	message: str
	changelog: str


@dataclass
class UpdateReport:
	""" Aggregated result of an update check: an optional core update plus zero or more plugin updates. """
	core: CoreUpdateInfo | None = None
	plugins: list[PluginUpdateInfo] = field(default_factory=list)

	def HasUpdates(self) -> bool:
		return self.core is not None or len(self.plugins) > 0


def NormalizeVersion(value: str) -> str:
	""" Strips common GitHub tag decorations (whitespace, leading 'v', 'releases/') from a version string. """
	value = (value or '').strip()
	if value.lower().startswith('releases/'):
		value = value[len('releases/'):]
	if value[:1] in ('v', 'V'):
		value = value[1:]
	return value


def ParseVersion(version: str) -> tuple[int, int, int] | None:
	""" Parses a 'major.minor.patch' version string into a comparable tuple, or None if it isn't numeric. """
	parts: list[str] = NormalizeVersion(version).split('.')
	try:
		nums: list[int] = [int(p) for p in parts[:3]]
	except ValueError:
		return None
	while len(nums) < 3:
		nums.append(0)
	return (nums[0], nums[1], nums[2])


def IsNewerVersion(candidate: str, baseline: str) -> bool:
	""" Returns True if candidate is a strictly newer numeric version than baseline. """
	c = ParseVersion(candidate)
	b = ParseVersion(baseline)
	if c is None or b is None:
		return False
	return c > b


def ComputeUpdateSignature(report: UpdateReport) -> str:
	"""
	Builds a stable signature of all versions found in the report.
	Used by the "Skip this update" action: if any version changes later, the signature differs
	and the update is no longer considered skipped.
	"""
	parts: list[str] = []
	if report.core is not None:
		parts.append(f'core={NormalizeVersion(report.core.latest_version)}')
	for plugin in sorted(report.plugins, key=lambda p: p.plugin_uid):
		parts.append(f'{plugin.plugin_uid}={NormalizeVersion(plugin.latest_version)}')
	return ';'.join(parts)


class _PluginCheckWorker(QObject):
	""" Runs every loaded plugin's optional CheckForUpdates() on a background thread. """
	finished = pyqtSignal(list)  # list[PluginUpdateInfo]

	def __init__(self, plugins: list[QAVMPlugin]) -> None:
		super().__init__()
		self._plugins = plugins

	def Run(self) -> None:
		results: list[PluginUpdateInfo] = []
		for plugin in self._plugins:
			try:
				func = getattr(plugin.module, 'CheckForUpdates', None)
				if not callable(func):
					continue
				data = func()
				if not isinstance(data, dict):
					logger.warning(f'Plugin {plugin.GetUID()} CheckForUpdates() returned non-dict: {type(data)}')
					continue
				if not data.get('update_available'):
					continue
				results.append(PluginUpdateInfo(
					plugin_uid=plugin.GetUID(),
					plugin_name=plugin.GetName(),
					current_version=plugin.GetVersionStr(),
					latest_version=str(data.get('latest_version', '')),
					download_url=str(data.get('download_url', '')),
					title=str(data.get('update_title', '')),
					message=str(data.get('update_message', '')),
					changelog=str(data.get('changelog', '')),
				))
			except Exception:
				logger.exception(f'Plugin {plugin.GetUID()} CheckForUpdates() raised an exception')
		self.finished.emit(results)


class UpdateManager(QObject):
	"""
	Coordinates QAVM core and plugin update checks.

	- Core check: asynchronous GitHub releases request (does not block the UI).
	- Plugin check: each plugin's CheckForUpdates() runs on a background thread.
	Once both complete, the results are aggregated and the appropriate signal is emitted.
	"""
	showUpdatePopup = pyqtSignal(object)  # UpdateReport — emitted only when the popup should be shown
	noUpdatesFound = pyqtSignal()         # emitted for manual checks when everything is up to date
	checkFailed = pyqtSignal(str)         # emitted for manual checks when the core check fails

	def __init__(self, pluginManager: PluginManager, qavmSettings: QAVMGlobalSettings, parent: QObject | None = None) -> None:
		super().__init__(parent)
		self._pluginManager = pluginManager
		self._settings = qavmSettings

		self._network = QNetworkAccessManager(self)
		self._network.finished.connect(self._onCoreReplyFinished)

		self._running: bool = False
		self._manual: bool = False
		self._coreDone: bool = False
		self._pluginsDone: bool = False
		self._coreResult: CoreUpdateInfo | None = None
		self._pluginResults: list[PluginUpdateInfo] = []
		self._coreError: str = ''

		self._pluginThread: QThread | None = None
		self._pluginWorker: _PluginCheckWorker | None = None

	# ----------------------------- Public API -----------------------------
	def CheckNow(self, *, force: bool = False, manual: bool = False) -> None:
		""" Starts an update check. When not forced, respects the configured interval. """
		if self._running:
			logger.debug('Update check already running; ignoring new request')
			return

		if not force and not self._isAutoCheckDue():
			return

		self._running = True
		self._manual = manual
		self._coreDone = False
		self._pluginsDone = False
		self._coreResult = None
		self._pluginResults = []
		self._coreError = ''

		self._startCoreCheck()
		self._startPluginCheck()

	# ----------------------------- Gating -----------------------------
	def _isAutoCheckDue(self) -> bool:
		interval: str = self._settings.GetUpdateCheckInterval()
		if interval == 'never':
			return False
		if interval == 'startup':
			return True
		if interval == 'weekly':
			lastStr: str = self._settings.GetUpdateCheckLastTime()
			if not lastStr:
				return True
			try:
				last = datetime.fromisoformat(lastStr)
			except ValueError:
				return True
			return datetime.now(timezone.utc) - last >= WEEKLY_INTERVAL
		return True

	# ----------------------------- Core check -----------------------------
	def _startCoreCheck(self) -> None:
		url = QUrl(f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest')
		request = QNetworkRequest(url)
		request.setRawHeader(b'Accept', b'application/vnd.github+json')
		request.setRawHeader(b'X-GitHub-Api-Version', b'2022-11-28')
		request.setRawHeader(b'User-Agent', b'QAVM-UpdateChecker')
		self._network.get(request)

	def _onCoreReplyFinished(self, reply: QNetworkReply) -> None:
		try:
			self._coreResult, self._coreError = self._parseCoreReply(reply)
		finally:
			reply.deleteLater()
			self._coreDone = True
			self._tryFinalize()

	def _parseCoreReply(self, reply: QNetworkReply) -> tuple[CoreUpdateInfo | None, str]:
		statusCode = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)

		if reply.error() != QNetworkReply.NetworkError.NoError:
			return None, reply.errorString()
		if statusCode == 404:
			return None, 'No GitHub releases found for this repository.'
		if statusCode != 200:
			return None, f'GitHub returned HTTP {statusCode}.'

		try:
			data = json.loads(bytes(reply.readAll()).decode('utf-8'))
		except Exception as e:
			return None, f'Could not parse GitHub response: {e}'

		tagName: str = data.get('tag_name', '')
		latestVersion: str = NormalizeVersion(tagName)
		if not latestVersion:
			return None, f'Release tag is not a valid version: {tagName!r}'

		currentVersion: str = GetQAVMVersion()
		if not IsNewerVersion(latestVersion, currentVersion):
			return None, ''  # up to date, not an error

		return CoreUpdateInfo(
			current_version=currentVersion,
			latest_version=latestVersion,
			tag_name=tagName,
			name=data.get('name') or tagName,
			html_url=data.get('html_url', ''),
			body=data.get('body', ''),
		), ''

	# ----------------------------- Plugin check -----------------------------
	def _startPluginCheck(self) -> None:
		plugins: list[QAVMPlugin] = self._pluginManager.GetPlugins()

		self._pluginThread = QThread(self)
		self._pluginWorker = _PluginCheckWorker(plugins)
		self._pluginWorker.moveToThread(self._pluginThread)

		self._pluginThread.started.connect(self._pluginWorker.Run)
		self._pluginWorker.finished.connect(self._onPluginCheckFinished)
		self._pluginWorker.finished.connect(self._pluginThread.quit)
		self._pluginThread.finished.connect(self._pluginWorker.deleteLater)

		self._pluginThread.start()

	def _onPluginCheckFinished(self, results: list) -> None:
		self._pluginResults = results
		self._pluginsDone = True
		self._tryFinalize()

	# ----------------------------- Finalize -----------------------------
	def _tryFinalize(self) -> None:
		if not (self._coreDone and self._pluginsDone):
			return

		self._running = False

		# Record the time of this completed check (used for weekly throttling).
		self._settings.SetUpdateCheckLastTime(datetime.now(timezone.utc).isoformat())
		self._settings.Save()

		report = UpdateReport(core=self._coreResult, plugins=list(self._pluginResults))

		if not report.HasUpdates():
			if self._coreError and self._manual:
				self.checkFailed.emit(self._coreError)
			elif self._coreError:
				logger.warning(f'Update check failed: {self._coreError}')
			elif self._manual:
				self.noUpdatesFound.emit()
			return

		if self._manual:
			self.showUpdatePopup.emit(report)
			return

		# Automatic check: honor snooze and skip suppression.
		if self._isSnoozed():
			return
		if self._isSkipped(report):
			return
		self.showUpdatePopup.emit(report)

	def _isSnoozed(self) -> bool:
		value: str = self._settings.GetUpdateCheckSnoozeUntil()
		if not value:
			return False
		if value == SNOOZE_SENTINEL_STARTUP:
			# "Next startup" snooze is consumed at this startup, so the popup may show again.
			self._settings.SetUpdateCheckSnoozeUntil('')
			self._settings.Save()
			return False
		try:
			until = datetime.fromisoformat(value)
		except ValueError:
			return False
		return datetime.now(timezone.utc) < until

	def _isSkipped(self, report: UpdateReport) -> bool:
		signature: str = ComputeUpdateSignature(report)
		return bool(signature) and signature == self._settings.GetUpdateCheckSkipSignature()
