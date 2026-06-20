from __future__ import annotations
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from enum import StrEnum

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from qavm.manager_plugin import UID
from qavm.qavmapi import BaseDescriptor, BaseTag

if TYPE_CHECKING:
	from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorDataImpl

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
	
class BaseTagImpl(BaseTag):
	def __init__(self, uid: str, name: str, color: str, tagScopes: list[TagScope] = list(), order: int = 0, description: str = '') -> None:
		self.uid: str = uid
		self.name: str = name
		self.color: str = color
		self.tagScopes: list[TagScope] = tagScopes  # empty is the same as global scope
		self.order: int = order  # display order in the tags palette (lower comes first)
		self.description: str = description

	def GetUID(self) -> str:
		return self.uid

	def GetName(self) -> str:
		return self.name
	
	def GetColor(self) -> str:
		return self.color
	
	def GetScopes(self) -> list[TagScope]:
		return self.tagScopes

	def GetDescription(self) -> str:
		return self.description

	def GetOrder(self) -> int:
		return self.order

	def SetOrder(self, order: int) -> None:
		self.order = order

	def IsApplicableInContext(self, pluginID: str, softwareID: str, viewUID: str) -> bool:
		""" Returns True if the tag is applicable in the given plugin/software/view context. An empty scope list means global (always applicable). """
		if not self.tagScopes:
			return True  # empty is the same as global scope
		return any(scope.IsApplicable(pluginID, softwareID, viewUID) for scope in self.tagScopes)

	@staticmethod
	def Deserialize(data: dict[str, str]) -> BaseTagImpl:
		if not isinstance(data, dict):
			raise TypeError(f'Expected dict, got {type(data)}')
		if {'uid', 'name', 'color', 'tagScopes'}.issubset(data.keys()):
			scopes: list[str] = json.loads(data.get('tagScopes', '[]'))
			return BaseTagImpl(
				uid=data['uid'],
				name=data['name'],
				color=data['color'],
				tagScopes=[TagScope.Deserialize(scope) for scope in scopes],
				order=int(data.get('order', 0)),
				description=data.get('description', '')
			)
		raise ValueError(f'Invalid tag data: {data}. Expected keys: uid, name, color, tagScopes')
	
	def Serialize(self) -> dict[str, str | int]:
		return {
			'uid': self.uid,
			'name': self.name,
			'color': self.color,
			'tagScopes': json.dumps([scope.Serialize() for scope in self.tagScopes]),
			'order': self.order,
			'description': self.description
		}

	def __repr__(self) -> str:
		return f'BaseTag(uid={self.uid}, name={self.name}, color={self.color}, tagScopes={self.tagScopes}, order={self.order}, description={self.description})'
	
	def __eq__(self, other: object) -> bool:
		if not isinstance(other, BaseTagImpl):
			return False
		return (self.uid == other.uid and
				self.name == other.name and
				self.color == other.color and
				self.tagScopes == other.tagScopes and
				self.order == other.order and
				self.description == other.description)

