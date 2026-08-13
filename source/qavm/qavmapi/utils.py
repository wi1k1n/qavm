import os, platform, json, hashlib, subprocess, sys
import zipfile, shutil, tempfile, ctypes
from pathlib import Path
from typing import Any, Optional

def PlatformWindows():
	return platform.system() == 'Windows'
def PlatformLinux():
	return platform.system() == 'Linux'
def PlatformMacOS():
	return platform.system() == 'Darwin'
def PlatformName() -> str:
	return platform.system().lower()

def IsDebug() -> bool:
	return os.environ.get('QAVM_DEV_MODE', '0') in ('1', 'true', 'True')

# === Detection Functions ===

def IsPathFile(path: Path) -> bool:
	return path.is_file() and not path.is_symlink()

def IsPathDir(path: Path) -> bool:
	isJunction = IsPathJunction(path) if PlatformWindows() else False
	return path.is_dir() and not path.is_symlink() and not isJunction

def IsPathSymlinkF(path: Path) -> bool:
	return path.is_symlink() and path.resolve().is_file()

def IsPathSymlinkD(path: Path) -> bool:
	return path.is_symlink() and path.resolve().is_dir()

def IsPathJunction(path: Path) -> bool:
	if not PlatformWindows():
		# raise NotImplementedError("Junctions are only supported on Windows.")
		return False
	if not path.is_dir() or not path.exists():
		return False
	FILE_ATTRIBUTE_REPARSE_POINT = 0x400
	attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
	return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT) and not path.is_symlink()

def IsPathShortcut(path: Path) -> bool:
	if not PlatformWindows():
		# raise NotImplementedError("Shortcuts are only supported on Windows.")
		return False
	return path.suffix.lower() == '.lnk' and path.is_file()

# === Target Retrieval Functions ===

def GetShortcutTarget(path: Path) -> Optional[Path]:
	if not PlatformWindows():
		raise NotImplementedError("Shortcuts are only supported on Windows.")
	if not IsPathShortcut(path):
		return None
	import win32com.client
	shell = win32com.client.Dispatch("WScript.Shell")
	shortcut = shell.CreateShortcut(str(path))
	return Path(shortcut.TargetPath)

def GetSymlinkFTarget(path: Path) -> Optional[Path]:
	return path.resolve() if IsPathSymlinkF(path) else None

def GetSymlinkDTarget(path: Path) -> Optional[Path]:
	return path.resolve() if IsPathSymlinkD(path) else None

def GetJunctionTarget(path: Path) -> Optional[Path]:
	if not PlatformWindows():
		raise NotImplementedError("Junctions are only supported on Windows.")
	return path.resolve() if IsPathJunction(path) else None

# === Creation Helpers ===

def _checkLinkExistsOverwriteMkdir(target: Path, link: Path, exist_overwrite: bool):
	if not target.exists():
		raise FileNotFoundError(target)
	if link.exists():
		if exist_overwrite:
			DeletePath(link)
		else:
			raise FileExistsError(link)
	link.parent.mkdir(parents=True, exist_ok=True)

# === Creation Functions ===

def CreateDir(path: Path, parents: bool = True, exist_ok: bool = True):
	path.mkdir(parents=parents, exist_ok=exist_ok)

def CreateShortcut(target: Path, link: Path, exist_overwrite: bool = False):
	if not PlatformWindows():
		raise NotImplementedError("Shortcuts are only supported on Windows.")
	_checkLinkExistsOverwriteMkdir(target, link, exist_overwrite)

	import win32com.client
	shell = win32com.client.Dispatch("WScript.Shell")
	shortcut = shell.CreateShortcut(str(link))
	shortcut.TargetPath = str(target)
	shortcut.Save()

def CreateSymlinkF(target: Path, link: Path, exist_overwrite: bool = False):
	_checkLinkExistsOverwriteMkdir(target, link, exist_overwrite)
	link.symlink_to(target)

def CreateSymlinkD(target: Path, link: Path, exist_overwrite: bool = False):
	_checkLinkExistsOverwriteMkdir(target, link, exist_overwrite)
	link.symlink_to(target, target_is_directory=True)

