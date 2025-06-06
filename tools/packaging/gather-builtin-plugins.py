import os, argparse, shutil
from pathlib import Path

def cleanPluginFolder(plugin_folder: Path):
	# remove __pycache__ if it exists
	pycache_path = plugin_folder / '__pycache__'
	if pycache_path.exists() and pycache_path.is_dir():
		print(f'Removing __pycache__ folder: {pycache_path}')
		shutil.rmtree(pycache_path)
	
	# remove .pyc files if they exist
	for pyc_file in plugin_folder.rglob('*.pyc'):
		if pyc_file.is_file():
			print(f'Removing .pyc file: {pyc_file}')
			pyc_file.unlink()

def main():
	parser = argparse.ArgumentParser(description='Gather built-in plugins for packaging')
	parser.add_argument('--pluginsFolder', type=str, action='append', help='Path to the folder containing all required plugin folders (can be used multiple times)', default=[])
	parser.add_argument('--extraPluginFolders', type=str, nargs='+', help='Path to additional plugin folders (takes positional arguments)', default=[])
	parser.add_argument('--destination', type=str, default='builtin_plugins', help='Destination folder for the gathered plugins (default: builtin_plugins)')

	args = parser.parse_args()

	print(f'Gathering built-in plugins from: {args.pluginsFolder}')

	plugins_folders: set[Path] = set()
	for pluginsFolderPathStr in args.pluginsFolder:
		pluginsFolderPath = Path(pluginsFolderPathStr)
		if not pluginsFolderPath.exists():
			print(f'❌ Plugins folder not found: {pluginsFolderPath}')
			continue

		# Iterate over plugin folders inside current plugins folder
		for pluginPath in pluginsFolderPath.iterdir():
			if not pluginPath.is_dir():
				continue
			plugins_folders.add(pluginPath.resolve().absolute())

	if args.extraPluginFolders:
		print(f'Adding extra plugin folders: {args.extraPluginFolders}')
		plugins_folders.update(Path(p) for p in args.extraPluginFolders)

	# Validate paths
	valid_folders = set()
	for folder in plugins_folders:
		if not folder.exists() or not folder.is_dir():
			print(f'❌ Error: {folder} is not a valid directory.')
			continue
		plugin_file = folder / f'{folder.name}.py'
		if not plugin_file.exists() or not plugin_file.is_file():
			print(f'❌ Error: {plugin_file} does not exist or is not a file.')
			continue
		valid_folders.add(folder)

	print(f'Valid plugin folders: {valid_folders}')

	destination_path: Path = Path(args.destination)
	
	if destination_path.is_dir():
		print(f'Removing existing destination folder: {destination_path}')
		try:
			shutil.rmtree(destination_path)
		except Exception as e:
			print(f'❌ Failed to remove existing destination folder {destination_path}: {e}')
			return
		
	if not destination_path.exists():
		print(f'Creating destination folder: {destination_path}')
		destination_path.mkdir(parents=True, exist_ok=True)
	elif not destination_path.is_dir():
		print(f'❌ Error: Destination path {destination_path} is not a directory.')
		return

	for plugin_folder in valid_folders:
		print(f'Gathering plugin: {plugin_folder}')
		dest_path = destination_path / plugin_folder.name
		if dest_path.exists():
			print(f'Plugin folder already exists, deleting: {dest_path}')
			try:
				shutil.rmtree(dest_path)
			except Exception as e:
				print(f'❌ Failed to delete existing plugin folder {dest_path}: {e}')
				continue

		try:
			shutil.copytree(plugin_folder, dest_path)
			print(f'✅ Copied plugin folder to: {dest_path}')
		except Exception as e:
			print(f'❌ Failed to copy plugin folder {plugin_folder} to {dest_path}: {e}')

		cleanPluginFolder(dest_path)

if __name__ == '__main__':
	main()