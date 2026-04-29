import io
import json
import plistlib
import struct
from pathlib import Path
from typing import Any
import logging

import pefile
from PIL import Image
logging.getLogger("PIL").setLevel(logging.WARNING)  # Suppress PIL warnings

from qavm.qavmapi.utils import GetQAVMCachePath, GetQAVMTempPath, GetHashFile, PlatformWindows, PlatformMacOS
from qavm.qavmapi.media_cache import MediaCache

RT_ICON = 3
RT_GROUP_ICON = 14

def GetIconFromExecutable(executablePath: Path) -> Path | None:
	"""Searched for cached icon file and extracts if not found"""
	
	"""
	Icons cache data structure:
	{
		"execIndex": {
			"executablePath1": {
				"execHash": "sha256[:12]",
				"iconHash": "sha256[:12]",
			}, {
			...
			}
		}
	}
	"""
	mediaCache: MediaCache = MediaCache()

	iconPathsIndex: dict = dict()

	# Load cache data
	iconsCacheDirPath: Path = GetQAVMCachePath()/'icons'
	iconsCacheDataPath: Path = iconsCacheDirPath/'icons-data.json'
	if iconsCacheDataPath.exists():
		with open(iconsCacheDataPath, 'r') as f:
			data = json.load(f)
			if data is not None:
				# TODO: do a proper validation pass
				if not isinstance(data, dict) or 'execIndex' not in data:
					raise Exception('Invalid icons index data')
				iconPathsIndex = data
	
	execIndex: dict = iconPathsIndex.get('execIndex', dict())
	
	# Check if executable is indexed
	icPathToKey: dict[Path, str] = {Path(k): k for k in execIndex.keys()}
	if executablePath not in icPathToKey:
		return ExtractIconFromExecutable(executablePath)
	
	# Executable is indexed, check if icon is cached
	execPathStr: str = icPathToKey[executablePath]
	execData: dict = execIndex[execPathStr]
	if 'iconHash' not in execData:
		return ExtractIconFromExecutable(executablePath)
	cachedPath: Path | None = mediaCache.GetCachedPath(execData['iconHash'])
	if cachedPath is None or not cachedPath.exists():
		return ExtractIconFromExecutable(executablePath)
	
	# Check if executable file has changed
	execHash: str = GetHashFile(executablePath)
	if execHash.lower() != execData['execHash'].lower():
		return ExtractIconFromExecutable(executablePath)
	
	return cachedPath

def ExtractIconFromExecutable(executablePath: Path) -> Path | None:
	"""Extracts the icon from the executable file."""
	iconPath: Path | None = None
	if PlatformWindows():
		iconPath = GetIconFromExecutableWindows(executablePath)
	if PlatformMacOS():
		iconPath = GetIconFromExecutableMacOS(executablePath)
	# if PlatformLinux():
	# 	iconPath = GetIconFromExecutableLinux(executablePath)
	if iconPath is None:
		print(f'Failed to extract icon from executable: {executablePath}')  # TODO: make logger a part of qavmapi and use it instead
		return None
	
	mediaCache: MediaCache = MediaCache()

	### Cache icon
	iconsCacheDirPath: Path = GetQAVMCachePath()/'icons'
	iconsCacheDataPath: Path = iconsCacheDirPath/'icons-data.json'
	
	# Load existing cache data. Check GetIconFromExecutable() description for data structure
	iconsCache: dict[str, dict[str, Any]] = dict()
	if iconsCacheDataPath.exists():  # TODO: code repetition
		with open(iconsCacheDataPath, 'r') as f:
			data = json.load(f)
			if data is not None and isinstance(data, dict):
				iconsCache = data

	execHash: str = GetHashFile(executablePath)
	iconHash: str = GetHashFile(iconPath)

	# Update executable index
	if 'execIndex' not in iconsCache:
		iconsCache['execIndex'] = dict()
	iconsCache['execIndex'][str(executablePath)] = {
		'execHash': execHash,
		'iconHash': iconHash
	}

	mediaCache.CacheMedia(iconHash, iconPath)

	# Save cache data
	iconsCacheDirPath.mkdir(parents=True, exist_ok=True)
	with open(iconsCacheDataPath, 'w') as f:
		json.dump(iconsCache, f)

	return iconPath

