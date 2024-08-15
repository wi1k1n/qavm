import c4d, maxon
import sys, os, threading, platform, json, time, datetime as dt
from pathlib import Path
from typing import Any

BACKEND_PLUGIN_ID = 1064093
BACKEND_PLUGIN_VERSION = '0.1.0'


BACKEND_PLUGIN_DATA_FILENAME = 'qavm_data.json'  # name of the file in the C4D_PREFS_DIR where the backend plugin stores its data

def GetQAVMCachePath() -> Path:  # TODO: inject here code from qavm.qavmapi.utils
	def PlatformWindows():
		return platform.system() == 'Windows'
	def PlatformMacOS():
		return platform.system() == 'Darwin'
	appDataPath: Path = Path.home()
	if PlatformWindows():
		appDataPath = Path(os.getenv('APPDATA'))
	if PlatformMacOS():
		appDataPath = Path.home()/'Library/Preferences'
	return appDataPath/'qamv/cache'

QAVM_DEFAULT_CACHE_FILEPATH = GetQAVMCachePath()/'c4d/index.json'  # path to the qavm data-file

QAVM_ARGS: dict[str, Any] = {  # argument: default_value
	'qavm_c4dCacheDataPath': QAVM_DEFAULT_CACHE_FILEPATH,
	'qavm_c4dUID': '0',
}

# isC4DStarted = False

# def waitForC4DInit():
# 	global isC4DStarted
# 	print(f'Waiting for Cinema to start... {dt.datetime.now()}')
# 	for i in range(60):
# 		time.sleep(1)
# 		if isC4DStarted:
# 			break
# 	print(f'Cinema started: {dt.datetime.now()}')

class QAVMBackendPlugin(c4d.plugins.CommandData):
	def Execute(self, doc):
		c4d.gui.MessageDialog("Hello World!")
		return True

def StoreBackendPluginData():
	global QAVM_ARGS

	prefsDirPath: maxon.Url = maxon.Application.GetUrl(maxon.APPLICATION_URLTYPE.PREFS_DIR)
	backendPluginDataPath: maxon.Url = prefsDirPath + BACKEND_PLUGIN_DATA_FILENAME

	redshiftData: dict = None

	try:
		import redshift
		
		print("Redshift found")
		print(f'Redshift plugin version: {redshift.GetPluginVersion()}')
		print(f'Redshift plugin build: {redshift.GetPluginBuild()}')
		print(f'Redshift core version: {redshift.GetCoreVersion()}')

		redshiftData = {
			"plugin_version": redshift.GetPluginVersion(),
			"plugin_build": redshift.GetPluginBuild(),
			"core_version": redshift.GetCoreVersion()
		}
	except:
		pass

	backendPluginData: dict = {
		"qavm_backend_plugin_version": BACKEND_PLUGIN_VERSION,
		"plugins": {
			"redshift": redshiftData
		}
	}
	
	if 'qavm_c4dUID' in QAVM_ARGS:
		backendPluginData['uid'] = QAVM_ARGS['qavm_c4dUID']

	backendPluginDataPathStr = backendPluginDataPath.GetSystemPath()
	with open(backendPluginDataPathStr, 'w') as f:
		f.write(json.dumps(backendPluginData))

