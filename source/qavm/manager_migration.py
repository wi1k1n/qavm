""" Data migration & backup manager.

QAVM stores its regular (app) data in a per-version subfolder of <appdata>/qavm/ and each plugin's data in
its own per-plugin-version subtree under <appdata>/qavm/plugins/<pluginID>/<pluginVersion>/. This manager
is responsible for figuring out, on startup, whether the data folder for the current version already exists
and, if not, what to do about it:

  * Patch bumps (same major.minor, different patch): silently carry over the data from the nearest
    patch-compatible sibling version. No prompt, no migration event.

  * Minor/major bumps (or the legacy pre-0.4.0 "qamv" layout): treated as a migration event. The user is
    prompted and offered to create a timestamped backup of the previous data before QAVM starts fresh. The
    previous data is always left untouched so users can roll back manually if anything goes wrong.

For 0.4.0 the migration event only performs detection + backup + fresh start (no automatic data transform);
the per-settings transform hook (BaseSettings.MigrateSettings) is in place for future cross-version upgrades.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

import qavm.qavmapi.utils as utils
from qavm.qavm_version import GetQAVMVersion

import qavm.logs as logs
logger = logs.logger

MANIFEST_FILENAME: str = '.qavm_manifest.json'
LEGACY_DATA_FOLDERNAME: str = 'qamv'  # pre-0.4.0 (typo) data root, kept around for manual rollback
RESERVED_ROOT_SUBFOLDERS: set[str] = {'plugins', 'logs'}  # non-version subfolders of the data root


def _ParseVersion(version: str) -> tuple[int, int, int] | None:
	""" Parses a 'major.minor.patch' version string into a comparable tuple, or None if it isn't numeric. """
	parts: list[str] = version.split('.')
	try:
		nums: list[int] = [int(p) for p in parts[:3]]
	except ValueError:
		return None
	while len(nums) < 3:
		nums.append(0)
	return (nums[0], nums[1], nums[2])


