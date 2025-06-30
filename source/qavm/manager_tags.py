from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from qavm.manager_descriptor_data import DescriptorDataManager

from qavm.qavmapi import BaseDescriptor

import qavm.logs as logs
logger = logs.logger

class Tag(object):
	def __init__(self, uid: str, name: str, color: str) -> None:
		self.uid: str = uid
		self.name: str = name
		self.color: str = color

	def GetUID(self) -> str:
		return self.uid

	def GetName(self) -> str:
		return self.name
	
	def GetColor(self) -> str:
		return self.color

	@staticmethod
	def Deserialize(data: dict[str, str]) -> Tag:
		if not isinstance(data, dict):
			raise TypeError(f'Expected dict, got {type(data)}')
		if {'uid', 'name', 'color'}.issubset(data.keys()):
			return Tag(
				uid=data['uid'],
				name=data['name'],
				color=data['color']
			)
		raise ValueError(f'Invalid tag data: {data}. Expected keys: uid, name, color')
	
	def Serialize(self) -> dict[str, str]:
		return {
			'uid': self.uid,
			'name': self.name,
			'color': self.color
		}

	def __repr__(self) -> str:
		return f'Tag(uid={self.uid}, name={self.name}, color={self.color})'
	
	def __eq__(self, other: object) -> bool:
		if not isinstance(other, Tag):
			return False
		return (self.uid == other.uid and
				self.name == other.name and
				self.color == other.color)

class TagsManager(object):
	def __init__(self, tagsDataFilepath: Path, descDataManager: DescriptorDataManager) -> None:
		self.tagsDataFilepath: Path = tagsDataFilepath
		self.descDataManager: DescriptorDataManager = descDataManager

		self.tags: dict[str, Tag] = dict()  # Using a dict for faster lookups by tag uid

	def LoadTags(self) -> None:
		if not self.tagsDataFilepath.exists():
			self.SaveTags()
			return
		try:
			data = self.tagsDataFilepath.read_text(encoding='utf-8')
			tagList = json.loads(data)
			self.tags = dict()
			for tag in tagList:
				try:
					t: Tag = Tag.Deserialize(tag)
					self.tags[t.GetUID()] = t
				except (TypeError, ValueError) as e:
					logger.error(f'Failed to deserialize tag {tag}: {e}')
					continue
		except json.JSONDecodeError as e:
			raise RuntimeError(f'Failed to load tags from {self.tagsDataFilepath}: {e}') from e
		
	def SaveTags(self) -> None:
		try:
			tagList = [tag.Serialize() for tag in self.tags.values()]
			self.tagsDataFilepath.write_text(json.dumps(tagList, indent=4), encoding='utf-8')
		except Exception as e:
			raise RuntimeError(f'Failed to save tags to {self.tagsDataFilepath}: {e}') from e

	def GetTags(self) -> dict[str, Tag]:
		return self.tags
	
	def GetTag(self, tagUID: str) -> Tag | None:
		if not isinstance(tagUID, str):
			raise TypeError(f'Expected str, got {type(tagUID)}')
		return self.tags.get(tagUID, None)
	
	def AddTag(self, tag: Tag) -> None:
		if not isinstance(tag, Tag):
			raise TypeError(f'Expected Tag, got {type(tag)}')
		if tag in self.tags:
			logger.warning(f'Tag {tag} already exists, skipping addition')
			return
		self.tags[tag.GetUID()] = tag
		self.SaveTags()

	def RemoveTag(self, tag: Tag) -> None:
		if not isinstance(tag, Tag):
			raise TypeError(f'Expected Tag, got {type(tag)}')
		if tag.GetUID() not in self.tags:
			return
		del self.tags[tag.GetUID()]
		self.SaveTags()
	
	def AssignTag(self, desc: BaseDescriptor, tag: Tag) -> None:
		if not isinstance(desc, BaseDescriptor):
			raise TypeError(f'Expected BaseDescriptor, got {type(desc)}')
		if not isinstance(tag, Tag):
			raise TypeError(f'Expected Tag, got {type(tag)}')
		
		if tag.GetUID() not in self.tags:
			raise ValueError(f'Tag {tag.GetUID()} does not exist in tags manager')
		
		descData: dict[str, Any] = self.descDataManager.GetDescriptorData(desc)
		if qavmData := descData.get('__qavm__', {}):
			if 'tags' not in qavmData:
				qavmData['tags'] = []
			if tag.GetUID() not in qavmData['tags']:
				qavmData['tags'].append(tag.GetUID())
				self.descDataManager.SetDescriptorData(desc.GetUID(), descData)
				self.descDataManager.SaveData()