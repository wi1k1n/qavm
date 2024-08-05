import sys, os, argparse

import qavm.logs as logs
logger = logs.logger

from qavm.qavm_version import LoadVersionInfo
from qavm.qavmapp import QAVMApp
import qavm.qavmapi.utils as utils

from qt_material import apply_stylesheet

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
	return parser.parse_args()

def main():
	LoadVersionInfo(os.getcwd())
	WindowsSetupCustomIcon()
	args = ParseArgs()

	try:
		app: QAVMApp = QAVMApp(sys.argv, args)
		apply_stylesheet(app, theme='dark_amber.xml', extra={'density_scale': '-1'})
		sys.exit(app.exec())
	except Exception as e:
		logger.exception("QAVM application crashed")

if __name__ == "__main__":
	main()