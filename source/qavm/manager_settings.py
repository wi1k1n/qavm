
import logs
logger = logs.logger

class SettingsManager:
	def __init__(self, prefsFolderPath: str):
		self.prefsFolderPath: str = prefsFolderPath

		self.selectedSoftwareUID: str = ''
		self.searchPaths: list[str] = [
			'C:\\Program Files'
		]
		self.searchSubfoldersDepth: int = 2
	
	def LoadSettings(self):
		logger.info('Loading settings: NotImplemented')

	def GetSelectedSoftwareUID(self) -> str:
		return self.selectedSoftwareUID
	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
		self.selectedSoftwareUID = softwareUID

	def GetSearchPaths(self) -> list[str]:
		return self.searchPaths
	
	def GetSearchSubfoldersDepth(self) -> int:
		return self.searchSubfoldersDepth