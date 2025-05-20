import os  # TODO: Get rid of os.path in favor of pathlib
from pathlib import Path
from functools import partial

from PyQt6.QtCore import Qt, QMargins, QPoint, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QCursor, QColor, QBrush, QPainter, QMouseEvent
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QLabel, QTabWidget, QScrollArea, QStatusBar, QTableWidgetItem, QTableWidget,
	QHeaderView, QMenu, QMenuBar, QStyledItemDelegate, QApplication
)

from qavm.manager_plugin import PluginManager, SoftwareHandler
from qavm.manager_settings import SettingsManager, QAVMSettings

from qavm.qavmapi import (
	BaseDescriptor, BaseSettings, BaseTileBuilder, BaseTableBuilder, BaseContextMenu
)
from qavm.utils_gui import FlowLayout
import qavm.qavmapi_utils as qavmapi_utils

import qavm.logs as logs
logger = logs.logger

# TODO: wtf, rename it please!
class MyTableViewHeader(QHeaderView):
	def __init__(self, orientation, parent=None):
			super().__init__(orientation, parent)
			self.setSortIndicatorShown(True)
			self.setSortIndicator(0, Qt.SortOrder.AscendingOrder)

	def mousePressEvent(self, event):
			logicalIndex = self.logicalIndexAt(event.position().toPoint())
			currentOrder = self.sortIndicatorOrder()

			if logicalIndex != self.sortIndicatorSection() or currentOrder == Qt.SortOrder.AscendingOrder:
					self.setSortIndicator(logicalIndex, Qt.SortOrder.DescendingOrder)
			else:
					self.setSortIndicator(logicalIndex, Qt.SortOrder.AscendingOrder)

			self.sectionClicked.emit(logicalIndex)  # Emit the signal for the section clicked

			super().mousePressEvent(event)
			
# TODO: wtf, rename it please!
class MyTableWidget(QTableWidget):
	clickedLeft = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	clickedRight = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	clickedMiddle = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	doubleClickedLeft = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	doubleClickedRight = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	doubleClickedMiddle = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers

	def mousePressEvent(self, event: QMouseEvent):
		if event.button() == Qt.MouseButton.LeftButton:
			print("Left button clicked")
			self.clickedLeft.emit(self.currentRow(), self.currentColumn(), QApplication.keyboardModifiers())
		elif event.button() == Qt.MouseButton.RightButton:
			print("Right button clicked")
			self.clickedRight.emit(self.currentRow(), self.currentColumn(), QApplication.keyboardModifiers())
		elif event.button() == Qt.MouseButton.MiddleButton:
			print("Middle button clicked")
			self.clickedMiddle.emit(self.currentRow(), self.currentColumn(), QApplication.keyboardModifiers())

		super().mousePressEvent(event)

	def mouseDoubleClickEvent(self, event: QMouseEvent):
		index = self.indexAt(event.pos())
		if not index.isValid():
			return

		row = index.row()
		col = index.column()

		if event.button() == Qt.MouseButton.LeftButton:
			print("Left button double clicked")
			self.doubleClickedLeft.emit(row, col, QApplication.keyboardModifiers())
		elif event.button() == Qt.MouseButton.RightButton:
			print("Right button double clicked")
			self.doubleClickedRight.emit(row, col, QApplication.keyboardModifiers())
		elif event.button() == Qt.MouseButton.MiddleButton:
			print("Middle button double clicked")
			self.doubleClickedMiddle.emit(row, col, QApplication.keyboardModifiers())

		super().mouseDoubleClickEvent(event)

