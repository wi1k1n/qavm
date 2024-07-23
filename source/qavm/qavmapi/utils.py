import os, platform

def GetPluginsFolderPath() -> str:
	return os.path.join(GetPrefsFolderPath(), 'plugins')

def GetPrefsFolderPath() -> str:
	path: str = os.path.join(GetAppDataPath(), 'qamv')
	os.makedirs(path, exist_ok=True)
	return path

def GetAppDataPath() -> str:
	"""Returns the path to the AppData folder for the current user."""
	if PlatformWindows():
		return os.getenv('APPDATA')
	# if PlatformLinux():
	# 	return os.path.expanduser('~')
	if PlatformMacOS():
		return os.path.expanduser('~/Library/Preferences')


def PlatformWindows():
    return platform.system() == 'Windows'
def PlatformLinux():
    return platform.system() == 'Linux'
def PlatformMacOS():
    return platform.system() == 'Darwin'