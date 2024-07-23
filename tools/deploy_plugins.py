import os, shutil, hashlib
import importlib.util

IGNORE_DIRS_LIST = set(['__pycache__'])

def file_hash(file_path):
    """Compute the hash of a file."""
    hash_algo = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_algo.update(chunk)
    return hash_algo.hexdigest()

# TODO: using hardlink is potentially easier
def DeployFolder(sourceFolderPath: str, targetFolderPath: str) -> None:
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

if __name__ == "__main__":
    print('deploy_plugins.py - START')

    sourcePluginsFolderPath = os.path.join('source', 'plugins')

    spec = importlib.util.spec_from_file_location('qavm_utils', os.path.join('source', 'qavm', 'qavmapi', 'utils.py'))
    qavm_utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qavm_utils)
    if not hasattr(qavm_utils, 'GetPluginsFolderPath'):
        print('Failed to load source/utils.py')
        exit(1)
    targetPluginsFolderPath = qavm_utils.GetPluginsFolderPath()
    print(f'> Deploying plugins from {sourcePluginsFolderPath} to {targetPluginsFolderPath}')    

    for dir in os.scandir(sourcePluginsFolderPath):
        if not dir.is_dir():
            continue
        sourcePluginFolderPath = dir.path
        targetPluginFolderPath = os.path.join(targetPluginsFolderPath, dir.name)
        print(f'> Deploying "{dir.name}"')
        print(f'\t{sourcePluginFolderPath} -> {targetPluginFolderPath}')

        DeployFolder(sourcePluginFolderPath, targetPluginFolderPath)
    
    print('deploy_plugins.py - FINISHED')