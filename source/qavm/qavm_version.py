from pathlib import Path
import qavm.logs as logs
logger = logs.logger

QAVM_VERSION = '0.1.0'
BUILD_VERSION = ''

def LoadVersionInfo(rootPath: Path):
	global BUILD_VERSION, logger
	
	buildFilePath = rootPath / 'build.txt'
	if not buildFilePath.exists():
		logger.exception('Failed to load build info from build.txt file')
		return
	
	try:
		with open(buildFilePath, 'r') as f:
			buildDateStr: str = ''
			buildCommitStr: str = ''
			while line := f.readline():
				line = line.rstrip()
				if not len(line):
					continue
				if not len(buildDateStr):
					buildDateStr = line
					continue
				if not len(buildCommitStr):
					buildCommitStr = line
					break
			BUILD_VERSION = buildCommitStr
	except:
		logger.exception('Failed to load build info from build.txt file')