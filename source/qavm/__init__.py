import sys, os
from functools import partial
from typing import List

# Tweak Windows app group for the custom icon to be used instead of Python one
try:
    from ctypes import windll  # Only exists on Windows.
    myappid = 'in.wi1k.tools.qavm.001'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

import logs
logger = logs.logger

from qavm_version import LoadVersionInfo
from plugin_manager import PluginManager
import utils

if __name__ == "__main__":
	try:
		LoadVersionInfo(os.getcwd())
		
		pluginManager = PluginManager(utils.GetPluginsFolderPath())
		pluginManager.LoadPlugins()

	except Exception as e:
		logger.exception("QAVM application crashed")