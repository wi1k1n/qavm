import json
from pathlib import Path
from typing import Any
from qavm.qavmapi import BaseDescriptor, BaseDescriptorData, DescriptonrDataAccessor

class DescriptorDataImpl(BaseDescriptorData):
	def Serialize(self) -> dict[str, Any]:
		""" Serializes the descriptor data to a dictionary. """
		return {
			'tags': self.tags,
			'noteSmall': self.noteSmall,
			'noteDetail': self.noteDetail
		}
	
	# TODO: refactor this to a more generic implementation
	@staticmethod
	def Deserialize(data: dict[str, Any]) -> 'DescriptorDataImpl':
		""" Deserializes the descriptor data from a dictionary. """
		if not isinstance(data, dict):
			raise TypeError(f'Expected dict, got {type(data)}')
		descData = DescriptorDataImpl()
		if 'tags' in data:
			if not isinstance(data['tags'], list):
				raise TypeError(f'Expected list for tags, got {type(data["tags"])}')
			descData.tags = data['tags']
		if 'noteSmall' in data:
			if not isinstance(data['noteSmall'], str):
				raise TypeError(f'Expected str for noteSmall, got {type(data["noteSmall"])}')
			descData.noteSmall = data['noteSmall']
		if 'noteDetail' in data:
			if not isinstance(data['noteDetail'], str):
				raise TypeError(f'Expected str for noteDetail, got {type(data["noteDetail"])}')
			descData.noteDetail = data['noteDetail']
		return descData

class DescriptonrDataAccessorImpl(DescriptonrDataAccessor):
	def __init__(self, descDataManager: 'DescriptorDataManager'):
		self.descDataManager: DescriptorDataManager = descDataManager

	def GetDescriptorData(self, desc: BaseDescriptor) -> DescriptorDataImpl:
		return self.descDataManager.GetDescriptorData(desc)

class DescriptorDataManager(object):
	def __init__(self, dataFilepath: Path) -> None:
		self.dataFilepath: Path = dataFilepath
		# self.data_old: dict[str, Any] = {'__qavm__': {}}
		self.data: dict[str, DescriptorDataImpl] = {}  # UID -> DescriptorDataImpl
		self.descDataAccessor: DescriptonrDataAccessorImpl = DescriptonrDataAccessorImpl(self)

	def GetDescriptorDataAccessor(self) -> DescriptonrDataAccessorImpl:
		return self.descDataAccessor
	
	def GetDescriptorData(self, desc: BaseDescriptor) -> DescriptorDataImpl:
		descUID: str = desc.GetUID()
		if descUID not in self.data:
			self.data[descUID] = DescriptorDataImpl()
		return self.data[descUID]
	
	def SetDescriptorData(self, desc: BaseDescriptor, data: DescriptorDataImpl) -> None:
		if not isinstance(data, DescriptorDataImpl):
			raise TypeError(f'Expected DescriptorDataImpl, got {type(data)}')
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
	
	def DeserializeData(self, data: dict[str, Any]) -> dict[str, DescriptorDataImpl]:
		""" Deserializes the descriptor data from a dictionary. """
		if not isinstance(data, dict):
			raise TypeError(f'Expected dict, got {type(data)}')
		return {descUID: DescriptorDataImpl.Deserialize(dd) for descUID, dd in data.items()}