import os, platform, json, hashlib
from pathlib import Path
from typing import Any

def PlatformWindows():
	return platform.system() == 'Windows'
def PlatformLinux():
	return platform.system() == 'Linux'
def PlatformMacOS():
	return platform.system() == 'Darwin'


def GetPluginsFolderPath() -> Path:
	return GetQAVMDataPath()/'plugins'

def GetQAVMDataPath() -> Path:
	path: str = GetAppDataPath()/'qamv'
	os.makedirs(path, exist_ok=True)
	return path

def GetPrefsFolderPath() -> Path:
	return GetQAVMDataPath()/'preferences'

def GetQAVMTempPath() -> Path:
	return GetTempDataPath()/'qavm'

def GetQAVMCachePath() -> Path:
	return GetQAVMDataPath()/'cache'

def GetAppDataPath() -> Path:
	"""Returns the path to the AppData folder for the current user."""
	if PlatformWindows():
		return Path(os.getenv('APPDATA'))
	if PlatformMacOS():
		return Path.home()/'Library/Preferences'
	# if PlatformLinux():
	# 	return os.path.expanduser('~')
	raise Exception('Unsupported platform')

def GetTempDataPath() -> Path:
	"""Returns the path to the temporary directory."""
	if PlatformWindows():
		return Path(os.getenv('TEMP'))
	if PlatformMacOS():
		raise Exception('Not implemented')
		return Path('/tmp')
	# if PlatformLinux():
	# 	return Path('/tmp')
	raise Exception('Unsupported platform')



def getFileHash(filePath: Path, hashAlgo='sha256'):
	CHUNKSIZE = 32 * 1024 * 1024  # 32 MB
	hashFunc = hashlib.new(hashAlgo)
	with open(filePath, 'rb') as file:
		while chunk := file.read(CHUNKSIZE):
			hashFunc.update(chunk)
	return hashFunc.hexdigest()[:12]

def GetIconFromExecutable(executablePath: Path) -> Path | None:
	"""Searched for cached icon file and extracts if not found"""
	iconsCache: dict[str, dict[str, Any]] = dict()

	# Load cache data
	iconsCacheDirPath: Path = GetQAVMCachePath()/'icons'
	iconsCacheDataPath: Path = iconsCacheDirPath/'icons-data.json'
	if iconsCacheDataPath.exists():
		with open(iconsCacheDataPath, 'r') as f:
			data = json.load(f)
			if data is not None and isinstance(data, dict) and len(data):
				iconsCache = data
	
	# Check if icon is cached
	icPathToKey: dict[Path, str] = {Path(k): k for k in iconsCache.keys()}
	if executablePath not in icPathToKey:
		return ExtractIconFromExecutable(executablePath)
	
	iconData: dict[str, Any] = iconsCache[icPathToKey[executablePath]]
	if iconData is None or not isinstance(iconData, dict) \
			or 'execHash' not in iconData or 'iconFilePath' not in iconData:
		return ExtractIconFromExecutable(executablePath)
	
	iconPath: Path = iconsCacheDirPath/iconData['iconFilePath']

	# Check if executable file has changed
	execHash: str = getFileHash(executablePath)
	if execHash.lower() != iconData['execHash'].lower() or not iconPath.exists():
		return ExtractIconFromExecutable(executablePath)
	
	return iconPath

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
		logger.error(f'Failed to extract icon from executable: {executablePath}')
		return None
	
	# Cache icon	
	iconsCacheDirPath: Path = GetQAVMCachePath()/'icons'
	iconsCacheDataPath: Path = iconsCacheDirPath/'icons-data.json'

	execHash: str = getFileHash(executablePath)
	iconTargetPath: Path = iconsCacheDirPath/f'{execHash}{iconPath.suffix}'
	if iconTargetPath.exists():
		iconTargetPath.unlink()
	if not iconTargetPath.parent.exists():
		iconTargetPath.parent.mkdir(parents=True, exist_ok=True)
	shutil.copy(iconPath, iconTargetPath)

	# Load existing cache data
	iconsCache: dict[str, dict[str, Any]] = dict()
	if iconsCacheDataPath.exists():  # TODO: code repetition
		with open(iconsCacheDataPath, 'r') as f:
			data = json.load(f)
			if data is not None and isinstance(data, dict) and len(data):
				iconsCache = data
	
	# Update current entry
	iconsCache[str(executablePath)] = {
		'execHash': execHash,
		'iconFilePath': str(iconTargetPath.relative_to(iconsCacheDirPath))
	}

	# Save cache data
	with open(iconsCacheDataPath, 'w') as f:
		json.dump(iconsCache, f)

	return iconPath

##################################################################################################################
############################### TODO: Implement this part as a binding to the C++ code ###########################
##################################################################################################################

"""Utility script for extracting icons from executable files using 7zip.

Accepts .exe files, links to .exe files, and directories containing .exe files.

Example usage:
	python icon_extractor.py 'my/exe.exe'
	python icon_extractor.py 'my/exe/folder'
	python icon_extractor.py 'my/exe.lnk'


Author: Maatss
Date: 2023-10-03
GitHub: https://github.com/Maatss/PyIconExtractor
Version: 1.0
"""

"""Uses 7zip prepared by daemondevin: https://github.com/daemondevin/7-ZipPortable"""

from pathlib import Path
import subprocess, re, shutil, imghdr
from subprocess import CompletedProcess
from typing import List, Tuple, Optional


