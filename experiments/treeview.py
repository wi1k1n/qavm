from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
	QApplication, QMainWindow, QTreeView, QWidget, QVBoxLayout
)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
import sys

from qt_material import apply_stylesheet, get_theme

# Sample plugin data
PLUGIN_REGISTRY = [
	{
		'id': 'software.example1',
		'name': 'Example SW',
		'descriptors': {
			'desc.type.1': {'qualifier': 'ExampleQualifier1', 'descriptor': 'ExampleDescriptor1'},
			'desc.type.2': {'qualifier': 'ExampleQualifier2', 'descriptor': 'ExampleDescriptor2'},
		},
		'views': {
			'tiles': {
				'view.tiles.1': 'ExampleTileBuilder1',
				'view.tiles.2': 'ExampleTileBuilder2',
			},
			'table': {
				'view.table.1': 'ExampleTableBuilder1',
				'view.table.2': 'ExampleTableBuilder2',
			},
			'custom': {
				'view.custom.1': 'ExampleCustomView1',
				'view.custom.2': 'ExampleCustomView2',
			}
		},
		'settings': 'ExampleSettings',
		'menuitems': 'ExampleMenuItems',
	},
	{
		'id': 'software.renderx',
		'name': 'RenderX',
		'descriptors': {
			'desc.rtx': {'qualifier': 'RTXQualifier', 'descriptor': 'RTXDescriptor'}
		},
		'views': {
			'tiles': {
				'view.rtx.tiles': 'RenderXTileBuilder'
			}
		},
		'settings': 'RenderXSettings',
		'menuitems': 'RenderXMenu'
	},
	{
		'id': 'software.analyzepro',
		'name': 'AnalyzePro',
		'descriptors': {},
		'views': {
			'table': {
				'view.ap.table': 'AnalyzeTableView'
			},
			'custom': {
				'view.ap.custom': 'AnalyzeCustomView'
			}
		},
		'settings': 'AnalyzeSettings',
		'menuitems': 'AnalyzeMenuItems'
	}
]

def build_plugin_tree_model(plugin_data):
	model = QStandardItemModel()
	model.setHorizontalHeaderLabels(["Plugin Structure"])

	for plugin in plugin_data:
		root_item = QStandardItem(f"{plugin['name']} ({plugin['id']})")

		# # Descriptors
		# if descriptors := plugin.get("descriptors"):
		# 	descriptors_item = QStandardItem("Descriptors")
		# 	for key, val in descriptors.items():
		# 		desc_item = QStandardItem(key)
		# 		for subkey, subval in val.items():
		# 			child = QStandardItem(f"{subkey}: {subval}")
		# 			desc_item.appendRow(child)
		# 		descriptors_item.appendRow(desc_item)
		# 	root_item.appendRow(descriptors_item)

		# Views (with checkboxes on leaf items)
		if views := plugin.get("views"):
			views_node = QStandardItem("Views")
			for view_type, view_dict in views.items():
				view_type_item = QStandardItem(view_type.capitalize())
				for key, val in view_dict.items():
					view_entry = QStandardItem(f"{key}: {val}")
					view_entry.setCheckable(True)
					view_entry.setCheckState(Qt.CheckState.Unchecked)  # Unchecked by default
					view_type_item.appendRow(view_entry)
				views_node.appendRow(view_type_item)
			root_item.appendRow(views_node)

		# # Settings
		# if settings := plugin.get("settings"):
		# 	settings_item = QStandardItem(f"Settings: {settings}")
		# 	root_item.appendRow(settings_item)

		# Menu Items
		if menuitems := plugin.get("menuitems"):
			menu_item = QStandardItem(f"Menu Items: {menuitems}")
			root_item.appendRow(menu_item)

		model.appendRow(root_item)

	return model

class PluginViewer(QWidget):
	def __init__(self, plugins):
		super().__init__()
		layout = QVBoxLayout(self)
		self.tree_view = QTreeView()
		model = build_plugin_tree_model(plugins)
		self.tree_view.setModel(model)
		self.tree_view.expandAll()
		layout.addWidget(self.tree_view)

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.setWindowTitle("Plugin Viewer")
		self.resize(600, 500)
		self.setCentralWidget(PluginViewer(PLUGIN_REGISTRY))

# THEME = 'dark_purple.xml'
THEME = 'light_purple.xml'

if __name__ == "__main__":
	app = QApplication(sys.argv)
	apply_stylesheet(app, theme=THEME)
	window = MainWindow()
	window.show()
	sys.exit(app.exec())
