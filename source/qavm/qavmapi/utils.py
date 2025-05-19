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
