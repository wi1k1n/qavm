"""
copyright
"""
import example_simple
import example_images

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.example'  # unique plugin id in the domain format, e.g. 'com.example.plugin'
PLUGIN_VERSION = '0.2.0'  # version in a [0-999].[0-999].[0-999] format, e.g. 0.1.0 (major.minor.patch)
PLUGIN_VARIANT = ''  # extra (str) information about the plugin version, e.g. 'Alpha'
PLUGIN_NAME = '(Example Plugin)'  # the name of the plugin as it will be displayed in the QAVM
PLUGIN_DEVELOPER = 'Ilya Mazlov (mazlov.i.a@gmail.com)'  # developer's name or organization
PLUGIN_WEBSITE = 'https://github.com/wi1k1n/qavm'  # plugin's website or repository URL

"""
QAVM can be extended by plugins. Each plugin is represented by a folder with a python script that has the same name as the folder.

Each plugin can implement multiple modules. Modules can be of different types, e.g. software, settings, etc.
"""

def RegisterPluginSoftware():
	return example_simple.REGISTRATION_DATA \
		+ example_images.REGISTRATION_DATA

def RegisterPluginWorkspaces():
	return {
		**example_simple.WORKSPACES_DATA,
		**example_images.WORKSPACES_DATA,
	}