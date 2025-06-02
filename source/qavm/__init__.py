import sys, os, argparse

import cProfile, pstats

import qavm.logs as logs
logger = logs.logger

from qavm.qavm_version import LoadVersionInfo, GetBuildVersion, GetQAVMVersion, GetPackageVersion
from qavm.qavmapp import QAVMApp
import qavm.qavmapi.utils as utils
from qavm.qavmapi.gui import GetThemeName, SetTheme

def WindowsSetupCustomIcon():
	# Tweak Windows app group for the custom icon to be used instead of Python one
	try:
		from ctypes import windll  # Only exists on Windows.
		myappid = 'in.wi1k.tools.qavm'
		windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
	except ImportError:
		pass

def ParseArgs() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description='QAVM - Quick Application Version Manager')
	# TODO: make this handle list of paths
	parser.add_argument('--pluginsFolder', type=str, help='Path to the plugins folder (Default: %APPDATA%/qavm/plugins)', default=utils.GetDefaultPluginsFolderPath())
	parser.add_argument('--extraPluginsFolder', type=str, action='append', help='Path to an additional plugins folder (can be used multiple times)', default=[])
	parser.add_argument('--extraPluginPath', type=str, action='append', help='Path to an additional plugin to load (can be used multiple times)', default=[])
	parser.add_argument('--selectedSoftwareUID', type=str, help='UID of the selected software (Default: empty)', default='')
	args = parser.parse_args()
	
	provided_args = {
		k: v for k, v in vars(args).items()
		if v != parser.get_default(k)
	}
	logger.info(f'Provided arguments: {provided_args}')

	return args

def main():
	LoadVersionInfo(utils.GetQAVMRootPath())
	print(f'QAVM Version: {GetQAVMVersion()}')
	print(f'Package Version: {GetPackageVersion()}')
	print(f'Build Version: {GetBuildVersion()}')

	if utils.PlatformWindows():
		WindowsSetupCustomIcon()
	
	args = ParseArgs()

	# profiler = cProfile.Profile()
	# profiler.enable()

	try:
		app: QAVMApp = QAVMApp(sys.argv, args)
		app.exec()
	except Exception as e:
		logger.exception("QAVM application crashed")
		
	# profiler.disable()
	# profiler.dump_stats("app_profile.prof")

if __name__ == "__main__":
	main()