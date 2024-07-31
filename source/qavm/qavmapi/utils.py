from pathlib import Path
import os, platform

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



def GetIconFromExecutable(executablePath: Path) -> bytes:
	"""Extracts the icon from the executable file."""
	if PlatformWindows():
		return GetIconFromExecutableWindows(executablePath)
	if PlatformMacOS():
		return GetIconFromExecutableMacOS(executablePath)
	# if PlatformLinux():
	# 	return GetIconFromExecutableLinux(executablePath)
	raise Exception('Unsupported platform')

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
				  ) -> bytes:
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

		with open(icon_path, "rb") as f:
			return f.read()
	return b''

def GetIconFromExecutableWindows(executablePath: Path) -> bytes:
	if executablePath.suffix.lower() != '.exe':
		raise Exception('Not an executable file')
	
	path7z: Path = Path('external/7zip/win/7z.exe')

	icon_files: List[Tuple[str, int]] = find_icons_in_exe(path7z, executablePath)
	if not icon_files:
		return b''
	
	tempPath: Path = GetQAVMTempPath()/'icons'
	return extract_icons(path7z, executablePath, icon_files, tempPath)

def GetIconFromExecutableMacOS(executablePath: Path) -> bytes:
	raise Exception('Not implemented')

##################################################################################################################
############################### ///////////////////////////////////////////////////// ############################
##################################################################################################################