def UpdateQAVMCacheData():
	global QAVM_ARGS
	if 'qavm_c4dUID' not in QAVM_ARGS:
		return
	
	thisC4D_QAVM_UID: str = QAVM_ARGS['qavm_c4dUID']
	thisC4D_PrefsPath: Path = Path(maxon.Application.GetUrl(maxon.APPLICATION_URLTYPE.PREFS_DIR).GetSystemPath())

	print(f'[QAVM] #-DEBUG-# qavm_c4dUID: {thisC4D_QAVM_UID}')
	print(f'[QAVM] #-DEBUG-# qavm_c4dCacheDataPath: {QAVM_ARGS["qavm_c4dCacheDataPath"]}')
	print(f'[QAVM] #-DEBUG-# thisC4D_PrefsPath: {thisC4D_PrefsPath}')

	c4dCacheDataPath: Path = Path(QAVM_ARGS['qavm_c4dCacheDataPath'])
	if not c4dCacheDataPath.exists():
		c4dCacheDataPath.parent.mkdir(parents=True, exist_ok=True)
		with open(c4dCacheDataPath, 'w') as f:
			json.dump({}, f)
	
	c4dCacheData: dict = {}
	with open(c4dCacheDataPath, 'r') as f:
		c4dCacheData: dict = json.load(f)

	if thisC4D_QAVM_UID not in c4dCacheData:
		c4dCacheData[thisC4D_QAVM_UID] = {
			'prefsPath': str(thisC4D_PrefsPath),
			'lastUpdate': dt.datetime.now().isoformat()
		}
	
	if 'prefsPath' not in c4dCacheData[thisC4D_QAVM_UID]:
		print(f'[QAVM] Missing prefsPath in cache data for QAVM UID: {thisC4D_QAVM_UID}')
		return

	qavmIndexedC4DPrefsPath: str = c4dCacheData[thisC4D_QAVM_UID]['prefsPath']
	if Path(qavmIndexedC4DPrefsPath).resolve() != thisC4D_PrefsPath.resolve():
		print(f'[QAVM] Different prefs paths, QAVM indexed path is replaced with currently actual.\nQAVM indexed:\n\t{qavmIndexedC4DPrefsPath}\nCurrently actual:\n\t{str(thisC4D_PrefsPath)}')
		c4dCacheData[thisC4D_QAVM_UID].update(str(thisC4D_PrefsPath))
	
	with open(c4dCacheDataPath, 'w') as f:
		json.dump(c4dCacheData, f)

def foo():
	global QAVM_ARGS
	if 'qavm_c4dUID' not in QAVM_ARGS:
		print('[QAVM] Missing qavm_c4dUID argument')
		return
		
	StoreBackendPluginData()
	UpdateQAVMCacheData()

def PluginMessage(id, data):
	global QAVM_ARGS
	# global isC4DStarted

	if id == c4d.C4DPL_STARTACTIVITY:
		print("QAVM Backend Plugin: Start Activity")
		print(data)

	if id == c4d.C4DPL_PROGRAM_STARTED:
		print("QAVM Backend Plugin: Program Started")
		print(data) #print data

		# isC4DStarted = True
		
		# plugin: c4d.plugins.BasePlugin
		# for plugin in  c4d.plugins.FilterPluginList(c4d.PLUGINTYPE_VIDEOPOST, True):
		# 	if (plugin.GetInfo() & c4d.PLUGINFLAG_VIDEOPOST_ISRENDERER):
		# 		print (plugin.GetName())
		
		return True
	
	if id == c4d.C4DPL_COMMANDLINEARGS:
		print("QAVM Backend Plugin: Arguments")
		print(sys.argv) #print arguments

		for v in sys.argv:
			if not v.startswith('qavm_'):
				continue
			tokens: list[str] = v.split('=', 1)
			if len(tokens) != 2:
				print(f'[QAVM] Invalid argument: {v}')
				continue
			arg: str = tokens[0]
			val: str = tokens[1]
			if arg not in QAVM_ARGS:
				print(f'[QAVM] Unknown argument: {arg}')
				continue
			QAVM_ARGS[arg] = val
		
		foo()

		return True
	return False

if __name__ == "__main__":
	print("QAVM Backend Plugin: Registering Plugin")
	
	# x = threading.Thread(target=waitForC4DInit)
	# x.start()
	
	c4d.plugins.RegisterCommandPlugin(id=BACKEND_PLUGIN_ID, str="QAVM Backend", info=0, help='', dat=QAVMBackendPlugin(), icon=None)