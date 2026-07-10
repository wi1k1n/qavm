""" Data migration manager.

QAVM stores its regular (app) data in a per-version subfolder of <appdata>/qavm/ and each plugin's data in
its own per-plugin-version subtree under <appdata>/qavm/plugins/<pluginID>/<pluginVersion>/. This manager
is responsible for figuring out, on startup, whether the data folder for the current version already exists
and, if not, what to do about it:

  * Patch bumps (same major.minor, different patch): silently carry over the data from the nearest
    patch-compatible sibling version. No prompt, no migration event.

  * Minor/major bumps (or the legacy pre-0.4.0 "qamv" layout): treated as a migration event. The user is
    prompted and offered to either start with fresh settings (recommended), copy the previous data (both
    QAVM's and the plugins') so it is used with the new version, or quit. The previous data is always left
    untouched regardless of the choice.

For 0.4.0 the migration event copies the previous data verbatim when requested (no automatic data transform);
the per-settings transform hook (BaseSettings.MigrateSettings) is in place for future cross-version upgrades.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
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
		self.migrationChoice: str | None = None  # 'fresh' | 'copy', set at the migration prompt (drives plugin data too)

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

		# 2) Prior data from a different minor/major or the legacy layout -> migration event (prompt).
		prior: tuple[str, Path] | None = self._detectPriorData()
		if prior is not None:
			label, sourcePath = prior
			choice: str = self._promptMigration(label, sourcePath)
			if choice == 'quit':
				logger.info('User aborted startup at the data migration prompt.')
				raise SystemExit(0)
			self.migrationChoice = choice  # remembered so plugin data follows the same fresh/copy decision
			if choice == 'copy':
				logger.info(f'Copying data from "{label}" -> "{self.currentVersion}".')
				self._copyTree(sourcePath, self.currentVersionPath)
				self._writeManifest(self.currentVersionPath, self.currentVersion, kind='copy', migratedFrom=label)
			else:  # 'fresh'
				self._writeManifest(self.currentVersionPath, self.currentVersion, kind='fresh-after-migration', migratedFrom=label)
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
		""" Ensures a plugin's versioned data folder exists on its first launch. By default it silently carries
		over data from the nearest patch-compatible sibling version of the SAME plugin. During a migration event
		the user's choice is honoured: 'fresh' starts the plugin clean, 'copy' carries over the nearest sibling
		of any version. Safe to call repeatedly. """
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
		sibling: Path | None = None
		if self.migrationChoice != 'fresh':
			sibling = self._findNearestPluginSibling(pluginRoot, pluginVersion, acrossMinor=(self.migrationChoice == 'copy'))
		if sibling is not None:
			logger.info(f'Carrying over plugin "{pluginID}" data "{sibling.name}" -> "{pluginVersion}".')
			self._copyTree(sibling, targetPath)
		else:
			targetPath.mkdir(parents=True, exist_ok=True)
		self._writeManifest(targetPath, pluginVersion, kind=('copy' if sibling else 'fresh'),
							 migratedFrom=(sibling.name if sibling else None), pluginID=pluginID)

	def _findNearestPluginSibling(self, pluginRoot: Path, pluginVersion: str, acrossMinor: bool = False) -> Path | None:
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
			if acrossMinor or (parsed[0] == current[0] and parsed[1] == current[1]):
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

	def _promptMigration(self, label: str, sourcePath: Path) -> str:
		""" Shows the migration prompt. Returns 'fresh', 'copy' or 'quit'. """
		box: QMessageBox = QMessageBox()
		box.setIcon(QMessageBox.Icon.Information)
		box.setWindowTitle('QAVM data migration')
		box.setText(f'A new QAVM version ({self.currentVersion}) is starting for the first time.')
		box.setInformativeText(
			f'Existing data from a previous version ({label}) was found at:\n{sourcePath}\n\n'
			f'You can start QAVM {self.currentVersion} with fresh settings (recommended), or copy the previous '
			f'data (both QAVM\'s and the plugins\') so it is used with the new version. Your previous data is left '
			f'untouched either way.'
		)
		# Make the shown path selectable so it can be copied.
		box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
		freshBtn = box.addButton('Start fresh (Recommended)', QMessageBox.ButtonRole.AcceptRole)
		copyBtn = box.addButton('Copy previous data', QMessageBox.ButtonRole.ActionRole)
		quitBtn = box.addButton('Quit', QMessageBox.ButtonRole.RejectRole)
		box.setDefaultButton(freshBtn)
		box.exec()
		clicked = box.clickedButton()
		if clicked is quitBtn:
			return 'quit'
		if clicked is copyBtn:
			return 'copy'
		return 'fresh'

	def _writeManifest(self, versionPath: Path, version: str, kind: str,
					   migratedFrom: str | None = None, pluginID: str | None = None) -> None:
		try:
			versionPath.mkdir(parents=True, exist_ok=True)
			manifest: dict = {
				'version': version,
				'app_version': self.currentVersion,
				'created': datetime.now().isoformat(timespec='seconds'),
				'kind': kind,
				'migrated_from': migratedFrom,
			}
			if pluginID is not None:
				manifest['plugin_id'] = pluginID
			with open(versionPath / MANIFEST_FILENAME, 'w') as f:
				json.dump(manifest, f, indent='\t')
		except Exception:
			logger.exception(f'Failed to write QAVM data manifest at {versionPath}.')