def CreateJunction(target: Path, link: Path, exist_overwrite: bool = False):
	if not PlatformWindows():
		raise NotImplementedError("Junctions are only supported on Windows.")
	_checkLinkExistsOverwriteMkdir(target, link, exist_overwrite)
	os.system(f'mklink /J "{link}" "{target}" >nul')

# === Deletion Functions ===

def DeletePath(path: Path):
	if IsPathDir(path):
		shutil.rmtree(path)
	else:
		path.unlink()

# === Copy Functions ===

def CopyPath(src: Path, dst: Path, exist_overwrite: bool = False):
	"""
	Copies the filesystem object at `src` to `dst`, preserving the object type.
	"""
	if not src.exists():
		raise FileNotFoundError(src)

	if dst.exists():
		if not exist_overwrite:
			raise FileExistsError(dst)
		DeletePath(dst)

	if IsPathDir(src):
		shutil.copytree(src, dst)

	elif IsPathSymlinkF(src):
		CreateSymlinkF(src.resolve(), dst, exist_overwrite=exist_overwrite)

	elif IsPathSymlinkD(src):
		CreateSymlinkD(src.resolve(), dst, exist_overwrite=exist_overwrite)

	elif PlatformWindows() and IsPathShortcut(src):
		CreateShortcut(GetShortcutTarget(src), dst, exist_overwrite=exist_overwrite)

	elif PlatformWindows() and IsPathJunction(src):
		CreateJunction(GetJunctionTarget(src), dst, exist_overwrite=exist_overwrite)

	elif IsPathFile(src):  # this should be the last check
		shutil.copy2(src, dst)

	else:
		raise ValueError(f"Unsupported or unknown path type: {src}")








# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================










def OpenFolderInExplorer(folderPath: Path):
	if PlatformWindows():
		os.startfile(folderPath)
	elif PlatformMacOS():
		subprocess.Popen(['open', folderPath])
	# elif PlatformLinux():
	# 	subprocess.Popen(['xdg-open', folderPath])
	else:
		raise Exception('Unsupported platform')

def RunCommandWindows(cmd: str) -> str:
	"""
	Launch cmd.exe and run `cmd`.
	cmd: string, e.g. 'dir C:\\Windows'
	"""
	if not PlatformWindows():
		raise Exception('This function is only supported on Windows')
	import subprocess
	params = f"/c {cmd}"
	result = subprocess.run(['cmd.exe', params], capture_output=True, text=True)
	if result.returncode != 0:
		raise RuntimeError(f"Command failed with error: {result.stderr}")
	return result.stdout

def RunCommandWindowsAsAdmin(cmd):
	"""
	Launch cmd.exe as administrator and run `cmd`.
	cmd: string, e.g. 'dir C:\\Windows'
	"""
	if not PlatformWindows():
		raise Exception('This function is only supported on Windows')
	import ctypes
	# ShellExecuteW returns >32 if successful
	params = f"/k {cmd}"
	# None, verb, file, params, cwd, show
	result = ctypes.windll.shell32.ShellExecuteW(
		None,                   # hwnd
		"runas",                # verb
		"cmd.exe",              # file
		params,                 # parameters
		None,                   # directory (use default)
		1                       # SW_SHOWNORMAL
	)
	if result <= 32:
		raise RuntimeError(f"Failed to launch admin cmd (error code {result})")
	
def RunCommandMacOS(cmd: str) -> subprocess.CompletedProcess:
	""" Launches a shell command on macOS and returns the output.
	cmd: string, e.g. 'ls -l /Applications'
	"""
	if not PlatformMacOS():
		raise Exception('This function is only supported on macOS')
	return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def RunCommandMacOSAsAdmin(cmd: str) -> subprocess.CompletedProcess:
	"""
	Launch a shell command on macOS with administrator privileges via osascript.
	cmd: string, e.g. 'ln -s "/src" "/dst"'
	"""
	if not PlatformMacOS():
		raise Exception('This function is only supported on macOS')
	escaped = cmd.replace('\\', '\\\\').replace('"', '\\"')
	osascript_cmd = f'osascript -e \'do shell script "{escaped}" with administrator privileges\''
	result = subprocess.run(osascript_cmd, shell=True, capture_output=True, text=True)
	if result.returncode != 0:
		raise RuntimeError(f"Admin command failed (exit code {result.returncode}): {result.stderr}")
	return result