class MigrationManager:
	def __init__(self) -> None:
		self.dataRootPath: Path = utils.GetQAVMDataRootPath(create=False)
		self.currentVersion: str = GetQAVMVersion()
		self.currentVersionPath: Path = self.dataRootPath / self.currentVersion

	####################### Regular (app) data #######################

	def CheckAndPrompt(self) -> None:
		""" Entry point invoked once at startup, before any versioned data folder is written to. """
		try:
			self._checkAndPrompt()
		except SystemExit:
			raise
		except Exception:
			logger.exception('Data migration check failed; continuing with a clean state.')

	def _checkAndPrompt(self) -> None:
		if self._isInitialized(self.currentVersionPath):
			logger.info(f'QAVM data for version {self.currentVersion} already initialized.')
			return

		# First launch for this version.
		utils.GetQAVMDataRootPath(create=True)  # make sure the root exists

		# 1) Silent patch-copy from the nearest same-major.minor sibling (no prompt, no migration event).
		sibling: Path | None = self._findNearestPatchSibling()
		if sibling is not None:
			logger.info(f'Carrying over data from patch-compatible version "{sibling.name}" -> "{self.currentVersion}".')
			self._copyTree(sibling, self.currentVersionPath)
			self._writeManifest(self.currentVersionPath, self.currentVersion, kind='patch-copy', migratedFrom=sibling.name)
			return

		# 2) Prior data from a different minor/major or the legacy layout -> migration event (prompt + backup).
		prior: tuple[str, Path] | None = self._detectPriorData()
		if prior is not None:
			label, sourcePath = prior
			backedUp: bool = False
			choice: str = self._promptBackup(label, sourcePath)
			if choice == 'quit':
				logger.info('User aborted startup at the data migration prompt.')
				raise SystemExit(0)
			if choice == 'backup':
				backedUp = self._backup(label, sourcePath) is not None
			# 0.4.0 scope: start fresh after backup (no automatic data transform yet).
			self._writeManifest(self.currentVersionPath, self.currentVersion, kind='fresh-after-backup', migratedFrom=label, backedUp=backedUp)
			return

		# 3) Genuine fresh install.
		logger.info('No previous QAVM data found; starting fresh.')
		self._writeManifest(self.currentVersionPath, self.currentVersion, kind='fresh')

	def _listVersionSiblings(self) -> list[tuple[tuple[int, int, int], Path]]:
		""" Returns the initialized, version-named sibling folders of the current version (excluding it). """
		result: list[tuple[tuple[int, int, int], Path]] = []
		if not self.dataRootPath.is_dir():
			return result
		for child in self.dataRootPath.iterdir():
			if not child.is_dir() or child.name == self.currentVersion or child.name in RESERVED_ROOT_SUBFOLDERS:
				continue
			parsed: tuple[int, int, int] | None = _ParseVersion(child.name)
			if parsed is None or not self._isInitialized(child):
				continue
			result.append((parsed, child))
		return result

	def _findNearestPatchSibling(self) -> Path | None:
		""" Among same-major.minor siblings, returns the highest-patch one (most recent compatible data). """
		current: tuple[int, int, int] | None = _ParseVersion(self.currentVersion)
		if current is None:
			return None
		sameMinor: list[tuple[tuple[int, int, int], Path]] = [
			(v, p) for (v, p) in self._listVersionSiblings() if v[0] == current[0] and v[1] == current[1]
		]
		if not sameMinor:
			return None
		sameMinor.sort(key=lambda vp: vp[0])
		return sameMinor[-1][1]

	def _detectPriorData(self) -> tuple[str, Path] | None:
		""" Detects previous data that warrants a migration event, returning (humanLabel, sourcePath). """
		current: tuple[int, int, int] | None = _ParseVersion(self.currentVersion)
		# Prefer a versioned sibling from a different minor/major (future cross-minor upgrades).
		crossMinor: list[tuple[tuple[int, int, int], Path]] = [
			(v, p) for (v, p) in self._listVersionSiblings()
			if current is None or (v[0], v[1]) != (current[0], current[1])
		]
		if crossMinor:
			crossMinor.sort(key=lambda vp: vp[0])
			_, path = crossMinor[-1]
			return (f'QAVM {path.name}', path)
		# Legacy pre-0.4.0 data root (the old "qamv" typo folder).
		legacyPath: Path = utils.GetAppDataPath() / LEGACY_DATA_FOLDERNAME
		if legacyPath.is_dir() and any(legacyPath.iterdir()):
			return ('QAVM 0.3.x', legacyPath)
		return None

	####################### Per-plugin data #######################

	def EnsurePluginData(self, pluginID: str, pluginVersion: str) -> None:
		""" Ensures a plugin's versioned data folder exists, silently carrying over data from the nearest
		patch-compatible sibling version of the SAME plugin on its first launch. Safe to call repeatedly. """
		try:
			self._ensurePluginData(pluginID, pluginVersion)
		except Exception:
			logger.exception(f'Plugin data migration check failed for plugin "{pluginID}" v{pluginVersion}.')

	def _ensurePluginData(self, pluginID: str, pluginVersion: str) -> None:
		if not pluginID or not pluginVersion:
			return
		pluginRoot: Path = utils.GetQAVMDataRootPath(create=False) / 'plugins' / pluginID
		targetPath: Path = pluginRoot / pluginVersion
		if self._isInitialized(targetPath):
			return
		sibling: Path | None = self._findNearestPluginPatchSibling(pluginRoot, pluginVersion)
		if sibling is not None:
			logger.info(f'Carrying over plugin "{pluginID}" data "{sibling.name}" -> "{pluginVersion}".')
			self._copyTree(sibling, targetPath)
		else:
			targetPath.mkdir(parents=True, exist_ok=True)
		self._writeManifest(targetPath, pluginVersion, kind=('patch-copy' if sibling else 'fresh'),
							 migratedFrom=(sibling.name if sibling else None), pluginID=pluginID)

	def _findNearestPluginPatchSibling(self, pluginRoot: Path, pluginVersion: str) -> Path | None:
		current: tuple[int, int, int] | None = _ParseVersion(pluginVersion)
		if current is None or not pluginRoot.is_dir():
			return None
		candidates: list[tuple[tuple[int, int, int], Path]] = []
		for child in pluginRoot.iterdir():
			if not child.is_dir() or child.name == pluginVersion:
				continue
			parsed: tuple[int, int, int] | None = _ParseVersion(child.name)
			if parsed is None or not self._isInitialized(child):
				continue
			if parsed[0] == current[0] and parsed[1] == current[1]:
				candidates.append((parsed, child))
		if not candidates:
			return None
		candidates.sort(key=lambda vp: vp[0])
		return candidates[-1][1]

	####################### Helpers #######################

	def _isInitialized(self, versionPath: Path) -> bool:
		return (versionPath / MANIFEST_FILENAME).is_file()

	def _copyTree(self, src: Path, dst: Path) -> None:
		dst.mkdir(parents=True, exist_ok=True)
		shutil.copytree(src, dst, dirs_exist_ok=True)

	def _promptBackup(self, label: str, sourcePath: Path) -> str:
		""" Shows the migration prompt. Returns 'backup', 'continue' or 'quit'. """
		box: QMessageBox = QMessageBox()
		box.setIcon(QMessageBox.Icon.Information)
		box.setWindowTitle('QAVM data migration')
		box.setText(f'A new QAVM version ({self.currentVersion}) is starting for the first time.')
		box.setInformativeText(
			f'Existing data from a previous version ({label}) was found at:\n{sourcePath}\n\n'
			f'QAVM {self.currentVersion} will start with fresh settings. Your previous data is left untouched, '
			f'but you can also create a separate timestamped backup now so you can roll back manually if needed.'
		)
		backupBtn = box.addButton('Back up && continue', QMessageBox.ButtonRole.AcceptRole)
		box.addButton('Continue without backup', QMessageBox.ButtonRole.DestructiveRole)
		quitBtn = box.addButton('Quit', QMessageBox.ButtonRole.RejectRole)
		box.setDefaultButton(backupBtn)
		box.exec()
		clicked = box.clickedButton()
		if clicked is quitBtn:
			return 'quit'
		if clicked is backupBtn:
			return 'backup'
		return 'continue'

	def _backup(self, label: str, sourcePath: Path) -> Path | None:
		""" Creates a timestamped copy of `sourcePath` next to it. Returns the backup path or None on failure. """
		try:
			timestamp: str = datetime.now().strftime('%Y%m%d-%H%M%S')
			versionTag: str = label.replace('QAVM', '').strip().replace(' ', '_') or 'prev'
			backupPath: Path = sourcePath.parent / f'{sourcePath.name}-backup-{versionTag}-{timestamp}'
			logger.info(f'Backing up "{sourcePath}" -> "{backupPath}".')
			self._copyTree(sourcePath, backupPath)
			return backupPath
		except Exception:
			logger.exception('Failed to create data backup.')
			return None

	def _writeManifest(self, versionPath: Path, version: str, kind: str,
					   migratedFrom: str | None = None, backedUp: bool = False, pluginID: str | None = None) -> None:
		try:
			versionPath.mkdir(parents=True, exist_ok=True)
			manifest: dict = {
				'version': version,
				'app_version': self.currentVersion,
				'created': datetime.now().isoformat(timespec='seconds'),
				'kind': kind,
				'migrated_from': migratedFrom,
				'backed_up': backedUp,
			}
			if pluginID is not None:
				manifest['plugin_id'] = pluginID
			with open(versionPath / MANIFEST_FILENAME, 'w') as f:
				json.dump(manifest, f, indent='\t')
		except Exception:
			logger.exception(f'Failed to write QAVM data manifest at {versionPath}.')
