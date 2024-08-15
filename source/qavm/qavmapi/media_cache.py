import json, time, shutil
from pathlib import Path

from qavm.qavmapi import utils

# Singleton pattern: https://refactoring.guru/design-patterns/singleton/python/example
class MediaCacheMeta(type):
	_instances = {}
	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(MediaCacheMeta, cls).__call__(*args, **kwargs)
		return cls._instances[cls]

class CacheEntry:
	def __init__(self, path: Path, timeCacheCreated: int):
		self.path: Path = path
		self.timeCacheCreated: int = timeCacheCreated
	
	@staticmethod
	def fromDict(data: dict):
		if not isinstance(data, dict) or 'path' not in data or 'timeCacheCreated' not in data:
			raise Exception('Invalid CacheEntry data')
		return CacheEntry(Path(data['path']), data['timeCacheCreated'])
	def toDict(self) -> dict:
		return {'path': str(self.path), 'timeCacheCreated': self.timeCacheCreated}

""" MediaCache manages media files in a cached manner. One can use to optimize the access to media files. """
class MediaCache(metaclass=MediaCacheMeta):
	def __init__(self):
		self.dirPath: Path = utils.GetQAVMCachePath()/'mediacache'
		self.indexPath: Path = self.dirPath/'index.json'
		self.mediaPath: Path = self.dirPath/'media'
		self.cache: dict[str, CacheEntry]	= {}

		self._load()
	
	def GetCachedPath(self, mediaUID: str) -> Path | None:
		if cacheEntry := self.cache.get(mediaUID, None):
			return self.dirPath/cacheEntry.path
		return None

	def GetTimeCacheCreated(self, mediaUID: str) -> int:
		if cacheEntry := self.cache.get(mediaUID, None):
			return cacheEntry.timeCacheCreated
		return 0
	
	def CacheMedia(self, mediaUID: str, path: Path):
		hash: str = utils.GetHashFile(path)
		targetPath: Path = self.mediaPath/f'{hash}{path.suffix}'
		try:
			targetPath.parent.mkdir(parents=True, exist_ok=True)
			shutil.copy2(path, targetPath)
		except Exception as e:
			print(f'Failed to copy media file to cache: {e}')
			return
		
		self.cache[mediaUID] = CacheEntry(targetPath.relative_to(self.dirPath), int(time.time() * 1000))
		self._save()
	
	def _save(self):
		with open(self.indexPath, 'w') as f:
			json.dump({'index': {k: v.toDict() for k, v in self.cache.items()}}, f)

	def _load(self):
		self.dirPath.mkdir(parents=True, exist_ok=True)
		if not self.indexPath.exists():
			self._save()
			return
		
		with open(self.indexPath, 'r') as f:
			if data := json.load(f):
				# TODO: do a proper validation pass
				if not isinstance(data, dict) or 'index' not in data or not isinstance(data['index'], dict):
					raise Exception('Invalid icons cache data')
				self.cache = {k: CacheEntry.fromDict(v) for k, v in data['index'].items()}