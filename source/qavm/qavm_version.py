from pathlib import Path
import qavm.logs as logs
logger = logs.logger

QAVM_VERSION = '0.2.0'
QAVM_VARIANT = 'dev'
PACKAGE_VERSION = ''
BUILD_VERSION = ''

def LoadVersionInfo(rootPath: Path):
	global BUILD_VERSION, PACKAGE_VERSION, logger
	
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
			PACKAGE_VERSION = buildDateStr
			BUILD_VERSION = buildCommitStr
	except:
		logger.exception('Failed to load build info from build.txt file')

def GetQAVMVersion() -> str:
	return QAVM_VERSION
def GetQAVMVariant() -> str:
	return QAVM_VARIANT
def GetQAVMVersionVariant() -> str:
	return QAVM_VERSION + (f' ({QAVM_VARIANT})' if QAVM_VARIANT else '')
def GetPackageVersion() -> str:
	return PACKAGE_VERSION
def GetBuildVersion() -> str:
	return BUILD_VERSION