def GetAppDataPath() -> Path:
	"""Returns the path to the AppData folder for the current user. For example: C:\\Users\\myself\\AppData\\Roaming"""
	if PlatformWindows():
		return Path(str(os.getenv('APPDATA')))
	if PlatformMacOS():
		return Path.home()/'Library/Preferences'
	# if PlatformLinux():
	# 	return os.path.expanduser('~')
	raise Exception('Unsupported platform')

def GetLocalAppDataPath() -> Path:
	"""Returns the path to the Local AppData folder for the current user. For example: C:\\Users\\myself\\AppData\\Local"""
	if PlatformWindows():
		return Path(str(os.getenv('LOCALAPPDATA')))
	if PlatformMacOS():
		return Path.home()/'Library/Application Support'
	# if PlatformLinux():
	# 	return os.path.expanduser('~')
	raise Exception('Unsupported platform')

def GetTempDataPath() -> Path:
	"""Returns the path to the temporary directory. For example: C:\\Users\\myself\\AppData\\Local\\Temp"""
	return Path(tempfile.gettempdir())

def GetQAVMDataVersionTag() -> str:
	"""Returns the version tag used to scope the regular (app) data folder, i.e. the full QAVM version (e.g. '0.4.0').
	Patch releases get their own subfolder; the migration logic silently carries data across patch bumps."""
	# Imported lazily to avoid a circular import (qavm_version -> logs -> utils).
	from qavm.qavm_version import GetQAVMVersion
	return GetQAVMVersion()

def GetQAVMDataRootPath(create=True) -> Path:
	"""Returns the root folder for ALL QAVM data (version-agnostic). For example: C:\\Users\\myself\\AppData\\Roaming\\qavm
	This folder hosts the per-version regular data subfolders and the per-plugin data subtree."""
	path: Path = GetAppDataPath()/'qavm'
	if create: CreateDir(path)
	return path

def GetQAVMDataPath(create=True) -> Path:
	"""Returns the regular (app) data folder for the CURRENT QAVM version.
	For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\0.4.0"""
	path: Path = GetQAVMDataRootPath(create=create)/GetQAVMDataVersionTag()
	if create: CreateDir(path)
	return path

def GetDefaultPluginsFolderPath(create=False) -> Path:
	"""Returns the folder where user-installed plugin SOURCE CODE lives (app-versioned).
	For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\0.4.0\\plugins"""
	path: Path = GetQAVMDataPath(create=create)/'plugins'
	if create: CreateDir(path)
	return path

def GetPrefsFolderPath(create=True) -> Path:
	"""Returns the path to the QAVM preferences folder (app-versioned). For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\0.4.0\\preferences"""
	path: Path = GetQAVMDataPath(create=create)/'preferences'
	if create: CreateDir(path)
	return path

def GetQAVMTempPath(create=True) -> Path:
	"""Returns the path to the QAVM temporary folder. For example: C:\\Users\\myself\\AppData\\Local\\Temp\\qavm"""
	path: Path =  GetTempDataPath()/'qavm'
	if create: CreateDir(path)
	return path

def GetQAVMCachePath(create=True) -> Path:
	"""Returns the path to the QAVM cache folder (app-versioned). For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\0.4.0\\cache"""
	path: Path =  GetQAVMDataPath(create=create)/'cache'
	if create: CreateDir(path)
	return path

def GetQAVMLogsPath(create=True) -> Path:
	"""Returns the path to the QAVM logs folder. Logs are SHARED across versions (unversioned).
	For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\logs"""
	path: Path =  GetQAVMDataRootPath(create=create)/'logs'
	if create: CreateDir(path)
	return path

# TODO: consider having %APPDATA%/qavm/<version>/data folder for this type of data
def GetQAVMDescriptorDataFilepath() -> Path:
	"""Returns the path to the QAVM descriptor data file (app-versioned). For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\0.4.0\\descdata.json"""
	return GetQAVMDataPath()/'descdata.json'

# TODO: consider having %APPDATA%/qavm/<version>/data folder for this type of data
def GetQAVMTagsDataFilepath() -> Path:
	"""Returns the path to the QAVM tags data file (app-versioned). For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\0.4.0\\tagsdata.json"""
	return GetQAVMDataPath()/'tagsdata.json'