class MainWindow(QMainWindow):
	def __init__(self, app, parent: QWidget | None = None) -> None:
		super(MainWindow, self).__init__(parent)

		self.app = app
		
		self.dialogsManager = self.app.GetDialogsManager()
		self.pluginManager: PluginManager = self.app.GetPluginManager()
		self.settingsManager: SettingsManager = self.app.GetSettingsManager()
		self.qavmSettings: QAVMSettings = self.settingsManager.GetQAVMSettings()
		self.softwareSettings: BaseSettings = self.settingsManager.GetSoftwareSettings()
		self.softwareSettings.tilesUpdateRequired.connect(self.UpdateTilesWidget)
		self.softwareSettings.tablesUpdateRequired.connect(self.UpdateTableWidget)

		self.setWindowTitle("QAVM")
		self.resize(1420, 840)
		self.setMinimumSize(350, 250)

		self._setupActions()
		self._setupMenuBar()
		self._setupStatusBar()

		self._setupCentralWidget()

	def _setupActions(self):
		# self.actionSave = QAction("&Save tags and tiles", self)
		# self.actionSave.setShortcut(QKeySequence.StandardKey.Save)

		self.actionPrefs = QAction(QIcon(":preferences.svg"), "&Preferences", self)
		self.actionPrefs.setShortcut("Ctrl+E")
		self.actionPrefs.triggered.connect(self._showPreferences)

		self.actionExit = QAction("&Exit", self, shortcut=QKeySequence.StandardKey.Quit)
		self.actionExit.triggered.connect(self.close)

		self.actionPluginSelection = QAction("Select software", self)
		self.actionPluginSelection.setEnabled(len(self.pluginManager.GetSoftwareHandlers()) > 1)
		self.actionPluginSelection.triggered.connect(self._switchToPluginSelection)

		self.actionRescan = QAction("&Rescan", self)
		self.actionRescan.setShortcut("Ctrl+F5")
		self.actionRescan.triggered.connect(self._rescanSoftware)

		# self.actionAbout = QAction("&About", self)
		# self.actionShortcuts = QAction("&Shortcuts", self)
		# self.actionShortcuts.setShortcut("F1")
		# self.actionReportBug = QAction("&Report a bug", self)
		# self.actionReportBug.setShortcut("Ctrl+Shift+B")
		# self.actionCheckUpdates = QAction("&Check for updates", self)
		
		# self.actionRefresh = QAction("&Refresh", self)
		# self.actionRefresh.setShortcut(QKeySequence.StandardKey.Refresh)
		# self.actionRescan = QAction("Re&scan", self)
		# self.actionRescan.setShortcut("Ctrl+F5")

		# self.actionTags = QAction("&Tags", self)
		# self.actionTags.setShortcut("Ctrl+T")

		# self.actionFiltersort = QAction("Filte&r/Sort", self)
		# self.actionFiltersort.setShortcut("Ctrl+F")

		# self.actionFoldAll = QAction("Toggle &fold all", self)
		# self.actionFoldAll.setShortcut("Ctrl+A")

		# self._createGroupActions()
		
		# self.actionSave.triggered.connect(self._storeData)
		# self.actionPrefs.triggered.connect(self.openPreferences)
		# self.actionExit.triggered.connect(sys.exit)
		# self.actionAbout.triggered.connect(self.about)
		# self.actionCheckUpdates.triggered.connect(CheckForUpdates)
		# self.actionShortcuts.triggered.connect(self.help)
		# self.actionReportBug.triggered.connect(lambda: self._showActivateDialog('trackbugs'))
		# self.actionRefresh.triggered.connect(lambda: self.updateTilesWidget())
		# self.actionRescan.triggered.connect(self.rescan)
		# self.actionTags.triggered.connect(self.toggleOpenTagsWindow)
		# self.actionFiltersort.triggered.connect(self.toggleOpenFilterSortWindow)
		# self.actionFoldAll.triggered.connect(self._toggleFoldAllC4DGroups)
		
		# # Adding help tips
		# newTip = "Create a new file"
		# self.newAction.setStatusTip(newTip)
		# self.newAction.setToolTip(newTip)

	def _setupMenuBar(self):
		menuBar: QMenuBar = self.menuBar()
		menuBar.setNativeMenuBar(True)
		
		fileMenu = menuBar.addMenu('&File')
		# fileMenu.addAction(self.actionSave)
		# fileMenu.addSeparator()
		fileMenu.addAction(self.actionRescan)
		fileMenu.addSeparator()
		fileMenu.addAction(self.actionPluginSelection)
		fileMenu.addSeparator()
		fileMenu.addAction(self.actionExit)
		
		editMenu = menuBar.addMenu("&Edit")
		# editMenu.addAction(self.actionRefresh)
		# editMenu.addAction(self.actionRescan)
		# editMenu.addSeparator()
		# editMenu.addAction(self.actionTags)
		# editMenu.addAction(self.actionFiltersort)
		# fileMenu.addSeparator()
		editMenu.addAction(self.actionPrefs)
		
		viewMenu = menuBar.addMenu("&View")
		# viewMenu.addAction(self.actionFoldAll)
		# viewMenu.addSeparator()
		# # for k, action in self.actionsGrouping.items():
		# # 	viewMenu.addAction(action)
		
		switchMenu = menuBar.addMenu("&Switch")
		def populate_switch_menu():
			switchMenu.clear()
			swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()  # [pluginID, softwareID, SoftwareHandler]
			for pluginID, softwareID, softwareHandler in swHandlers:
				plugin: QAVMPlugin = self.pluginManager.GetPlugin(pluginID)
				swUID: str = f'{pluginID}#{softwareID}'
				title: str = f'{softwareHandler.GetName()} [{plugin.GetName()} @ {plugin.GetVersionStr()}] ({swUID})'
				action = QAction(title, self)
				action.triggered.connect(partial(self._switchToPluginSelection, swUID))
				switchMenu.addAction(action)
		switchMenu.aboutToShow.connect(populate_switch_menu)

		helpMenu = menuBar.addMenu("&Help")
		# helpMenu.addAction(self.actionShortcuts)
		# helpMenu.addAction(self.actionReportBug)
		# helpMenu.addAction(self.actionCheckUpdates)
		# helpMenu.addAction(self.actionAbout)
	
	def _setupStatusBar(self):
		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)

	# TODO: this shouldn't be in constructor!
	def _setupCentralWidget(self):
		self.tabsWidget: QTabWidget = QTabWidget()
		
		self.UpdateTilesWidget()
		self.UpdateTableWidget()

		# TODO: handle case when softwareHandler is None
		softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()
		contextMenu: BaseContextMenu = softwareHandler.GetTileBuilderContextMenuClass()(softwareHandler.GetSettings())
		tileBuilder: BaseTileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings(), contextMenu)

		self.freeMoveWidget = self._createFreeMoveWidget(self.app.GetSoftwareDescriptions(), tileBuilder, self)
		self.tabsWidget.insertTab(2, self.freeMoveWidget, "Free Move")

		self.setCentralWidget(self.tabsWidget)

		self.tabsWidget.currentChanged.connect(self._onTabChanged)
		lastOpenedTab: int = self.qavmSettings.GetLastOpenedTab()
		if lastOpenedTab >= 0 and lastOpenedTab < self.tabsWidget.count():
			self.tabsWidget.setCurrentIndex(lastOpenedTab)

	def _onTabChanged(self, index: int):
		self.qavmSettings.SetLastOpenedTab(index)
		self.qavmSettings.Save()  # TODO: should save now or later once per all changes?
	
	def _createFreeMoveWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget):
		return QLabel("Freemove", parent)
	
	def UpdateTableWidget(self):
		softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()  # TODO: handle case when softwareHandler is None
		contextMenu: BaseContextMenu = softwareHandler.GetTableBuilderContextMenuClass()(softwareHandler.GetSettings())
		tableBuilder = softwareHandler.GetTableBuilderClass()(softwareHandler.GetSettings(), contextMenu)
		if type(tableBuilder) is BaseTableBuilder:
			return
		
		currentTabIndex: int = self.tabsWidget.currentIndex()

		if hasattr(self, 'tableWidget') and self.tableWidget:
			self.tableWidget.deleteLater()
		
		self.tableWidget = self._createTableWidget(self.app.GetSoftwareDescriptions(), tableBuilder, contextMenu, self)
		self.tabsWidget.insertTab(1, self.tableWidget, "Details")
		
		self.tabsWidget.setCurrentIndex(currentTabIndex)

	def _createTableWidget(self, descs: list[BaseDescriptor], tableBuilder: BaseTableBuilder, contextMenu: BaseContextMenu, parent: QWidget):
		tableWidget = MyTableWidget(parent)

		headers: list[str] = tableBuilder.GetTableCaptions()

		tableWidget.setRowCount(len(descs))
		tableWidget.verticalHeader().setVisible(False)

		myHeader = MyTableViewHeader(Qt.Orientation.Horizontal, tableWidget)
		tableWidget.setHorizontalHeader(myHeader)
		tableWidget.setColumnCount(len(headers) + 1)
		tableWidget.setHorizontalHeaderLabels(headers + ['descIdx'])
		tableWidget.hideColumn(len(headers))  # hide descIdx column, this is kinda dirty, but gives more flexibility comparing to qabstracttablemodel and qproxymodel
		tableWidget.setItemDelegate(tableBuilder.GetItemDelegate())
		
		tableWidget.setSortingEnabled(True)
		tableWidget.horizontalHeader().setStretchLastSection(True)
		tableWidget.horizontalHeader().setMinimumSectionSize(150)
		tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		
		tableWidget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
		tableWidget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

		tableWidget.doubleClickedLeft.connect(partial(self._onTableItemDoubleClickedLeft, tableWidget, tableBuilder))
		tableWidget.clickedMiddle.connect(partial(self._onTableItemClickedMiddle, tableWidget, tableBuilder))

		# TODO: this sounds like a temp solution
		self.tableContextMenus: list[QMenu] = list()
		def showContextMenu(pos):
			selectedRowsUnique: set = {idx.row() for idx in tableWidget.selectedIndexes()}
			currentRow = selectedRowsUnique.pop()
			descIdx: int = int(tableWidget.item(currentRow, len(headers)).text())
			self.tableContextMenus[descIdx].exec(QCursor.pos())

		for r, desc in enumerate(descs):
			# rowColor = QBrush(colors[r % 3])
			for c, header in enumerate(headers):
				tableWidgetItem = tableBuilder.GetTableCellValue(desc, c)
				if not isinstance(tableWidgetItem, QTableWidgetItem):
					tableWidgetItem = QTableWidgetItem(tableWidgetItem)
				tableWidget.setItem(r, c, tableWidgetItem)
			tableWidget.setItem(r, len(headers), QTableWidgetItem(str(r)))

			self.tableContextMenus.append(contextMenu.CreateMenu(desc))
		
		tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		tableWidget.customContextMenuRequested.connect(showContextMenu)
		
		return tableWidget
	
	def _onTableItemDoubleClickedLeft(self, tableWidget: QTableWidget, tableBuilder: BaseTableBuilder, row: int, col: int, modifiers: Qt.KeyboardModifier):
		if row < 0 or col < 0:
			return
		descIdx: int = int(tableWidget.item(row, len(tableBuilder.GetTableCaptions())).text())
		tableBuilder.HandleClick(self.app.GetSoftwareDescriptions()[descIdx], row, col, True, 0, QApplication.keyboardModifiers())

	def _onTableItemClickedMiddle(self, tableWidget: QTableWidget, tableBuilder: BaseTableBuilder, row: int, col: int, modifiers: Qt.KeyboardModifier):
		if row < 0 or col < 0:
			return
		descIdx: int = int(tableWidget.item(row, len(tableBuilder.GetTableCaptions())).text())
		tableBuilder.HandleClick(self.app.GetSoftwareDescriptions()[descIdx], row, col, False, 2, QApplication.keyboardModifiers())
	
	def UpdateTilesWidget(self):
		softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()  # TODO: handle case when softwareHandler is None
		contextMenu: BaseContextMenu = softwareHandler.GetTileBuilderContextMenuClass()(softwareHandler.GetSettings())
		tileBuilder: BaseTileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings(), contextMenu)
		if type(tileBuilder) is BaseTileBuilder:
			return

		currentTabIndex: int = self.tabsWidget.currentIndex()

		if hasattr(self, 'tilesWidget') and self.tilesWidget:
			self.tilesWidget.deleteLater()

		self.tilesWidget = self._createTilesWidget(self.app.GetSoftwareDescriptions(), tileBuilder, contextMenu, self)
		self.tabsWidget.insertTab(0, self.tilesWidget, "Tiles")
		
		self.tabsWidget.setCurrentIndex(currentTabIndex)

	def _createTilesWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, contextMenu: BaseContextMenu, parent: QWidget):
		tiles: list[QWidget] = list()

		for desc in descs:
			desc.updated.connect(partial(self._onDescriptorUpdated, desc))
			tileWidget = tileBuilder.CreateTileWidget(desc, parent)
			
			tileWidget.descriptor = desc
			tileWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
			menu = contextMenu.CreateMenu(desc)
			tileWidget.customContextMenuRequested.connect(partial(lambda m, p: m.exec(QCursor.pos()), menu))

			tiles.append(tileWidget)

		flWidget = self._createFlowLayoutWithFromWidgets(self, tiles)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget, self)

		return scrollWidget
	
	# TODO: this is very similar to UpdateTilesWidget, code duplication
	def _onDescriptorUpdated(self, desc: BaseDescriptor):
		if not hasattr(self, 'tilesWidget'):
			return
		
		scrollArea = self.tilesWidget
		flWidget = scrollArea.widget()
		if not flWidget or not isinstance(flWidget.layout(), FlowLayout):
			return

		flowLayout: FlowLayout = flWidget.layout()

		for i in range(flowLayout.count()):
			widget = flowLayout.itemAt(i).widget()
			if getattr(widget, 'descriptor', None) == desc:
				# Remove old widget
				flowLayout.removeWidget(widget)
				widget.deleteLater()

				# Create and insert new tile
				softwareHandler = self.pluginManager.GetSoftwareHandler(self.qavmSettings.GetSelectedSoftwareUID())
				contextMenu = softwareHandler.GetTileBuilderContextMenuClass()(softwareHandler.GetSettings())
				tileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings(), contextMenu)

				newTile = tileBuilder.CreateTileWidget(desc, self)
				newTile.descriptor = desc
				newTile.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
				menu = contextMenu.CreateMenu(desc)
				newTile.customContextMenuRequested.connect(partial(lambda m, p: m.exec(QCursor.pos()), menu))

				# Optional: keep tiles sorted or in original order
				flowLayout.insertWidget(i, newTile)
				break

		self.tableWidget.update()


	def _createFlowLayoutWithFromWidgets(self, parent, widgets: list[QWidget]):
		flWidget = QWidget(parent)
		flWidget.setMinimumWidth(50)

		flowLayout = FlowLayout(flWidget, margin=5, hspacing=5, vspacing=5)
		flowLayout.setSpacing(0)

		for widget in widgets:
			widget.setFixedWidth(widget.sizeHint().width())
			flowLayout.addWidget(widget)

		return flWidget
	
	def _wrapWidgetInScrollArea(self, widget, parent):
		scrollWidget = QScrollArea(parent)
		scrollWidget.setWidgetResizable(True)
		scrollWidget.setWidget(widget)
		return scrollWidget
	
	def _switchToPluginSelection(self, swUID: str = ''):
		# TODO: this should probably has clearer handling
		self.qavmSettings.SetSelectedSoftwareUID(swUID)
		self.app.selectedSoftwareUID = swUID
		self.qavmSettings.Save()
		self.dialogsManager.GetPluginSelectionWindow().show()
		self.close()
	
	def _rescanSoftware(self):
		self.app.ResetSoftwareDescriptions()
		self.UpdateTilesWidget()


	def _showPreferences(self):
		prefsWindow: QMainWindow = self.app.GetDialogsManager().GetPreferencesWindow()
		prefsWindow.show()
		prefsWindow.activateWindow()
