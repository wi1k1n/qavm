import json
from pathlib import Path
from typing import Any
from qavm.qavmapi import BaseDescriptor




class DescriptorDataManager(object):
	def __init__(self, dataFilepath: Path) -> None:
		self.dataFilepath: Path = dataFilepath
		self.data: dict[str, Any] = {'__qavm__': {}}

	def GetDescriptorData(self, desc: BaseDescriptor) -> dict[str, Any]:
		descUID: str = desc.GetUID()
		ret: dict[str, Any] = {}
		for handlerBranchID, data in self.data.items():
			if descUID in data:
				ret[handlerBranchID] = data[descUID]
		return ret
	
	def SetDescriptorData(self, descUID: str, data: dict[str, Any]) -> None:
		if not isinstance(data, dict):
			raise TypeError(f'Expected dict, got {type(data)}')
		if '__qavm__' not in self.data:
			self.data['__qavm__'] = {}
		for handlerBranchID in self.data:
			if descUID in self.data[handlerBranchID]:
				self.data[handlerBranchID][descUID] = data
				return
		self.data['__qavm__'][descUID] = data

	def LoadData(self) -> None:
		if not self.dataFilepath.exists():
			self.SaveData()  # Create the file if it doesn't exist
			return
		try:
			self.data = json.loads(self.dataFilepath.read_text(encoding='utf-8'))
		except json.JSONDecodeError as e:
			raise RuntimeError(f'Failed to load descriptor data from {self.dataFilepath}: {e}') from e
		
	def SaveData(self) -> None:
		try:
			self.dataFilepath.write_text(json.dumps(self.data, indent=4), encoding='utf-8')
		except Exception as e:
			raise RuntimeError(f'Failed to save descriptor data to {self.dataFilepath}: {e}') from e

	# def LoadDescriptorsData(self, workspace: 'QAVMWorkspace') -> None:
	# 	if not workspace:
	# 		return
		
	# 	plugins, _ = workspace.GetInvolvedPlugins()
	# 	for plugin in plugins:
	# 		for (sID, swHandler) in plugin.GetSoftwareHandlers().items():
	# 			descClasses: dict[str, type[BaseDescriptor]] = swHandler.GetDescriptorClasses()
	# 			print(f'Loading descriptors for {swHandler.GetName()} ({len(descClasses)} classes)')