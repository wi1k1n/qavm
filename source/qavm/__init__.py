import sys, os

import logs
logger = logs.logger

from qavm_version import LoadVersionInfo
from qavmapp import QAVMApp

from qt_material import apply_stylesheet

def WindowsSetupCustomIcon():
	# Tweak Windows app group for the custom icon to be used instead of Python one
	try:
		from ctypes import windll  # Only exists on Windows.
		myappid = 'in.wi1k.tools.qavm'
		windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
	except ImportError:
		pass

def main():
	LoadVersionInfo(os.getcwd())
	WindowsSetupCustomIcon()

	try:
		app: QAVMApp = QAVMApp(sys.argv)
		apply_stylesheet(app, theme='dark_amber.xml', extra={'density_scale': '-1'})
		sys.exit(app.exec())
	except Exception as e:
		logger.exception("QAVM application crashed")

if __name__ == "__main__":
	main()