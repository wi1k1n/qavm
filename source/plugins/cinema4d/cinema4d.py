class C4DQualifier:
	pass

class C4DDescriptor:
	pass

class C4DTileBuilder:
	pass

def RegisterPluginSoftware():
	return [
		{
			'id': 'in.wi1k.tools.qavm.plugin.cinema4d.software',
			'version': '0.1.0',
			'name': 'Cinema 4D',
			'description': 'Cinema 4D plugin for QAVM',
			'author': 'wi1k1n',
			'author_email': 'vfpkjd@gmail.com',

			'qualifier': C4DQualifier,
			'descriptor': C4DDescriptor,
			'tile_builder': C4DTileBuilder,
		}
	]
