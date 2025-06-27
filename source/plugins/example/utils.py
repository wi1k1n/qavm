import logging
import qavm.qavmapi.utils as qutils

def GetLogger(name):
	return None
	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
	_logger = logging.getLogger(name)

	LOGS_PATH = qutils.GetQAVMDataPath()/'qavm-example.log'
	loggerFileHandler = logging.FileHandler(LOGS_PATH)
	loggerFileHandler.setLevel(logging.ERROR)
	loggerFileHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
	_logger.addHandler(loggerFileHandler)
	return _logger