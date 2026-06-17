from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from enum import StrEnum

from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorDataImpl

from qavm.manager_plugin import UID
from qavm.qavmapi import BaseDescriptor

import qavm.logs as logs
logger = logs.logger

class TagScope(object):
	def __init__(self, pluginID: str = '', softwareID: str = '', viewUID: str = ''):
		"""
		A tag scope defines the applicability of a tag to certain plugin/software/view contexts.
		An empty value for any of the fields means it applies to all (e.g. empty pluginID means it applies to all plugins).
		"""
		self.pluginID: str = pluginID
		self.softwareID: str = softwareID
		self.viewUID: str = viewUID

	@staticmethod
	def Deserialize(data: str) -> TagScope:
		try:
			dataDict = json.loads(data)
			if not isinstance(dataDict, dict):
				raise TypeError(f'Expected dict, got {type(dataDict)}')
			if {'pluginID', 'softwareID', 'viewUID'}.issubset(dataDict.keys()):
				return TagScope(
					pluginID=dataDict['pluginID'],
					softwareID=dataDict['softwareID'],
					viewUID=dataDict['viewUID']
				)
			raise ValueError(f'Invalid tag scope data: {data}. Expected keys: pluginID, softwareID, viewUID')
		except json.JSONDecodeError as e:
			raise ValueError(f'Failed to deserialize tag scope from {data}: {e}') from e
	
	def Serialize(self) -> str:
		return json.dumps({
			'pluginID': self.pluginID,
			'softwareID': self.softwareID,
			'viewUID': self.viewUID
		})

	# TODO: should be checked with the UID overhaul
	def IsApplicable(self, pluginID: str, softwareID: str, viewUID: str) -> bool:
		"""
		Returns True if this scope applies to the given plugin/software/view context.
			pluginID: the plugin ID to check, e.g. 'in.wi1k.tools.qavm.plugin.example'
			softwareID: the software ID to check, e.g. 'software.simple' or 'software.images'
			viewUID: the view UID to check (can be wildcard), e.g. 'views/table/exe' or 'views/tiles/*'
		"""
		if self.pluginID:
			if UID.IsDataPathWildcard(pluginID):
				logger.warning(f'Plugin ID {pluginID} is wildcard! This is not implemented yet!')
				return False
			if self.pluginID != UID.FetchPluginID(pluginID):
				return False
		if self.softwareID:
			if UID.IsDataPathWildcard(softwareID):
				logger.warning(f'Software ID {softwareID} is wildcard! This is not implemented yet!')
				return False
			if self.softwareID != UID.FetchSoftwareID(softwareID):
				return False
		if self.viewUID:
			dataPath = UID.FetchDataPath(viewUID)
			if UID.IsDataPathWildcard(self.viewUID):
				if not UID.MatchDataPath(self.viewUID, dataPath):
					return False
			else:
				if self.viewUID != dataPath:
					return False
		return True
class Tag(object):
	def __init__(self, uid: str, name: str, color: str, tagScopes: list[TagScope] = list()) -> None:
		self.uid: str = uid
		self.name: str = name
		self.color: str = color
		self.tagScopes: list[TagScope] = tagScopes  # empty is the same as global scope

	def GetUID(self) -> str:
		return self.uid

	def GetName(self) -> str:
		return self.name
	
	def GetColor(self) -> str:
		return self.color
	
	def GetScopes(self) -> list[TagScope]:
		return self.tagScopes

	def IsApplicableInContext(self, pluginID: str, softwareID: str, viewUID: str) -> bool:
		""" Returns True if the tag is applicable in the given plugin/software/view context. An empty scope list means global (always applicable). """
		if not self.tagScopes:
			return True  # empty is the same as global scope
		return any(scope.IsApplicable(pluginID, softwareID, viewUID) for scope in self.tagScopes)

	@staticmethod
	def Deserialize(data: dict[str, str]) -> Tag:
		if not isinstance(data, dict):
			raise TypeError(f'Expected dict, got {type(data)}')
		if {'uid', 'name', 'color', 'tagScopes'}.issubset(data.keys()):
			scopes: list[str] = json.loads(data['tagScopes'])
			return Tag(
				uid=data['uid'],
				name=data['name'],
				color=data['color'],
				tagScopes=[TagScope.Deserialize(scope) for scope in scopes]
			)
		raise ValueError(f'Invalid tag data: {data}. Expected keys: uid, name, color, tagScopes')
	
	def Serialize(self) -> dict[str, str]:
		return {
			'uid': self.uid,
			'name': self.name,
			'color': self.color,
			'tagScopes': json.dumps([scope.Serialize() for scope in self.tagScopes])
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

		PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.maxon'
		# TODO: remove this
		self.tags['tag1'] = Tag('tag1', 'T-*', '#FF0000', [
			TagScope()
		])
		self.tags['tag2'] = Tag('tag2', 'T-maxon#*', '#00FF00', [
			TagScope(pluginID=PLUGIN_ID)
		])
		self.tags['tag3'] = Tag('tag3', 'T-maxon#c4d', '#0000FF', [
			TagScope(pluginID=PLUGIN_ID, softwareID='software.c4d')
		])
		self.tags['tag4'] = Tag('tag4', 'T-maxon#c4d+rs', '#FFFF00', [
			TagScope(pluginID=PLUGIN_ID, softwareID='software.c4d'),
			TagScope(pluginID=PLUGIN_ID, softwareID='software.redshift')
		])
		self.tags['tag5'] = Tag('tag5', 'T- table', '#FF00FF', [
			TagScope(viewUID='views/table/*')
		])

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

	def DeleteTag(self, tag: Tag) -> None:
		if not isinstance(tag, Tag):
			raise TypeError(f'Expected Tag, got {type(tag)}')
		if tag.GetUID() not in self.tags:
			return
		del self.tags[tag.GetUID()]
		self.SaveTags()

	def RemoveTag(self, desc: BaseDescriptor, tag: Tag) -> None:
		if not isinstance(tag, Tag):
			raise TypeError(f'Expected Tag, got {type(tag)}')
		if not isinstance(desc, BaseDescriptor):
			raise TypeError(f'Expected BaseDescriptor, got {type(desc)}')
		
		descData: DescriptorDataImpl = self.descDataManager.GetDescriptorData(desc)
		if tag.GetUID() in descData.tags:
			descData.tags.remove(tag.GetUID())
			self.descDataManager.SetDescriptorData(desc, descData)
			self.descDataManager.SaveData()
	
	def AssignTag(self, desc: BaseDescriptor, tag: Tag) -> None:
		if not isinstance(desc, BaseDescriptor):
			raise TypeError(f'Expected BaseDescriptor, got {type(desc)}')
		if not isinstance(tag, Tag):
			raise TypeError(f'Expected Tag, got {type(tag)}')
		
		if tag.GetUID() not in self.tags:
			raise ValueError(f'Tag {tag.GetUID()} does not exist in tags manager')
		
		descData: DescriptorDataImpl = self.descDataManager.GetDescriptorData(desc)
		if tag.GetUID() not in descData.tags:
			descData.tags.append(tag.GetUID())
			self.descDataManager.SetDescriptorData(desc, descData)
			self.descDataManager.SaveData()