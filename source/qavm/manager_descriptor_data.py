from qavm.qavmapi import BaseDescriptor





class DescriptorDataManager(object):
	def LoadDescriptorsData(self, workspace: 'QAVMWorkspace') -> None:
		if not workspace:
			return
		
		plugins, _ = workspace.GetInvolvedPlugins()
		for plugin in plugins:
			for (sID, swHandler) in plugin.GetSoftwareHandlers().items():
				descClasses: dict[str, type[BaseDescriptor]] = swHandler.GetDescriptorClasses()
				print(f'Loading descriptors for {swHandler.GetName()} ({len(descClasses)} classes)')