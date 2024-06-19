import os

def GetPluginsFolderPath() -> str:
	return os.path.join(GetPrefsFolderPath(), 'plugins')

def GetPrefsFolderPath() -> str:
	path: str = os.path.join(GetAppDataPath(), 'qamv')
	os.makedirs(path, exist_ok=True)
	return path

def GetAppDataPath() -> str:
	"""Returns the path to the AppData folder for the current user."""
	return os.getenv('APPDATA')