
import logs
logger = logs.logger

class SettingsManager:
	def __init__(self, prefsFolderPath: str):
		self.prefsFolderPath: str = prefsFolderPath

		self.selectedSoftwareUID: str = ''
	
	def LoadSettings(self):
		logger.info('Loading settings: NotImplemented')

	def GetSelectedSoftwareUID(self) -> str:
		return self.selectedSoftwareUID
	
	def SetSelectedSoftwareUID(self, softwareUID: str) -> None:
		self.selectedSoftwareUID = softwareUID