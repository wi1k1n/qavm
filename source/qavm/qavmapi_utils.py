def ValidateQualifierConfig(config):
	if not isinstance(config, dict):
		return False
	if 'requiredFileList' not in config or not isinstance(config['requiredFileList'], list):
		return False
	if 'negativeFileList' not in config or not isinstance(config['negativeFileList'], list):
		return False
	if 'fileContentsList' not in config or not isinstance(config['fileContentsList'], list):
		return False
	return True