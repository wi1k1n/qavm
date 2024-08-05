import os, shutil, hashlib
from pathlib import Path
import importlib.util

IGNORE_DIRS_LIST = set(['__pycache__'])

def file_hash(file_path):
	"""Compute the hash of a file."""
	hash_algo = hashlib.sha256()
	with open(file_path, 'rb') as f:
		while chunk := f.read(8192):
			hash_algo.update(chunk)
	return hash_algo.hexdigest()

def CopyPluginFolder(sourceFolderPath: str, targetFolderPath: str) -> None:
	sourceFolderPath = os.path.abspath(sourceFolderPath)
	targetFolderPath = os.path.abspath(targetFolderPath)

	if not os.path.isdir(sourceFolderPath):
		raise ValueError(f"Source folder '{sourceFolderPath}' does not exist or is not a directory.")
	
	if not os.path.exists(targetFolderPath):
		os.makedirs(targetFolderPath)
		print(f'> Created plugin folder: {targetFolderPath}')
	
	pluginFiles: set = set()

	# Iterate through all files in the source folder
	for root, dirs, files in os.walk(sourceFolderPath):
		relative_path = os.path.relpath(root, sourceFolderPath)
		target_root = os.path.join(targetFolderPath, relative_path)

		if not os.path.exists(target_root):
			os.makedirs(target_root)
			print(f'> Created target folder: {target_root}')

		for file in files:
			source_file_path = os.path.join(root, file)
			target_file_path = os.path.join(target_root, file)

			print(f'>>> {source_file_path} -> {target_file_path}')
			pluginFiles.add(os.path.abspath(target_file_path))

			result = ''
			if os.path.exists(target_file_path):
				source_hash = file_hash(source_file_path)
				target_hash = file_hash(target_file_path)
				
				if source_hash != target_hash:
					shutil.copy2(source_file_path, target_file_path)
					result = 'UPDATED'
				else:
					result = 'SKIPPED'
			else:
				shutil.copy2(source_file_path, target_file_path)
				result = 'COPIED'
			print(f'\t{result}')
	
	# Double check if there are any files in the target folder that are not in the source folder
	leftoverFiles = set()
	global IGNORE_DIRS_LIST
	for root, dirs, files in os.walk(targetFolderPath):
		# TODO: this line below accounts for paths in IGNORE_DIRS_LIST relative to plugins folder (e.g. inner folders with same names would still trigger exception)
		dirs[:] = [d for d in dirs if os.path.relpath(os.path.join(root, d), targetFolderPath) not in IGNORE_DIRS_LIST]
		for file in files:
			target_file_path = os.path.join(root, file)
			if os.path.abspath(target_file_path) not in pluginFiles:
				leftoverFiles.add(target_file_path)
	if len(leftoverFiles):
		print(f'> Leftover files found:')
		for file in leftoverFiles:
			path, fileName = os.path.split(file)
			print(f'\t{fileName} in {path}')
		raise ValueError(f'Leftover files found in target folder')

def mainCopyPluginFiles(sourcePluginsFolderPath: str, targetPluginsFolderPath: str):
	print('--- DEPLOY_MODE: Copying plugin files ---')

	for dir in os.scandir(sourcePluginsFolderPath):
		if not dir.is_dir():
			continue
		sourcePluginFolderPath = dir.path
		targetPluginFolderPath = os.path.join(targetPluginsFolderPath, dir.name)
		print(f'> Deploying "{dir.name}"')
		print(f'\t{sourcePluginFolderPath} -> {targetPluginFolderPath}')

		CopyPluginFolder(sourcePluginFolderPath, targetPluginFolderPath)

def mainCreateJunction(sourcePluginsFolderPath: str, targetPluginsFolderPath: str):
	print('--- DEPLOY_MODE: Creating junction ---')

	sourcePluginFolderPath: Path = Path(sourcePluginsFolderPath)
	targetPluginFolderPath: Path = Path(targetPluginsFolderPath)

	if targetPluginFolderPath.exists():
		if targetPluginFolderPath.is_junction():
			return print(f'> Target plugins folder is already a junction: {targetPluginFolderPath}')
		print(f'> Removing target plugins folder: {targetPluginFolderPath}')
		shutil.rmtree(targetPluginFolderPath)
	
	if qavm_utils.PlatformWindows():
		import _winapi
		print(f'> Creating junction: {sourcePluginFolderPath} -> {targetPluginFolderPath}')
		_winapi.CreateJunction(str(sourcePluginFolderPath), str(targetPluginFolderPath))
		return
	
	if qavm_utils.PlatformMacOS():
		raise NotImplementedError('Not implemented for MacOS yet')
		os.symlink(sourcePluginFolderPath, targetPluginFolderPath, target_is_directory=True)
		return print(f'> Created symlink: {sourcePluginFolderPath} -> {targetPluginFolderPath}')

if __name__ == "__main__":
	print('deploy_plugins.py - START')

	sourcePluginsFolderPath = os.path.join('source', 'plugins')

	spec = importlib.util.spec_from_file_location('qavm_utils', os.path.join('source', 'qavm', 'qavmapi', 'utils.py'))
	qavm_utils = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(qavm_utils)
	if not hasattr(qavm_utils, 'GetDefaultPluginsFolderPath'):
		print('Failed to load source/utils.py')
		exit(1)
	targetPluginsFolderPath = qavm_utils.GetDefaultPluginsFolderPath()
	print(f'> Deploying plugins from {sourcePluginsFolderPath} to {targetPluginsFolderPath}')  

	# mainCopyPluginFiles(sourcePluginsFolderPath, targetPluginsFolderPath)
	mainCreateJunction(sourcePluginsFolderPath, targetPluginsFolderPath)
	
	print('deploy_plugins.py - FINISHED')