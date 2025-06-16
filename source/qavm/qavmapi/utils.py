import os, platform, json, hashlib, subprocess, sys
import zipfile, shutil, tempfile
from pathlib import Path
from typing import Any

from qavm.qavmapi.media_cache import MediaCache

def PlatformWindows():
	return platform.system() == 'Windows'
def PlatformLinux():
	return platform.system() == 'Linux'
def PlatformMacOS():
	return platform.system() == 'Darwin'
def PlatformName() -> str:
	return platform.system().lower()


def GetQAVMDataPath() -> Path:
	path: Path = GetAppDataPath()/'qamv'
	os.makedirs(path, exist_ok=True)
	return path

def GetDefaultPluginsFolderPath() -> Path:
	return GetQAVMDataPath()/'plugins'

def GetPrefsFolderPath() -> Path:
	return GetQAVMDataPath()/'preferences'

def GetQAVMTempPath() -> Path:
	return GetTempDataPath()/'qavm'

def GetQAVMCachePath() -> Path:
	return GetQAVMDataPath()/'cache'

def GetAppDataPath() -> Path:
	"""Returns the path to the AppData folder for the current user."""
	if PlatformWindows():
		return Path(str(os.getenv('APPDATA')))
	if PlatformMacOS():
		return Path.home()/'Library/Preferences'
	# if PlatformLinux():
	# 	return os.path.expanduser('~')
	raise Exception('Unsupported platform')

def GetTempDataPath() -> Path:
	"""Returns the path to the temporary directory."""
	if PlatformWindows():
		return Path(os.getenv('TEMP', tempfile.gettempdir()))
	if PlatformMacOS() or PlatformLinux():
		return Path(tempfile.gettempdir())
	raise Exception('Unsupported platform')

def GetQAVMExecutablePath() -> Path:
	if PlatformWindows() or PlatformMacOS():
		return Path(sys.argv[0]).absolute()
	if PlatformLinux():
		raise Exception('Not implemented')
	raise Exception('Unsupported platform')

# TODO: this is likely for internal use only, so it should be outside of qavmapi
def GetQAVMRootPath() -> Path:
	if PlatformWindows() or PlatformMacOS():
		return GetQAVMExecutablePath().parent
	if PlatformLinux():
		raise Exception('Not implemented')
	raise Exception('Unsupported platform')

def OpenFolderInExplorer(folderPath: Path):
	if PlatformWindows():
		os.startfile(folderPath)
	elif PlatformMacOS():
		subprocess.Popen(['open', folderPath])
	# elif PlatformLinux():
	# 	subprocess.Popen(['xdg-open', folderPath])
	else:
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

def IsPathSymlink(path: Path) -> bool:
  return path.is_symlink()

def IsPathJunction(path: Path) -> bool:
		if not path.is_dir() or not PlatformWindows():
			return False
		import ctypes
		FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
		attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
		return attrs != -1 and bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT) and not path.is_symlink()

def GetPathSymlinkTarget(path: Path) -> Path:
  return path.resolve(strict=False) if IsPathSymlink(path) else path

def GetPathJunctionTarget(path: Path) -> Path:
  print('TODO: this is not tested!')  # TODO: test and fix
  return path.resolve(strict=False) if IsPathJunction(path) else path

def GetFileBirthtime(path: Path) -> float:
	if PlatformWindows():
		return path.stat().st_ctime
	elif PlatformMacOS():
		return path.stat().st_birthtime
	elif PlatformLinux():
		raise NotImplementedError('Linux does not support file birthtime retrieval in a standard way')

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

def CopyFolder(srcFolderPath: Path, dstFolderPath: Path, mkdir: bool = True) -> None:
	""" Copies srcFolderPath to dstFolderPath """
	if not srcFolderPath.is_dir():
		raise ValueError(f"Source path '{srcFolderPath}' is not a directory.")
	if mkdir:
		dstFolderPath.mkdir(parents=True, exist_ok=True)
	shutil.copytree(srcFolderPath, dstFolderPath, dirs_exist_ok=True, symlinks=True)

def DeleteFolder(folderPath: Path) -> None:
	""" Deletes the specified folder and all its contents. """
	if not folderPath.exists():
		return  # nothing to delete
	if not folderPath.is_dir():
		raise ValueError(f"Path '{folderPath}' is not a directory.")
	shutil.rmtree(folderPath)

def CopyFile(srcFilePath: Path, dstFilePath: Path) -> None:
	""" Copies a file from srcFilePath to dstFilePath. """
	if not srcFilePath.is_file():
		raise ValueError(f"Source path '{srcFilePath}' is not a file.")
	dstFilePath.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy2(srcFilePath, dstFilePath)