from qavm.manager_plugin import QAVMPlugin, SoftwareHandler, PluginManager, UID

from PyQt6.QtWidgets import QApplication

class QAVMWorkspace:
	def __init__(self, data: dict) -> None:
		views: dict = data.get('views', {})
		if not isinstance(views, dict):
			raise ValueError("Invalid workspace data: 'views' should be a dictionary.")
		
		self.tiles: list[str] = views.get('tiles', [])
		if not isinstance(self.tiles, list):
			raise ValueError("Invalid workspace data: 'tiles' should be a list of UIDs.")
		
		self.table: list[str] = views.get('table', [])
		if not isinstance(self.table, list):
			raise ValueError("Invalid workspace data: 'table' should be a list of UIDs.")
		
		self.custom: list[str] = views.get('custom', [])
		if not isinstance(self.custom, list):
			raise ValueError("Invalid workspace data: 'custom' should be a list of UIDs.")

		self.menuItems: list[str] = data.get('menuitems', [])

	def IsEmpty(self) -> bool:
		""" Returns True if the workspace has no views or menu items. """
		return not self.tiles and not self.table and not self.custom and not self.menuItems
	
	def GetInvolvedPlugins(self) -> tuple[set[QAVMPlugin], set[str]]:
		""" Returns a set of loaded plugins involved in the workspace views (and a set of plugins that were not found). """
		plugins: set[QAVMPlugin] = set()
		notFoundPlugins: set[str] = set()

		# TODO: make it more generic (in case new view types are added in the future)
		tiles, tilesNotFound = self._getInvolvedPluginsUIDs(self.tiles)
		table, tableNotFound = self._getInvolvedPluginsUIDs(self.table)
		custom, customNotFound = self._getInvolvedPluginsUIDs(self.custom)

		plugins.update(tiles)
		plugins.update(table)
		plugins.update(custom)
		notFoundPlugins.update(tilesNotFound)
		notFoundPlugins.update(tableNotFound)
		notFoundPlugins.update(customNotFound)

		return plugins, notFoundPlugins

	def GetInvolvedSoftwareHandlers(self) -> tuple[set[SoftwareHandler], set[str]]:
		""" Returns a set of software handlers involved in the workspace views (and a set of plugins that were not found). """
		plugins, notFoundPlugins = self.GetInvolvedPlugins()
		softwareHandlers: set[SoftwareHandler] = set()
		for plugin in plugins:
			softwareHandlers.update(plugin.GetSoftwareHandlers().values())
		return softwareHandlers, notFoundPlugins
	
	def GetTilesViews(self) -> dict[SoftwareHandler, list[str]]:  # -> {SoftwareHandler: [viewUIDs]}
		""" Returns tiles views in current workspace grouped by software handlers. """
		tilesViews: dict[SoftwareHandler, list[str]] = {}
		for viewUID in self.tiles:
			if plugin := QApplication.instance().GetPluginManager().GetPlugin(viewUID):
				if swHandler := plugin.GetSoftwareHandler(viewUID):
					if swHandler not in tilesViews:
						tilesViews[swHandler] = []
					tilesViews[swHandler].append(viewUID)
		return tilesViews
	
	def AsDict(self) -> dict:
		""" Returns the workspace data as a dictionary. """
		return {
			'views': {
				'tiles': self.tiles,
				'table': self.table,
				'custom': self.custom,
			},
			'menuitems': self.menuItems
		}
	
	def _getInvolvedPluginsUIDs(self, uids: list[str]) -> tuple[set[QAVMPlugin], set[str]]:
		app = QApplication.instance()
		pluginManager: PluginManager = app.GetPluginManager()
		plugins: set[QAVMPlugin] = set()
		notFoundPlugins: set[str] = set()
		for viewUID in uids:
			if plugin := pluginManager.GetPlugin(viewUID):
				plugins.add(plugin)
			else:
				notFoundPlugins.add(viewUID)
		return plugins, notFoundPlugins