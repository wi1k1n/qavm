import os, platform, json, hashlib, subprocess, sys
import zipfile, shutil, tempfile, ctypes
from pathlib import Path
from typing import Any, Optional

from qavm.qavmapi.media_cache import MediaCache

def PlatformWindows():
	return platform.system() == 'Windows'
def PlatformLinux():
	return platform.system() == 'Linux'
def PlatformMacOS():
	return platform.system() == 'Darwin'
def PlatformName() -> str:
	return platform.system().lower()


# def IsPathFile(path: Path) -> bool:
# 	""" Checks if the given path is a file. """
# 	if PlatformWindows():
# 		if IsPathSymlink(path) or IsPathJunction(path):
# 			return False  # Symlinks and junctions are not treated as regular files
# 	return path.is_file() and not IsPathSymlink(path)

# def IsPathFolder(path: Path) -> bool:
# 	""" Checks if the given path is a folder. """
# 	if PlatformWindows():
# 		if IsPathJunction(path):
# 			return False  # Junction points are treated as folders
# 	return path.is_dir() and not IsPathSymlink(path)

# def IsPathSymlink(path: Path) -> bool:
# 	"""
# 	Checks if the given path is a symbolic link.
# 	On Windows: returns False for junction points.
# 	"""
# 	return path.is_symlink()

# def GetPathSymlinkTarget(path: Path) -> Path:
# 	""" Returns the target of a symbolic link or junction point. If the path is not a symlink or junction, returns the path itself. """
# 	return path.resolve(strict=False) if IsPathSymlink(path) else path

# def IsPathJunction(path: Path) -> bool:
# 	""" Checks if the given path is a junction point (Windows only). """
# 	if not path.is_dir() or not PlatformWindows():
# 		return False
# 	import ctypes
# 	FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
# 	attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
# 	return attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT) and not path.is_symlink()

# def GetPathJunctionTarget(path: Path) -> Path:
# 	""" Returns the target of a junction point. If the path is not a junction, returns the path itself. (Windows only) """
# 	print('TODO: this is not tested!')  # TODO: test and fix
# 	if not PlatformWindows():
# 		raise NotImplementedError('This function is only supported on Windows')
# 	return path.resolve(strict=False) if IsPathJunction(path) else path


# def CreateFolder(path: Path, parents: bool = True, exist_ok: bool = True) -> None:
# 	""" Creates a folder at the specified path. """
# 	path.mkdir(parents=parents, exist_ok=exist_ok)

# def CreateSymlink(target: Path, link_name: Path) -> None:
# 	""" Creates a symbolic link at link_name pointing to target. """
# 	if not target.exists():
# 		raise ValueError(f"Target '{target}' does not exist.")
# 	if link_name.exists():
# 		raise ValueError(f"Link name '{link_name}' already exists.")
# 	target.symlink_to(link_name, target_is_directory=target.is_dir())

# def DeleteFolder(folderPath: Path) -> None:
# 	""" Deletes the specified folder and all its contents. """
# 	if not folderPath.exists():
# 		return  # nothing to delete
# 	if not IsPathFolder(folderPath) and not IsPathJunction(folderPath):
# 		raise ValueError(f"Path '{folderPath}' is not a folder.")
# 	shutil.rmtree(folderPath)

# def DeleteFile(filePath: Path) -> None:
# 	""" Deletes the specified file. """
# 	if not IsPathFile(filePath) and not IsPathSymlink(filePath):
# 		raise ValueError(f"Path '{filePath}' is not a file.")
# 	filePath.unlink(missing_ok=True)  # missing_ok=True allows it to not raise an error if the file does not exist

# def CopyFolder(srcFolderPath: Path, dstFolderPath: Path, mkdir: bool = True) -> None:
# 	""" Copies srcFolderPath to dstFolderPath """
# 	if not srcFolderPath.is_dir():
# 		raise ValueError(f"Source path '{srcFolderPath}' is not a directory.")
# 	if mkdir:
# 		dstFolderPath.mkdir(parents=True, exist_ok=True)
# 	shutil.copytree(srcFolderPath, dstFolderPath, dirs_exist_ok=True, symlinks=True)

# def CopyFile(srcFilePath: Path, dstFilePath: Path) -> None:
# 	""" Copies a file from srcFilePath to dstFilePath. """
# 	if not srcFilePath.is_file():
# 		raise ValueError(f"Source path '{srcFilePath}' is not a file.")
# 	dstFilePath.parent.mkdir(parents=True, exist_ok=True)
# 	shutil.copy2(srcFilePath, dstFilePath)



# === Detection Functions ===

def IsPathFile(path: Path) -> bool:
	return path.is_file() and not path.is_symlink()

def IsPathDir(path: Path) -> bool:
	return path.is_dir() and not path.is_symlink() and not IsPathJunction(path)

def IsPathSymlinkF(path: Path) -> bool:
	return path.is_symlink() and path.resolve().is_file()

def IsPathSymlinkD(path: Path) -> bool:
	return path.is_symlink() and path.resolve().is_dir()

def IsPathHardlink(path: Path) -> bool:
	if not path.exists() or path.is_symlink():
		return False
	hfile = os.open(path, os.O_RDONLY)
	try:
		info = os.fstat(hfile)
		return info.st_nlink > 1
	finally:
		os.close(hfile)

def IsPathJunction(path: Path) -> bool:
	if not PlatformWindows():
		raise NotImplementedError("Junctions are only supported on Windows.")
	if not path.is_dir() or not path.exists():
		return False
	FILE_ATTRIBUTE_REPARSE_POINT = 0x400
	attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
	return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT) and not path.is_symlink()

