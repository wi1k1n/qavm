# Contains some QAVM API related utility functions

def ValidateQualifierConfig(config):
	if not isinstance(config, dict):
		return False
	
	def checkAttrList(config, key, type):
		if key not in config or not isinstance(config[key], list):
			return False
		if config[key] and not isinstance(config[key][0], type):
			return False
		return True
	
	return checkAttrList(config, 'requiredFileList', str) \
		and checkAttrList(config, 'requiredDirList', str) \
		and checkAttrList(config, 'negativeFileList', str) \
		and checkAttrList(config, 'negativeDirList', str) \
		and checkAttrList(config, 'fileContentsList', tuple)
	
	return True