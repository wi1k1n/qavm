from qavmapi import BaseQualifier, BaseDescriptor, BaseTileBuilder

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.zbrush'
PLUGIN_VERSION = '0.1.0'

class ZBQualifier(BaseQualifier):
	pass

class ZBDescriptor(BaseDescriptor):
	pass

class ZBTileBuilder(BaseTileBuilder):
	pass

def RegisterModuleSoftware():
	return [
		{
			'id': 'software',  # this is a unique id under the PLUGIN_ID domain
			'name': 'ZBrush',
			# 'description': 'ZBrush software module for QAVM',
			# 'author': 'wi1k1n',
			# 'author_email': 'vfpkjd@gmail.com',

			'qualifier': ZBQualifier,
			'descriptor': ZBDescriptor,
			'tile_builder': ZBTileBuilder,
		}
	]