def IsPathShortcut(path: Path) -> bool:
	if not PlatformWindows():
		raise NotImplementedError("Shortcuts are only supported on Windows.")
	return path.suffix.lower() == '.lnk' and path.is_file()

def IsPathAlias(path: Path) -> bool:
	if not PlatformMacOS():
		raise NotImplementedError("Aliases are only supported on macOS.")
	return path.exists() and subprocess.run(
		["osascript", "-e", f'tell application "Finder" to return kind of (POSIX file "{path}" as alias)'],
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL
	).returncode == 0

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

def GetAliasTarget(path: Path) -> Optional[Path]:
	if not PlatformMacOS():
		raise NotImplementedError("Aliases are only supported on macOS.")
	if not IsPathAlias(path):
		return None
	result = subprocess.run([
		"osascript",
		"-e",
		f'set originalItem to (POSIX path of (original item of (POSIX file "{path}" as alias)))'
	], capture_output=True, text=True)
	return Path(result.stdout.strip()) if result.returncode == 0 else None

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

def CreateAlias(target: Path, link: Path, exist_overwrite: bool = False):
	if not PlatformMacOS():
		raise NotImplementedError("Aliases are only supported on macOS.")
	_checkLinkExistsOverwriteMkdir(target, link, exist_overwrite)
	subprocess.run([
		"osascript",
		"-e",
		f'tell application "Finder" to make alias file to POSIX file "{target}" at POSIX file "{link.parent}"',
		"-e",
		f'tell application "Finder" to set name of result to "{link.name}"'
	], check=True)

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

def CreateHardlink(target: Path, link: Path, exist_overwrite: bool = False):
	_checkLinkExistsOverwriteMkdir(target, link, exist_overwrite)
	os.link(target, link)

# === Deletion Functions ===

def DeletePath(path: Path):
	if IsPathDir(path):
		shutil.rmtree(path)
	else:
		path.unlink()









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










def GetFileBirthtime(path: Path) -> float:
	if PlatformWindows():
		return path.stat().st_ctime
	elif PlatformMacOS():
		return path.stat().st_birthtime
	elif PlatformLinux():
		raise NotImplementedError('Not implemented')



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
	
def RunCommandMacOS(cmd: str):
	""" Launches a shell command on macOS and returns the output.
	cmd: string, e.g. 'ls -l /Applications'
	"""
	if not PlatformMacOS():
		raise Exception('This function is only supported on macOS')
	return subprocess.run(cmd, shell=True, capture_output=True, text=True)




def GetAppDataPath() -> Path:
	"""Returns the path to the AppData folder for the current user. For example: C:\\Users\\myself\\AppData\\Roaming"""
	if PlatformWindows():
		return Path(str(os.getenv('APPDATA')))
	if PlatformMacOS():
		return Path.home()/'Library/Preferences'
	# if PlatformLinux():
	# 	return os.path.expanduser('~')
	raise Exception('Unsupported platform')

def GetTempDataPath() -> Path:
	"""Returns the path to the temporary directory. For example: C:\\Users\\myself\\AppData\\Local\\Temp"""
	return Path(tempfile.gettempdir())

def GetQAVMDataPath(create=True) -> Path:
	"""Returns the default path to the QAVM data folder. For example: C:\\Users\\myself\\AppData\\Roaming\\qavm"""
	path: Path = GetAppDataPath()/'qamv'
	if create: CreateDir(path)
	return path

def GetDefaultPluginsFolderPath(create=True) -> Path:
	"""Returns the default path to the QAVM plugins folder. For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\plugins"""
	path: Path = GetQAVMDataPath()/'plugins'
	if create: CreateDir(path)
	return path

def GetPrefsFolderPath(create=True) -> Path:
	"""Returns the path to the QAVM preferences folder. For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\preferences"""
	path: Path = GetQAVMDataPath()/'preferences'
	if create: CreateDir(path)
	return path

def GetQAVMTempPath(create=True) -> Path:
	"""Returns the path to the QAVM temporary folder. For example: C:\\Users\\myself\\AppData\\Local\\Temp\\qavm"""
	path: Path =  GetTempDataPath()/'qavm'
	if create: CreateDir(path)
	return path

def GetQAVMCachePath(create=True) -> Path:
	"""Returns the path to the QAVM cache folder. For example: C:\\Users\\myself\\AppData\\Roaming\\qavm\\cache"""
	path: Path =  GetQAVMDataPath()/'cache'
	if create: CreateDir(path)
	return path

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




def GetHashNumber(number, hashAlgo='sha256'):
	return GetHashString(str(number), hashAlgo)

def GetHashString(string: str, hashAlgo='sha256'):
	return hashlib.new(hashAlgo, string.encode()).hexdigest()

def GetHashFile(filePath: Path, hashAlgo='sha256'):
	CHUNKSIZE = 32 * 1024 * 1024  # 32 MB
	hashFunc = hashlib.new(hashAlgo)
	with open(filePath, 'rb') as file:
		while chunk := file.read(CHUNKSIZE):
			hashFunc.update(chunk)
	return hashFunc.hexdigest()[:12]

# TODO: this is better to be an QAVMApp class variable
processes: dict[str, subprocess.Popen] = dict()
def StartProcess(uid: str, path: Path, args: list[str]) -> int:
	p: subprocess.Popen | None = None

	if PlatformWindows():
		p = subprocess.Popen([str(path), *args])
	elif PlatformMacOS():
		raise Exception('Not implemented')
		p = subprocess.Popen(['open', str(path), *args])
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