############################ Per-plugin data paths ############################
# Plugin data (preferences, logs, ...) is scoped by the plugin's OWN version (PLUGIN_VERSION),
# decoupled from the app version, and lives in a dedicated subtree:
#   <appdata>/qavm/plugins/<pluginID>/<pluginVersion>/...

def GetPluginDataPath(pluginID: str, pluginVersion: str, create=True) -> Path:
	"""Returns the root data folder for a given plugin version.
	For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\plugins\\in.wi1k.tools.qavm.plugin.example\\0.4.0"""
	path: Path = GetQAVMDataRootPath(create=create)/'plugins'/pluginID/pluginVersion
	if create: CreateDir(path)
	return path

def GetPluginPrefsFolderPath(pluginID: str, pluginVersion: str, create=True) -> Path:
	"""Returns the preferences folder for a given plugin version.
	For example: <appdata>/qavm/plugins/<pluginID>/<pluginVersion>/preferences"""
	path: Path = GetPluginDataPath(pluginID, pluginVersion, create=create)/'preferences'
	if create: CreateDir(path)
	return path

def GetPluginLogsPath(pluginID: str, pluginVersion: str, create=True) -> Path:
	"""Returns the logs folder for a given plugin version.
	For example: <appdata>/qavm/plugins/<pluginID>/<pluginVersion>/logs"""
	path: Path = GetPluginDataPath(pluginID, pluginVersion, create=create)/'logs'
	if create: CreateDir(path)
	return path

def IsFrozen() -> bool:
	"""Returns True when running from a PyInstaller bundle (release), False when running from source (dev)."""
	return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def GetQAVMExecutablePath() -> Path:
	""" Returns the absolute path to the QAVM executable. For example: qavm\\source\\qavm.py"""
	if PlatformWindows() or PlatformMacOS():
		return Path(sys.argv[0]).absolute()
	if PlatformLinux():
		raise Exception('Not implemented')
	raise Exception('Unsupported platform')

def GetQAVMRootPath() -> Path:
	if PlatformWindows() or PlatformMacOS():
		return GetQAVMExecutablePath().parent
	if PlatformLinux():
		raise Exception('Not implemented')
	raise Exception('Unsupported platform')

def GetQAVMResPath() -> Path:
	""" Returns the absolute path to the QAVM resources folder.
	Release (PyInstaller): the 'res' folder sits next to the executable, i.e. <rootPath>/res.
	Development (running qavm.py): the executable lives in 'qavm/source', while the 'res' folder
	is one level up in the repository root, i.e. qavm/res."""
	if IsFrozen():
		if PlatformWindows():
			return GetQAVMRootPath()/'res'
		if PlatformMacOS():
			return GetQAVMRootPath().parent/'Resources/res'
		return GetQAVMRootPath()/'res'
	return GetQAVMRootPath().parent/'res'



def GetHashNumber(number, hashAlgo='sha256'):
	return GetHashString(str(number), hashAlgo)

def GetHashString(string: str, hashAlgo='sha256'):
	return hashlib.new(hashAlgo, string.encode()).hexdigest()

def GetHashFile(filePath: Path, hashAlgo='sha256'):
	# TODO: make a helper function out of it
	# .app bundles on macOS are directories; hash the main binary inside instead
	if filePath.is_dir():
		if PlatformMacOS() and filePath.suffix.lower() == '.app':
			info_plist = filePath / "Contents" / "Info.plist"
			if info_plist.exists():
				import plistlib
				with info_plist.open("rb") as f:
					info = plistlib.load(f)
				exec_name = info.get("CFBundleExecutable")
				if exec_name:
					binary = filePath / "Contents" / "MacOS" / exec_name
					if binary.exists():
						filePath = binary
					else:
						filePath = info_plist
				else:
					filePath = info_plist
		else:
			raise IsADirectoryError(f"Cannot hash a directory: {filePath}")
	CHUNKSIZE = 32 * 1024 * 1024  # 32 MB
	hashFunc = hashlib.new(hashAlgo)
	with open(filePath, 'rb') as file:
		while chunk := file.read(CHUNKSIZE):
			hashFunc.update(chunk)
	return hashFunc.hexdigest()[:12]

