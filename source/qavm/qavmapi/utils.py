from pathlib import Path
import os, platform

def GetPluginsFolderPath() -> Path:
	return GetQAVMDataPath()/'plugins'

def GetQAVMDataPath() -> Path:
	path: str = GetAppDataPath()/'qamv'
	os.makedirs(path, exist_ok=True)
	return path

def GetPrefsFolderPath() -> Path:
	return GetQAVMDataPath()/'preferences'

def GetAppDataPath() -> Path:
	"""Returns the path to the AppData folder for the current user."""
	if PlatformWindows():
		return Path(os.getenv('APPDATA'))
	# if PlatformLinux():
	# 	return os.path.expanduser('~')
	if PlatformMacOS():
		return Path.home()/'Library/Preferences'


def PlatformWindows():
    return platform.system() == 'Windows'
def PlatformLinux():
    return platform.system() == 'Linux'
def PlatformMacOS():
    return platform.system() == 'Darwin'