class TagsManager(QObject):
	# Emitted whenever the set of tags or any tag's data changes (add/update/delete/reorder), so that
	# views showing tags (e.g. the tags palette) can refresh regardless of where the change originated.
	tagsChanged = pyqtSignal()

	def __init__(self, tagsDataFilepath: Path, descDataManager: DescriptorDataManager) -> None:
		super().__init__()
		self.tagsDataFilepath: Path = tagsDataFilepath
		self.descDataManager: DescriptorDataManager = descDataManager

		self.tags: dict[str, BaseTagImpl] = dict()  # Using a dict for faster lookups by tag uid

		# PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.maxon'
		# # TODO: remove this
		# self.tags['tag1'] = BaseTagImpl('tag1', 'T-*', '#FF0000', [
		# 	TagScope()
		# ])
		# self.tags['tag2'] = BaseTagImpl('tag2', 'T-maxon#*', '#00FF00', [
		# 	TagScope(pluginID=PLUGIN_ID)
		# ])
		# self.tags['tag3'] = BaseTagImpl('tag3', 'T-maxon#c4d', '#0000FF', [
		# 	TagScope(pluginID=PLUGIN_ID, softwareID='software.c4d')
		# ])
		# self.tags['tag4'] = BaseTagImpl('tag4', 'T-maxon#c4d+rs', '#FFFF00', [
		# 	TagScope(pluginID=PLUGIN_ID, softwareID='software.c4d'),
		# 	TagScope(pluginID=PLUGIN_ID, softwareID='software.redshift')
		# ])
		# self.tags['tag5'] = BaseTagImpl('tag5', 'T- table', '#FF00FF', [
		# 	TagScope(viewUID='views/table/*')
		# ])

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
					t: BaseTagImpl = BaseTagImpl.Deserialize(tag)
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

	def GetTags(self) -> dict[str, BaseTagImpl]:
		return self.tags

	def GetTagsOrdered(self) -> list[BaseTagImpl]:
		""" Returns the tags sorted by their display order (ascending). """
		return sorted(self.tags.values(), key=lambda tag: tag.GetOrder())

	def ReorderTags(self, orderedTagUIDs: list[str], dontUpdateDescriptors: bool = False) -> None:
		""" Reassigns the display order of tags based on the given list of tag UIDs and persists the change. """
		if not isinstance(orderedTagUIDs, list):
			raise TypeError(f'Expected list, got {type(orderedTagUIDs)}')
		order: int = 0
		for tagUID in orderedTagUIDs:
			tag: BaseTagImpl | None = self.tags.get(tagUID, None)
			if tag is None:
				continue
			tag.SetOrder(order)
			order += 1
		# Any tags not present in orderedTagUIDs keep being appended at the end
		for tag in self.tags.values():
			if tag.GetUID() not in orderedTagUIDs:
				tag.SetOrder(order)
				order += 1
		self.SaveTags()
		self.tagsChanged.emit()
		if not dontUpdateDescriptors:
			# Reordering tags affects how they render on every descriptor that has them assigned, so we need to update all of them
			affectedDescUIDs: list[str] = [descUID for descUID, descData in self.descDataManager.data.items() if any(tagUID in descData.tags for tagUID in self.tags.keys())]
			QTimer.singleShot(0, lambda: self.descDataManager.NotifyDescriptorsDataUpdated(affectedDescUIDs))  # timer to avoid "label stuck to cursor issue"
	
	def ReorderDescriptorTags(self, desc: BaseDescriptor, orderedVisibleTagUIDs: list[str]) -> None:
		""" Reorders the tags assigned to a single descriptor so the ones in orderedVisibleTagUIDs follow
		that order, persisting and notifying listeners.

		Only the tags listed in orderedVisibleTagUIDs are rearranged; any other assigned tags (e.g. tags
		not visible in the current plugin/software/view scope) keep their existing slots. This lets the
		Tags cell reorder just the bubbles it shows without disturbing out-of-scope assignments. """
		if not isinstance(desc, BaseDescriptor):
			raise TypeError(f'Expected BaseDescriptor, got {type(desc)}')
		if not isinstance(orderedVisibleTagUIDs, list):
			raise TypeError(f'Expected list, got {type(orderedVisibleTagUIDs)}')
		descData: DescriptorDataImpl = self.descDataManager.GetDescriptorData(desc)
		visibleSet: set[str] = set(orderedVisibleTagUIDs)
		orderedIter = iter(orderedVisibleTagUIDs)
		# Walk the existing list, substituting the visible tags with the new ordering in their slots.
		newTags: list[str] = [next(orderedIter) if uid in visibleSet else uid for uid in descData.tags]
		if newTags == descData.tags:
			return
		descData.tags = newTags
		self.descDataManager.SetDescriptorData(desc, descData)
		self.descDataManager.SaveData()
		self.descDataManager.NotifyDescriptorsDataUpdated([desc.GetUID()])

	def GetTag(self, tagUID: str) -> BaseTagImpl | None:
		if not isinstance(tagUID, str):
			raise TypeError(f'Expected str, got {type(tagUID)}')
		return self.tags.get(tagUID, None)
	
	def AddTag(self, tag: BaseTagImpl) -> None:
		if not isinstance(tag, BaseTagImpl):
			raise TypeError(f'Expected BaseTagImpl, got {type(tag)}')
		if tag.GetUID() in self.tags:
			logger.warning(f'BaseTag {tag} already exists, skipping addition')
			return
		nextOrder: int = (max((t.GetOrder() for t in self.tags.values()), default=-1) + 1)
		tag.SetOrder(nextOrder)
		self.tags[tag.GetUID()] = tag
		self.SaveTags()
		self.tagsChanged.emit()

	def UpdateTag(self, tag: BaseTagImpl) -> None:
		""" Persists changes made to an existing tag (e.g. after editing name/color/scopes) and refreshes affected descriptors. """
		if not isinstance(tag, BaseTagImpl):
			raise TypeError(f'Expected BaseTagImpl, got {type(tag)}')
		if tag.GetUID() not in self.tags:
			raise ValueError(f'BaseTag {tag.GetUID()} does not exist in tags manager')
		self.tags[tag.GetUID()] = tag
		self.SaveTags()
		self.tagsChanged.emit()
		# Name/color/scope changes affect how the tag renders on every descriptor that has it assigned
		affectedDescUIDs: list[str] = [descUID for descUID, descData in self.descDataManager.data.items() if tag.GetUID() in descData.tags]
		self.descDataManager.NotifyDescriptorsDataUpdated(affectedDescUIDs)

	def DeleteTag(self, tag: BaseTagImpl, dontUpdateDescriptors: bool = False) -> None:
		if not isinstance(tag, BaseTagImpl):
			raise TypeError(f'Expected BaseTagImpl, got {type(tag)}')
		tagUID = tag.GetUID()
		if tagUID not in self.tags:
			return
		# Purge the tag UID from every descriptor that has it assigned
		affectedDescUIDs: list[str] = []
		for descUID, descData in self.descDataManager.data.items():
			if tagUID in descData.tags:
				descData.tags.remove(tagUID)
				affectedDescUIDs.append(descUID)
		if affectedDescUIDs:
			self.descDataManager.SaveData()
		del self.tags[tagUID]
		self.SaveTags()
		self.tagsChanged.emit()
		if not dontUpdateDescriptors:
			self.descDataManager.NotifyDescriptorsDataUpdated(affectedDescUIDs)

	def RemoveTag(self, desc: BaseDescriptor, tag: BaseTagImpl) -> None:
		if not isinstance(tag, BaseTagImpl):
			raise TypeError(f'Expected BaseTagImpl, got {type(tag)}')
		if not isinstance(desc, BaseDescriptor):
			raise TypeError(f'Expected BaseDescriptor, got {type(desc)}')
		
		descData: DescriptorDataImpl = self.descDataManager.GetDescriptorData(desc)
		if tag.GetUID() in descData.tags:
			descData.tags.remove(tag.GetUID())
			self.descDataManager.SetDescriptorData(desc, descData)
			self.descDataManager.SaveData()
			self.descDataManager.NotifyDescriptorsDataUpdated([desc.GetUID()])
	
	def AssignTag(self, desc: BaseDescriptor, tag: BaseTagImpl) -> None:
		if not isinstance(desc, BaseDescriptor):
			raise TypeError(f'Expected BaseDescriptor, got {type(desc)}')
		if not isinstance(tag, BaseTagImpl):
			raise TypeError(f'Expected BaseTagImpl, got {type(tag)}')
		
		if tag.GetUID() not in self.tags:
			raise ValueError(f'BaseTag {tag.GetUID()} does not exist in tags manager')
		
		descData: DescriptorDataImpl = self.descDataManager.GetDescriptorData(desc)
		if tag.GetUID() not in descData.tags:
			descData.tags.append(tag.GetUID())
			self.descDataManager.SetDescriptorData(desc, descData)
			self.descDataManager.SaveData()
			self.descDataManager.NotifyDescriptorsDataUpdated([desc.GetUID()])