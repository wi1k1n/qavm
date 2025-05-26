import os, platform, json, hashlib, subprocess
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
		return Path(str(os.getenv('TEMP')))
	if PlatformMacOS():
		raise Exception('Not implemented')
		return Path('/tmp')
	# if PlatformLinux():
	# 	return Path('/tmp')
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