def find_icons_in_exe(path_7zip: Path, exe_path: Path) -> List[Tuple[str, int]]:
	"""Find icons in an executable file.

	Args:
		exe_path (Path): Path to executable file.

	Returns:
		Optional[List[Tuple[str, int]]]: List of icon file paths and sizes.
	"""

	# List file contents using 7zip program
	list_cmd: List[str] = [str(path_7zip), "l", str(exe_path)]
	result: CompletedProcess[str] = subprocess.run(list_cmd, capture_output=True, text=True, check=False)
	output: str = result.stdout
	if result.returncode != 0:
		print(f"\t\t- Failed to list file contents, skipping '{exe_path}'.")
		return []

	# Find icon files
	icon_files: List[Tuple[str, int]] = []
	for line in output.split("\n"):
		# Search lines containing: "*\ICON\*"
		# I.e. files in the ICON directory
		match_ico_files: Optional[re.Match[str]] = re.search(r".+[\/\\]ICON[\/\\]\S+", line)

		# Skip if no match
		if not match_ico_files:
			continue

		# Extract icon file name and size
		# Example:
		#                                    Size   Compressed  Name
		# "                    .....       270398       270376  .rsrc\1033\ICON\1.ico"
		# "                    .....         2398         1376  .rsrc\1033\ICON\2"
		fields: List[str] = line.split()
		icon_file_path: str = fields[-1]
		icon_file_size: int = int(fields[-3])
		icon_files.append((icon_file_path, icon_file_size))

	# Return list sorted by size (large to small)
	icon_files.sort(key=lambda entry: entry[1], reverse=True)
	return icon_files

def extract_icon_from_exe(path_7zip: Path, exe_path: Path, inner_icon_file_path: str, output_dir_path: Path) -> Optional[Path]:
	"""Extract an icon from an executable file.

	Args:
		exe_path (Path): Path to executable file.
		inner_icon_file_path (str): Path to icon file inside executable file.
		output_path (Path): Path to where to save the icon file.

	Returns:
		bool: True if successful, else False.
	"""

	outerIconFilePath: Path = output_dir_path / Path(inner_icon_file_path).name
	if outerIconFilePath.exists():
		outerIconFilePath.unlink()

	# Extract icon file using 7zip program
	extract_cmd: List[str] = [str(path_7zip), "e", str(exe_path), inner_icon_file_path, f"-o{str(output_dir_path)}"]
	result: CompletedProcess[str] = subprocess.run(extract_cmd, capture_output=True, text=True, check=False)
	if result.returncode != 0:
		print(f"\t\t\t- Failed to extract icon file '{inner_icon_file_path}' from '{exe_path}'.")
		return None

	# If missing a file extension, guess it from the file header
	extracted_file_path: Path = output_dir_path / Path(inner_icon_file_path).name
	if extracted_file_path.suffix.lower() == "":
		print("\t\t\t- Guessing file extension from file header.")
		extension: str = imghdr.what(extracted_file_path)
		if extension:
			extracted_file_path = extracted_file_path.rename(extracted_file_path.with_suffix(f".{extension}"))
		else:
			print(f"\t\t\t\t- Failed to guess file extension for '{extracted_file_path}'.")
			return None

	# Return the path to the extracted icon file
	return extracted_file_path

# b = extract_icons(path7z, executablePath, icon_files, tempPath)
def extract_icons(path_7zip: Path,
					exe_file_path: Path,
					icon_files: List[Tuple[str, int]],
				#   output_dir_path: Path,
					temp_output_dir_path: Path,
				#   extract_largest_only: bool
					) -> Path | None:
	"""Extract icons from executable files, and save them to output directory.

	Args:
		path_7zip (Path): Path to 7zip program.
		exe_file_path (Path): Path to executable file.
		icon_files (List[Tuple[str, int]]): List of icon file paths and sizes.
		output_dir_path (Path): Path to where to store extracted icons.
		temp_output_dir_path (Path): Path to temporary output directory.
		extract_largest_only (bool): Extract only the largest icon file.

	Returns:
		bool: True if successful, else False.
	"""

	for file_index, (inner_icon_file_path, icon_file_size) in enumerate(icon_files, start=1):
		# print(f"\t\t- ({file_index}) Extracting icon named '{inner_icon_file_path}' ({icon_file_size} bytes).")
		icon_path: Optional[Path] = extract_icon_from_exe(path_7zip, exe_file_path, inner_icon_file_path, temp_output_dir_path)
		
		# Skip if extraction failed
		if not icon_path:
			print("\t\t\t- Failed to extract icon.")
			continue

		return icon_path
	return None

def GetIconFromExecutableWindows(executablePath: Path) -> Path | None:
	if executablePath.suffix.lower() != '.exe':
		raise Exception('Not an executable file')
	
	path7z: Path = Path('external/7zip/win/7z.exe')

	icon_files: List[Tuple[str, int]] = find_icons_in_exe(path7z, executablePath)
	if not icon_files:
		return None
	
	tempPath: Path = GetQAVMTempPath()/'icons'
	return extract_icons(path7z, executablePath, icon_files, tempPath)

def GetIconFromExecutableMacOS(executablePath: Path) -> bytes:
	raise Exception('Not implemented')

##################################################################################################################
############################### ///////////////////////////////////////////////////// ############################
##################################################################################################################