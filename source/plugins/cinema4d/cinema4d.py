from qavmapi import BaseQualifier, BaseDescriptor, BaseTileBuilder

PLUGIN_ID = 'in.wi1k.tools.qavm.plugin.cinema4d'
PLUGIN_VERSION = '0.1.0'

class C4DQualifier(BaseQualifier):
	pass

class C4DDescriptor(BaseDescriptor):
	pass

class C4DTileBuilder(BaseTileBuilder):
	pass

class C4DExampleQualifier(BaseQualifier):
	pass

class C4DExampleDescriptor(BaseDescriptor):
	pass

class C4DExampleTileBuilder(BaseTileBuilder):
	pass

def RegisterModuleSoftware():
	return [
		{
			'id': 'software',  # this is a unique id under the PLUGIN_ID domain
			'name': 'Cinema 4D',
			# 'description': 'Cinema 4D software module for QAVM',
			# 'author': 'wi1k1n',
			# 'author_email': 'vfpkjd@gmail.com',

			'qualifier': C4DQualifier,
			'descriptor': C4DDescriptor,
			'tile_builder': C4DTileBuilder,
		},
		{
			'id': 'software.example',  # this is a unique id under the PLUGIN_ID domain
			'name': 'C4D - Example',
			# 'description': 'Cinema 4D software module for QAVM',
			# 'author': 'wi1k1n',
			# 'author_email': 'vfpkjd@gmail.com',

			'qualifier': C4DExampleQualifier,
			'descriptor': C4DExampleDescriptor,
			'tile_builder': C4DExampleTileBuilder,
		}
	]
