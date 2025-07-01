import json
from pathlib import Path
from typing import Any
from qavm.qavmapi import BaseDescriptor



class DescriptorData(object):
	def __init__(self) -> None:
		self.tags: list[str] = []  # List of tag UIDs
		self.noteVisible: str = ''  # The small note that's visible on the descriptor tile
		self.note: str = ''  # The full note text, which can be edited in the note editor dialog
	
	def Serialize(self) -> dict[str, Any]:
		""" Serializes the descriptor data to a dictionary. """
		return {
			'tags': self.tags,
			'noteVisible': self.noteVisible,
			'note': self.note
		}
	
	# TODO: refactor this to a more generic implementation
	@staticmethod
	def Deserialize(data: dict[str, Any]) -> 'DescriptorData':
		""" Deserializes the descriptor data from a dictionary. """
		if not isinstance(data, dict):
			raise TypeError(f'Expected dict, got {type(data)}')
		descData = DescriptorData()
		if 'tags' in data:
			if not isinstance(data['tags'], list):
				raise TypeError(f'Expected list for tags, got {type(data["tags"])}')
			descData.tags = data['tags']
		if 'noteVisible' in data:
			if not isinstance(data['noteVisible'], str):
				raise TypeError(f'Expected str for noteVisible, got {type(data["noteVisible"])}')
			descData.noteVisible = data['noteVisible']
		if 'note' in data:
			if not isinstance(data['note'], str):
				raise TypeError(f'Expected str for note, got {type(data["note"])}')
			descData.note = data['note']
		return descData


class DescriptorDataManager(object):
	def __init__(self, dataFilepath: Path) -> None:
		self.dataFilepath: Path = dataFilepath
		# self.data_old: dict[str, Any] = {'__qavm__': {}}
		self.data: dict[str, DescriptorData] = {}  # UID -> DescriptorData

	def GetDescriptorData(self, desc: BaseDescriptor) -> DescriptorData:
		descUID: str = desc.GetUID()
		if descUID not in self.data:
			self.data[descUID] = DescriptorData()
		return self.data[descUID]
	
	def SetDescriptorData(self, desc: BaseDescriptor, data: DescriptorData) -> None:
		if not isinstance(data, DescriptorData):
			raise TypeError(f'Expected DescriptorData, got {type(data)}')
		descUID: str = desc.GetUID()
		self.data[descUID] = data

	def LoadData(self) -> None:
		if not self.dataFilepath.exists():
			self.SaveData()  # Create the file if it doesn't exist
			return
		try:
			self.data = self.DeserializeData(json.loads(self.dataFilepath.read_text(encoding='utf-8')))
		except json.JSONDecodeError as e:
			raise RuntimeError(f'Failed to load descriptor data from {self.dataFilepath}: {e}') from e
		
	def SaveData(self) -> None:
		try:
			self.dataFilepath.write_text(json.dumps(self.SerializeData(), indent=4), encoding='utf-8')
		except Exception as e:
			raise RuntimeError(f'Failed to save descriptor data to {self.dataFilepath}: {e}') from e
		
	def SerializeData(self) -> dict[str, Any]:
		""" Serializes the descriptor data to a dictionary. """
		return {descUID: dd.Serialize() for descUID, dd in self.data.items()}
	
	def DeserializeData(self, data: dict[str, Any]) -> dict[str, DescriptorData]:
		""" Deserializes the descriptor data from a dictionary. """
		if not isinstance(data, dict):
			raise TypeError(f'Expected dict, got {type(data)}')
		return {descUID: DescriptorData.Deserialize(dd) for descUID, dd in data.items()}

	# def LoadDescriptorsData(self, workspace: 'QAVMWorkspace') -> None:
	# 	if not workspace:
	# 		return
		
	# 	plugins, _ = workspace.GetInvolvedPlugins()
	# 	for plugin in plugins:
	# 		for (sID, swHandler) in plugin.GetSoftwareHandlers().items():
	# 			descClasses: dict[str, type[BaseDescriptor]] = swHandler.GetDescriptorClasses()
	# 			print(f'Loading descriptors for {swHandler.GetName()} ({len(descClasses)} classes)')