def GetWinExeVersionInfo(execPath: Path) -> tuple[str, str]:
	"""Extract file version and product version from exe properties.
	Returns (fileVersion, productVersion)"""
	try:
		import win32api
		strPath = str(execPath)
		# Get numeric file version
		info = win32api.GetFileVersionInfo(strPath, '\\')
		fileVersion = '{}.{}.{}.{}'.format(
			info['FileVersionMS'] >> 16, info['FileVersionMS'] & 0xFFFF,
			info['FileVersionLS'] >> 16, info['FileVersionLS'] & 0xFFFF)
		# Get string product version from StringFileInfo
		langCodepage = win32api.GetFileVersionInfo(strPath, '\\VarFileInfo\\Translation')
		prodVersion = None
		if langCodepage:
			lang, codepage = langCodepage[0]
			prodVersion = win32api.GetFileVersionInfo(strPath, f'\\StringFileInfo\\{lang:04x}{codepage:04x}\\ProductVersion')
		return fileVersion, prodVersion or fileVersion
	except Exception as e:
		logger.warning(f"Failed to get version info from {execPath}: {e}")
	return '', ''

# TODO: this is better to be an QAVMApp class variable
processes: dict[str, subprocess.Popen] = dict()
def StartProcess(uid: str, path: Path, args: list[str], clean_env: bool = True) -> int:
	"""
	Start a process and track it by `uid`.

	Args:
		uid: Unique identifier for the launched process.
		path: Path to the executable to run.
		args: List of arguments to pass to the process.
		clean_env: When True (default) remove Qt-related and Python environment
			variables from the child process environment to avoid DLL/plugin
			collisions (e.g. when launching external apps that bundle Qt).
	"""
	p: subprocess.Popen | None = None

	env_to_use = None
	if clean_env:
		env = os.environ.copy()
		for key in [
			"QT_PLUGIN_PATH",
			"QML2_IMPORT_PATH",
			"QT_QPA_PLATFORM_PLUGIN_PATH",
			"PYTHONPATH",
		]:
			env.pop(key, None)
		# Remove the current Python/app directory from PATH to avoid mixing DLLs.
		app_dir = str(Path(sys.executable).parent)
		path_entries = env.get("PATH", "").split(os.pathsep)
		path_entries = [
			p for p in path_entries
			if os.path.normcase(os.path.normpath(p)) != os.path.normcase(os.path.normpath(app_dir))
		]
		env["PATH"] = os.pathsep.join(path_entries)
		env_to_use = env

	if PlatformWindows():
		p = subprocess.Popen([str(path), *args], env=env_to_use)
	elif PlatformMacOS():
		# TODO: open doesn't give a PID, so we can't track the process. need to find the PID by name or something else
		p = subprocess.Popen(['open', '-a', str(path), '--args', *args], env=env_to_use)
	# elif PlatformLinux():
	# 	return subprocess.Popen([path, args]).pid
	else:
		raise Exception('Unsupported platform')
    
	if p is None:
		raise Exception('Failed to start process')

	processes[uid] = p
	return p.pid

def StopProcess(uid: str) -> bool:
	if uid not in processes:
		return False
	
	p = processes[uid]
	if PlatformWindows():
		if p and p.poll() is None:
			p.terminate()
			p.wait()
		# else:
		# 	print('Process not running')
		# subprocess.Popen(['taskkill', '/F', '/PID', str(p.pid)])
	elif PlatformMacOS():
		raise Exception('Not implemented')
		subprocess.Popen(['kill', '-9', str(p.pid)])
	# elif PlatformLinux():
	# 	subprocess.Popen(['kill', '-9', str(p.pid)])
	else:
		raise Exception('Unsupported platform')
	
	del processes[uid]
	return True

def IsProcessRunning(uid: str) -> bool:
	if uid not in processes:
		return False
	p = processes[uid]
	if p and p.poll() is None:
		return True
	return False

def ExtractZipFile(zipFilePath: Path, extractTo: Path) -> bool:
	"""Extracts a ZIP file to the specified directory."""
	raise AssertionError("This function isn't tested yet!")
	if not zipfile.is_zipfile(zipFilePath):
		return False
	with zipfile.ZipFile(zipFilePath, 'r') as zip_ref:
		zip_ref.extractall(extractTo)
	return True



# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================
# ======================================================================