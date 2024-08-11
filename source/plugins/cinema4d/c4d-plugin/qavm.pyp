import c4d
import sys, threading, time, datetime as dt

PLUGIN_ID = 1064093

isC4DStarted = False

def waitForC4DInit():
	global isC4DStarted
	print(f'Waiting for Cinema to start... {dt.datetime.now()}')
	for i in range(60):
		time.sleep(1)
		if isC4DStarted:
			break
	print(f'Cinema started: {dt.datetime.now()}')

class QAVMBackendPlugin(c4d.plugins.CommandData):
	def Execute(self, doc):
		c4d.gui.MessageDialog("Hello World!")
		return True


def PluginMessage(id, data):
	global isC4DStarted

	if id == c4d.C4DPL_STARTACTIVITY:
		print("QAVM Backend Plugin: Start Activity")
		print(data)

	if id == c4d.C4DPL_PROGRAM_STARTED:
		print("QAVM Backend Plugin: Program Started")
		print(data) #print data

		isC4DStarted = True
		
		# plugin: c4d.plugins.BasePlugin
		# for plugin in  c4d.plugins.FilterPluginList(c4d.PLUGINTYPE_VIDEOPOST, True):
		# 	if (plugin.GetInfo() & c4d.PLUGINFLAG_VIDEOPOST_ISRENDERER):
		# 		print (plugin.GetName())

		try:
			import redshift
			print("Redshift found")
			print(f'Redshift plugin version: {redshift.GetPluginVersion()}')
			print(f'Redshift plugin build: {redshift.GetPluginBuild()}')
			print(f'Redshift core version: {redshift.GetCoreVersion()}')
		except:
			pass
			
		return True

	if id == c4d.C4DPL_COMMANDLINEARGS:
		print("QAVM Backend Plugin: Arguments")
		print(sys.argv) #print arguments
		return True

	return False

if __name__ == "__main__":
	print("QAVM Backend Plugin: Registering Plugin")
	
	x = threading.Thread(target=waitForC4DInit)
	x.start()
	
	c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID, str="QAVM Backend", info=0, help='', dat=QAVMBackendPlugin(), icon=None)