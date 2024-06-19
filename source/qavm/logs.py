import sys, os, logging
import utils

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

LOGS_PATH = os.path.join(utils.GetPrefsFolderPath(), 'qavm.log')
loggerFileHandler = logging.FileHandler(LOGS_PATH)
loggerFileHandler.setLevel(logging.ERROR)
loggerFileHandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(loggerFileHandler)