def _build_ico_from_group(group_data: bytes, icons: dict[int, bytes]) -> bytes:
	"""Converts RT_GROUP_ICON resource data + RT_ICON resources into a valid .ico file."""
	reserved, icon_type, count = struct.unpack_from("<HHH", group_data, 0)

	if reserved != 0 or icon_type != 1:
		raise RuntimeError("Invalid icon group resource")

	entries = []
	offset = 6 + count * 16
	icon_payloads = []

	for i in range(count):
		entry_offset = 6 + i * 14

		width, height, color_count, reserved_byte, planes, bit_count, size, icon_id = struct.unpack_from(
			"<BBBBHHIH",
			group_data,
			entry_offset,
		)

		icon_data = icons.get(icon_id)
		if icon_data is None:
			continue

		entries.append(
			struct.pack(
				"<BBBBHHII",
				width,
				height,
				color_count,
				reserved_byte,
				planes,
				bit_count,
				len(icon_data),
				offset,
			)
		)

		icon_payloads.append(icon_data)
		offset += len(icon_data)

	if not entries:
		raise RuntimeError("Icon group exists, but no matching icon images were found")

	header = struct.pack("<HHH", 0, 1, len(entries))
	return header + b"".join(entries) + b"".join(icon_payloads)


def _load_largest_image_from_ico_bytes(ico_data: bytes) -> Image.Image:
	"""Loads all frames from ICO data and returns the largest one."""
	img = Image.open(io.BytesIO(ico_data))

	best = None
	best_area = -1

	for frame in range(getattr(img, "n_frames", 1)):
		try:
			img.seek(frame)
		except EOFError:
			break

		candidate = img.convert("RGBA")
		area = candidate.width * candidate.height

		if area > best_area:
			best = candidate.copy()
			best_area = area

	if best is None:
		raise RuntimeError("Could not decode ICO image")

	return best


def GetIconFromExecutableWindows(executablePath: Path) -> Path | None:
	"""Extracts the largest icon from a Windows PE file (.exe or .dll) using pefile."""
	if executablePath.suffix.lower() not in {'.exe', '.dll'}:
		return None

	try:
		pe = pefile.PE(str(executablePath))
	except pefile.PEFormatError:
		return None

	if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
		return None

	icon_groups: dict[int, bytes] = {}
	icons: dict[int, bytes] = {}

	for resource_type in pe.DIRECTORY_ENTRY_RESOURCE.entries:
		if resource_type.id == RT_GROUP_ICON:
			for name_entry in resource_type.directory.entries:
				for lang_entry in name_entry.directory.entries:
					data_rva = lang_entry.data.struct.OffsetToData
					size = lang_entry.data.struct.Size
					data = pe.get_memory_mapped_image()[data_rva:data_rva + size]
					icon_groups[name_entry.id] = data

		elif resource_type.id == RT_ICON:
			for name_entry in resource_type.directory.entries:
				for lang_entry in name_entry.directory.entries:
					data_rva = lang_entry.data.struct.OffsetToData
					size = lang_entry.data.struct.Size
					data = pe.get_memory_mapped_image()[data_rva:data_rva + size]
					icons[name_entry.id] = data

	if not icon_groups:
		return None

	# Take the first icon group (most apps have one main icon group)
	group_data = next(iter(icon_groups.values()))
	ico_data = _build_ico_from_group(group_data, icons)

	image = _load_largest_image_from_ico_bytes(ico_data)

	tempPath: Path = GetQAVMTempPath() / 'icons'
	tempPath.mkdir(parents=True, exist_ok=True)
	outputPath: Path = tempPath / f'{executablePath.stem}.png'
	image.save(outputPath)

	return outputPath


def GetIconFromExecutableMacOS(executablePath: Path) -> Path | None:
	"""Extracts icon from a macOS .app bundle or .icns file."""
	if executablePath.suffix.lower() == '.app':
		info_plist = executablePath / "Contents" / "Info.plist"
		if not info_plist.exists():
			return None

		with info_plist.open("rb") as f:
			info = plistlib.load(f)

		icon_name = info.get("CFBundleIconFile")
		if not icon_name:
			return None

		if not icon_name.endswith(".icns"):
			icon_name += ".icns"

		icns_path = executablePath / "Contents" / "Resources" / icon_name
		if not icns_path.exists():
			return None
	elif executablePath.suffix.lower() == '.icns':
		icns_path = executablePath
	else:
		return None

	try:
		img = Image.open(icns_path)
	except Exception:
		return None

	best = None
	best_area = -1

	for frame in range(getattr(img, "n_frames", 1)):
		try:
			img.seek(frame)
		except EOFError:
			break

		candidate = img.convert("RGBA")
		area = candidate.width * candidate.height

		if area > best_area:
			best = candidate.copy()
			best_area = area

	if best is None:
		return None

	tempPath: Path = GetQAVMTempPath() / 'icons'
	tempPath.mkdir(parents=True, exist_ok=True)
	outputPath: Path = tempPath / f'{executablePath.stem}.png'
	best.save(outputPath)

	return outputPath