import os, argparse, shutil, subprocess, sys
from pathlib import Path

def main():
	parser = argparse.ArgumentParser(description='Sign built-in plugins for packaging')
	parser.add_argument('--pluginsFolder', type=str, help='Path to the folder containing all required plugin folders', default='')
	parser.add_argument("--key", type=str, default="signing/keys/private.pem", help="Path to the private key file (default: signing/keys/private.pem)")
	parser.add_argument("--calculatePluginHashPythonScript", type=str, help="Path to the python script that calculates the plugin hash")
	parser.add_argument("--calculatePluginHashFunction", type=str, default="CalculatePluginHash", help="Name of the function that calculates the plugin hash (default: CalculatePluginHash)")
	args = parser.parse_args()

	print(f'Signing built-in plugins from: {args.pluginsFolder}')

	pluginsFolderPath: Path = Path(args.pluginsFolder)
	# Iterate over plugin folders
	for pluginPath in pluginsFolderPath.iterdir():
		if not pluginPath.is_dir():
			continue
		# execute the signing script 'sign-plugin.py' for each plugin
		sign_plugin_script = Path(__file__).parent / 'sign-plugin.py'
		if not sign_plugin_script.exists():
			print(f'❌ Error: sign-plugin.py script not found at {sign_plugin_script}')
			continue

		print(f'Signing plugin: {pluginPath}')

		cliArgs = [
			str(pluginPath),
			'--key', args.key,
			"--calculatePluginHashPythonScript", args.calculatePluginHashPythonScript,
			"--calculatePluginHashFunction", args.calculatePluginHashFunction
		]
		# get same python executable as this script
		pythonExec = Path(sys.executable).absolute()
		try:
			subprocess.run([pythonExec, str(sign_plugin_script)] + cliArgs, check=True)
		except subprocess.CalledProcessError as e:
			print(f'❌ Error signing plugin {pluginPath}: {e}')
			continue

if __name__ == '__main__':
	main()