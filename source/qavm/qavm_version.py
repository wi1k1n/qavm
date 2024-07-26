import os

import qavm.logs as logs
logger = logs.logger

QAVM_VERSION = '0.1.0'
BUILD_VERSION = ''

def LoadVersionInfo(rootPath: str):
	global BUILD_VERSION, logger
	try:
		with open(os.path.join(rootPath, 'build.txt'), 'r') as f:
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