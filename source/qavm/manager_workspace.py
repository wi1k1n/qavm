from qavm.manager_plugin import QAVMPlugin, SoftwareHandler, PluginManager

from PyQt6.QtWidgets import QApplication

class QAVMWorkspace:
	def __init__(self, data: dict) -> None:
		self.views: list[str] = data.get('views', [])
		self.menuItems: list[str] = data.get('menuitems', [])

	def IsEmpty(self) -> bool:
		""" Returns True if the workspace has no views or menu items. """
		return not self.views and not self.menuItems
	
	def GetInvolvedPlugins(self) -> tuple[set[QAVMPlugin], set[str]]:
		""" Returns a set of loaded plugins involved in the workspace views (and a set of plugins that were not found). """
		qavmApp = QApplication.instance()
		pluginManager: PluginManager = qavmApp.GetPluginManager()
		plugins: set[QAVMPlugin] = set()
		notFoundPlugins: set[str] = set()
		for viewUID in self.views:
			pluginID: str = QAVMPlugin.FetchPluginIDFromUID(viewUID)
			plugin: QAVMPlugin = pluginManager.GetPlugin(pluginID)
			if plugin:
				plugins.add(plugin)
			else:
				notFoundPlugins.add(pluginID)
		return plugins, notFoundPlugins

	def GetInvolvedSoftwareHandlers(self) -> tuple[set[SoftwareHandler], set[str]]:
		""" Returns a set of software handlers involved in the workspace views (and a set of plugins that were not found). """
		plugins, notFoundPlugins = self.GetInvolvedPlugins()
		softwareHandlers: set[SoftwareHandler] = set()
		for plugin in plugins:
			softwareHandlers.update(plugin.GetSoftwareHandlers().values())
		return softwareHandlers, notFoundPlugins