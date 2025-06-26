import os  # TODO: Get rid of os.path in favor of pathlib
from pathlib import Path
from functools import partial
from typing import Type, Optional

from PyQt6.QtCore import Qt, QMargins, QPoint, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QCursor, QColor, QBrush, QPainter, QMouseEvent
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QLabel, QTabWidget, QScrollArea, QStatusBar, QTableWidgetItem, QTableWidget,
	QHeaderView, QMenu, QMenuBar, QStyledItemDelegate, QApplication, QAbstractItemView, QMessageBox,
	QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QLineEdit, QHBoxLayout,
	QSizePolicy, QTableView, QTableWidgetSelectionRange, 
)

from qavm.manager_plugin import PluginManager, SoftwareHandler, UID, QAVMWorkspace
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings

from qavm.qavmapi import (
	BaseDescriptor, BaseSettings, BaseTileBuilder, BaseTableBuilder,
	BaseCustomView, SoftwareBaseSettings, BaseMenuItem, BaseBuilder, 
)
from qavm.qavmapi.utils import PlatformMacOS, PlatformWindows, PlatformLinux
from qavm.utils_gui import FlowLayout
from qavm.qavm_version import GetBuildVersion, GetPackageVersion, GetQAVMVersion, GetQAVMVersionVariant

import qavm.logs as logs
logger = logs.logger

# TODO: wtf, rename it please!
class MyTableViewHeader(QHeaderView):
	def __init__(self, orientation, parent=None):
		super().__init__(orientation, parent)
		self.setSortIndicatorShown(True)
		self.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(self._showContextMenu)
		self.setSectionsMovable(True)

		self._mousePressedPos = None
		self._mousePressedSection = -1

	def _showContextMenu(self, pos: QPoint):
		menu = QMenu(self)

		tableWidget = self.parent()
		if not isinstance(tableWidget, QTableWidget):
			return

		columnCount = tableWidget.columnCount() - 1  # Exclude the last column (descIdx)
		for col in range(columnCount):
			header_label = tableWidget.horizontalHeaderItem(col).text()
			action = QAction(header_label, menu)
			action.setCheckable(True)
			action.setChecked(not tableWidget.isColumnHidden(col))
			action.toggled.connect(lambda checked, col=col: tableWidget.setColumnHidden(col, not checked))
			menu.addAction(action)
   
		menu.exec(self.mapToGlobal(pos))
  
	def mousePressEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			self._mousePressedPos = event.pos()
			self._mousePressedSection = self.logicalIndexAt(self._mousePressedPos)
		super().mousePressEvent(event)
		
	def mouseReleaseEvent(self, event):
		if event.button() == Qt.MouseButton.LeftButton:
			releasedSection = self.logicalIndexAt(event.pos())
			if (
				releasedSection == self._mousePressedSection
				and (event.pos() - self._mousePressedPos).manhattanLength() < 4
			):
				currentOrder = self.sortIndicatorOrder()
				if releasedSection != self.sortIndicatorSection() or currentOrder == Qt.SortOrder.AscendingOrder:
					self.setSortIndicator(releasedSection, Qt.SortOrder.DescendingOrder)
				else:
					self.setSortIndicator(releasedSection, Qt.SortOrder.AscendingOrder)
				# self.sectionClicked.emit(releasedSection)  # Emit the signal for the section clicked
		super().mouseReleaseEvent(event)
			
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

class MyTabWidget(QTabWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self._uidToWidget = {}  # uid → QWidget

	def addTabWithUid(self, widget: QWidget, title: str, uid: str):
		if uid in self._uidToWidget:
			raise ValueError(f"UID '{uid}' already exists")
		self._uidToWidget[uid] = widget
		self.addTab(widget, title)

	def removeTabByUid(self, uid: str):
		widget = self._uidToWidget.pop(uid, None)
		if widget is not None:
			index = self.indexOf(widget)
			if index != -1:
				self.removeTab(index)

	def setTabVisibleByUid(self, uid: str, visible: bool):
		widget = self._uidToWidget.get(uid)
		if widget:
			index = self.indexOf(widget)
			self.tabBar().setTabVisible(index, visible)

	def getTabByUid(self, uid: str) -> QWidget | None:
		return self._uidToWidget.get(uid)

	def setCurrentTabByUid(self, uid: str):
		widget = self._uidToWidget.get(uid)
		if widget:
			self.setCurrentWidget(widget)

class MainWindow(QMainWindow):
	def __init__(self, parent: QWidget | None = None) -> None:
		super(MainWindow, self).__init__(parent)

		app = QApplication.instance()
		self.dialogsManager = app.GetDialogsManager()
		self.pluginManager: PluginManager = app.GetPluginManager()
		self.settingsManager: SettingsManager = app.GetSettingsManager()
		self.qavmSettings: QAVMGlobalSettings = self.settingsManager.GetQAVMSettings()
		
		# self.softwareSettings: SoftwareBaseSettings = self.settingsManager.GetSoftwareSettings()

		# self.softwareSettings.tilesUpdateRequired.connect(self.UpdateTilesWidget)
		# self.softwareSettings.tablesUpdateRequired.connect(self.UpdateTableWidget)
		
		# softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()

		workspace: QAVMWorkspace = app.GetWorkspace()
		swHandlers, _ = workspace.GetInvolvedSoftwareHandlers()
		swTitle: str = ', '.join([f'{sw.GetName()}' for sw in swHandlers])[:50]

		self.setWindowTitle(f'QAVM {GetQAVMVersionVariant()} - [{swTitle}]')
		self.resize(1420, 840)
		self.setMinimumSize(350, 250)

		self.pluginMenuItems: list[QMenu | QAction] = list()  # for some reason QMenu and QAction need to live in the MainWindow, otherwise Qt gets rid of them

		self._setupActions()
		self._setupMenuBar()
		self._setupStatusBar()

		self._setupCentralWidget()

	def _setupActions(self):
		self.actionPrefs = QAction(QIcon(":preferences.svg"), "&Preferences", self)
		self.actionPrefs.setShortcut("Ctrl+E")
		self.actionPrefs.triggered.connect(self._showPreferences)

		self.actionExit = QAction("&Exit", self, shortcut=QKeySequence.StandardKey.Quit)
		self.actionExit.triggered.connect(self.close)

		# self.actionPluginSelection = QAction("Select software", self)
		# self.actionPluginSelection.setEnabled(len(self.pluginManager.GetSoftwareHandlers()) > 1)
		# self.actionPluginSelection.triggered.connect(self._switchToPluginSelection)

		# self.actionRescan = QAction("&Rescan", self)
		# self.actionRescan.setShortcut("Ctrl+F5")
		# self.actionRescan.triggered.connect(self._rescanSoftware)

		self.actionAbout = QAction("&About", self)
		self.actionAbout.triggered.connect(self._showAboutDialog)

	def _setupMenuBar(self):
		menuBar: QMenuBar = self.menuBar()
		menuBar.setNativeMenuBar(True)  # Use native menu bar on macOS
		
		fileMenu: QMenu = QMenu("&File", self)
		# fileMenu.addAction(self.actionRescan)
		# fileMenu.addSeparator()
		# fileMenu.addAction(self.actionPluginSelection)
		# fileMenu.addSeparator()
		fileMenu.addAction(self.actionExit)
		menuBar.addMenu(fileMenu)
		
		if PlatformMacOS():  # workaround for stupid macOS menu bar
			fileMenu.addAction(self.actionPrefs)
		else:
			editMenu: QMenu = QMenu("&Edit", self)
			editMenu.addAction(self.actionPrefs)
			menuBar.addMenu(editMenu)
		
		# switchMenu: QMenu = QMenu("&Switch Workspace", self)
		# switchMenu.addAction(QAction("osx sucks", self))
		# menuBar.addMenu(switchMenu)
		# def populate_switch_menu():
		# 	switchMenu.clear()
		# 	swHandlers: list[tuple[str, str, SoftwareHandler]] = self.pluginManager.GetSoftwareHandlers()  # [pluginID, softwareID, SoftwareHandler]
		# 	for pluginID, softwareID, softwareHandler in swHandlers:
		# 		plugin: QAVMPlugin = self.pluginManager.GetPlugin(pluginID)
		# 		swUID: str = f'{pluginID}#{softwareID}'
		# 		title: str = f'{softwareHandler.GetName()} [{plugin.GetName()} @ {plugin.GetVersionStr()}] ({swUID})'
		# 		action = QAction(title, self)
		# 		action.triggered.connect(partial(self._switchToPluginSelection, swUID))
		# 		switchMenu.addAction(action)
		# switchMenu.aboutToShow.connect(populate_switch_menu)  # TODO: does this need dynamic update?

		app = QApplication.instance()
		workspace: QAVMWorkspace = app.GetWorkspace()

		for swHandler, menuItemsUIDs in workspace.GetMenuItems().items():
			for menuItemUID in menuItemsUIDs:
				if menuItem := swHandler.GetMenuItem(menuItemUID):
					if menu := menuItem.GetMenu(self):
						if isinstance(menu, QMenu):
							menuBar.addMenu(menu)
							self.pluginMenuItems.append(menu)  # for some reason QMenu and QAction need to live in the MainWindow, otherwise Qt gets rid of them
						elif isinstance(menu, QAction):
							menuBar.addAction(menu)
							self.pluginMenuItems.append(menu)  # for some reason QMenu and QAction need to live in the MainWindow, otherwise Qt gets rid of them
						else:
							logger.warning(f"Menu item {menu} is not a valid QMenu or QAction. Skipping.")

		helpMenu: QMenu = QMenu("&Help", self)
		helpMenu.addAction(self.actionAbout)
		menuBar.addMenu(helpMenu)

		# ##################################################################
		# ########################## Right Corner ##########################
		# ##################################################################
		# if not PlatformMacOS():  # macOS isn't capable of complex things
		# 	rightCornerMenu = QMenuBar(menuBar)
		# 	for pluginID, softwareID, softwareHandler in self.pluginManager.GetSoftwareHandlers():
		# 		swUID: str = f'{pluginID}#{softwareID}'
		# 		title: str = softwareHandler.GetName()
		# 		action = QAction(title, self, triggered=partial(self._switchToPluginSelection, swUID))
		# 		rightCornerMenu.addAction(action)
		# 	menuBar.setCornerWidget(rightCornerMenu)
	
	def _setupStatusBar(self):
		self.statusBar = QStatusBar()
		self.setStatusBar(self.statusBar)

	# TODO: this shouldn't be in constructor!
	def _setupCentralWidget(self):
		self.tabsWidget: MyTabWidget = MyTabWidget(self)
		
		app = QApplication.instance()
		workspace: QAVMWorkspace = app.GetWorkspace()

		for swHandler, tilesViewsUIDs in workspace.GetTilesViews().items():
			for viewUID in tilesViewsUIDs:
				self._createTilesView(swHandler, viewUID)

		for swHandler, tilesViewsUIDs in workspace.GetTableViews().items():
			for viewUID in tilesViewsUIDs:
				self._createTableView(swHandler, viewUID)

		for swHandler, customViews in workspace.GetCustomViews().items():
			for viewUID in customViews:
				self._createCustomView(swHandler, viewUID)

		# self.UpdateTilesWidget()
		# self.UpdateTableWidget()

		# TODO: FreeMove view is currently not implemented

		self.setCentralWidget(self.tabsWidget)

		self.tabsWidget.currentChanged.connect(self._onTabChanged)
		lastOpenedTab: int = self.qavmSettings.GetSetting('last_opened_tab')
		if lastOpenedTab >= 0 and lastOpenedTab < self.tabsWidget.count():
			self.tabsWidget.setCurrentIndex(lastOpenedTab)


	def _prepareDescriptors(self, swHandler: SoftwareHandler, viewUID: str, builder: BaseBuilder):
		# TODO: consider having some more understandable scheme for fetching descriptor types from dataPaths
		descTypes: list[str] = [t for t in map(UID.DataPathGetLastPart, swHandler.GetDescriptorClasses().keys()) if t]
		descTypes = builder.GetSupportedDescriptorTypes(descTypes)
		if not descTypes:
			return []

		app = QApplication.instance()
		descsMap: dict[str, list[BaseDescriptor]] = app.GetSoftwareDescriptors(swHandler)  # TODO: check to not iterate unnecessarily over unsupported descriptors
		
		descs: list[BaseDescriptor] = []
		for descUID, descsCur in descsMap.items():
			descType: Optional[str] = UID.DataPathGetLastPart(descUID)
			if descType in descTypes:
				descs.extend(builder.ProcessDescriptors(descType, descsCur))

		return descs
		
	def _createTilesView(self, swHandler: SoftwareHandler, viewUID: str):
		tileBuilderClass: Type[BaseTileBuilder] | None = swHandler.GetTileBuilderClass(viewUID)
		if tileBuilderClass is None or not issubclass(tileBuilderClass, BaseTileBuilder):
			return
		tileBuilder: BaseTileBuilder = tileBuilderClass(swHandler.GetSettings())
		
		descs: list[BaseDescriptor] = self._prepareDescriptors(swHandler, viewUID, tileBuilder)

		if tilesWidget := self._createTilesWidget(descs, tileBuilder, parent=self):
			self.tabsWidget.insertTab(0, tilesWidget, tileBuilder.GetName())
			# self.tabsWidget.addTabWithUid(tilesWidget, tileBuilder.GetName(), viewUID+descUID)
			
	def _createTableView(self, swHandler: SoftwareHandler, viewUID: str):
		tableBuilderClass: Type[BaseTableBuilder] | None = swHandler.GetTableBuilderClass(viewUID)
		if tableBuilderClass is None or not issubclass(tableBuilderClass, BaseTableBuilder):
			return
		tableBuilder: BaseTableBuilder = tableBuilderClass(swHandler.GetSettings())
		
		descs: list[BaseDescriptor] = self._prepareDescriptors(swHandler, viewUID, tableBuilder)

		if tilesWidget := self._createTableWidget(descs, tableBuilder, parent=self):
			self.tabsWidget.insertTab(0, tilesWidget, tableBuilder.GetName())
			# self.tabsWidget.addTabWithUid(tilesWidget, tableBuilder.GetName(), viewUID+descUID)

	def _createCustomView(self, swHandler: SoftwareHandler, viewUID: str):
		customViewClass: Type[BaseCustomView] | None = swHandler.GetCustomViewClass(viewUID)
		if customViewClass is None or not issubclass(customViewClass, BaseCustomView):
			return
		
		softwareSettings: SoftwareBaseSettings = swHandler.GetSettings()
		if customViewWidget := customViewClass(softwareSettings, self):
			self.tabsWidget.insertTab(0, customViewWidget, customViewWidget.GetName())

	def _onTabChanged(self, index: int):
		self.qavmSettings.SetSetting('last_opened_tab', index)
		self.qavmSettings.Save()  # TODO: should save now or later once per all changes?
	
	# def UpdateTableWidget(self):
	# 	softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()  # TODO: handle case when softwareHandler is None
	# 	contextMenu: BaseContextMenu = softwareHandler.GetTableBuilderContextMenuClass()(softwareHandler.GetSettings())
	# 	tableBuilder = softwareHandler.GetTableBuilderClass()(softwareHandler.GetSettings(), contextMenu)
	# 	if type(tableBuilder) is BaseTableBuilder:
	# 		return
		
	# 	currentTabIndex: int = self.tabsWidget.currentIndex()

	# 	if hasattr(self, 'tableWidget') and self.tableWidget:
	# 		self.tableWidget.deleteLater()
		
	# 	app = QApplication.instance()
	# 	self.tableWidget = self._createTableWidget(app.GetSoftwareDescriptions(), tableBuilder, contextMenu, self)
	# 	self.tabsWidget.insertTab(1, self.tableWidget, "Details")
	# 	self.tabsWidget.currentChanged.connect(partial(self._tableItemFocusBuggedWorkaround, self.tableWidget))
		
	# 	self.tabsWidget.setCurrentIndex(currentTabIndex)

	def _createTableWidget(self, descs: list[BaseDescriptor], tableBuilder: BaseTableBuilder, parent: QWidget):
		tableWidget = MyTableWidget(parent)

		headers: list[str] = tableBuilder.GetTableCaptions()

		tableWidget.setRowCount(len(descs))
		# tableWidget.verticalHeader().setVisible(False)  # TODO: make this preferences option

		myHeader = MyTableViewHeader(Qt.Orientation.Horizontal, tableWidget)
		tableWidget.setHorizontalHeader(myHeader)
		tableWidget.setColumnCount(len(headers) + 1)
		tableWidget.setHorizontalHeaderLabels(headers + ['descIdx'])
		tableWidget.hideColumn(len(headers))  # hide descIdx column, this is kinda dirty, but gives more flexibility comparing to qabstracttablemodel and qproxymodel
		tableWidget.setItemDelegate(tableBuilder.GetItemDelegateClass()(tableWidget))
		
		tableWidget.setSortingEnabled(True)
		tableWidget.horizontalHeader().setStretchLastSection(True)
		tableWidget.horizontalHeader().setMinimumSectionSize(150)
		tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
		tableWidget.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
		tableWidget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
		
		tableWidget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
		tableWidget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

		tableWidget.doubleClickedLeft.connect(partial(self._onTableItemDoubleClickedLeft, tableWidget, tableBuilder))
		tableWidget.clickedMiddle.connect(partial(self._onTableItemClickedMiddle, tableWidget, tableBuilder))
		tableWidget.itemSelectionChanged.connect(partial(self._tableItemFocusBuggedWorkaround, tableWidget))

		# TODO: this sounds like a temp solution
		# self.tableContextMenus: list[QMenu] = list()
		def showContextMenu(pos):
			selectedRowsUnique: set = {idx.row() for idx in tableWidget.selectedIndexes()}
			currentRow = selectedRowsUnique.pop()
			descIdx: int = int(tableWidget.item(currentRow, len(headers)).text())
			# self.tableContextMenus[descIdx].exec(QCursor.pos())
			if menu := tableBuilder.GetContextMenu(descs[descIdx]):
				menu.exec(QCursor.pos())

		for r, desc in enumerate(descs):
			# rowColor = QBrush(colors[r % 3])
			for c, header in enumerate(headers):
				tableWidgetItem = tableBuilder.GetTableCellValue(desc, c)
				if not isinstance(tableWidgetItem, QTableWidgetItem):
					tableWidgetItem = QTableWidgetItem(tableWidgetItem)
				tableWidget.setItem(r, c, tableWidgetItem)
			tableWidget.setItem(r, len(headers), QTableWidgetItem(str(r)))
		
		tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		tableWidget.customContextMenuRequested.connect(showContextMenu)
		
		return tableWidget
	
	def _tableItemFocusBuggedWorkaround(self, tableWidget: QTableWidget):
		"""
		For some reason, after switching to the TilesWidget + RMB click there and switching back to the TableWidget,
		the TableWidget starts highlighting the currently selected item regardless of the Qt.FocusPolicy.NoFocus
		"""
		if self.tabsWidget.currentIndex() == 1:  # TODO: dynamically get table tab index, don't hardcode!
			tableWidget.clearFocus()
	
	def _onTableItemDoubleClickedLeft(self, tableWidget: QTableWidget, tableBuilder: BaseTableBuilder, row: int, col: int, modifiers: Qt.KeyboardModifier):
		if row < 0 or col < 0:
			return
		app = QApplication.instance()
		descIdx: int = int(tableWidget.item(row, len(tableBuilder.GetTableCaptions())).text())
		tableBuilder.HandleClick(app.GetSoftwareDescriptions()[descIdx], row, col, True, 0, QApplication.keyboardModifiers())

	def _onTableItemClickedMiddle(self, tableWidget: QTableWidget, tableBuilder: BaseTableBuilder, row: int, col: int, modifiers: Qt.KeyboardModifier):
		if row < 0 or col < 0:
			return
		app = QApplication.instance()
		descIdx: int = int(tableWidget.item(row, len(tableBuilder.GetTableCaptions())).text())
		tableBuilder.HandleClick(app.GetSoftwareDescriptions()[descIdx], row, col, False, 2, QApplication.keyboardModifiers())
	
	# def UpdateTilesWidget(self):
	# 	softwareHandler: SoftwareHandler = self.pluginManager.GetCurrentSoftwareHandler()  # TODO: handle case when softwareHandler is None
	# 	contextMenu: BaseContextMenu = softwareHandler.GetTileBuilderContextMenuClass()(softwareHandler.GetSettings())
	# 	tileBuilder: BaseTileBuilder = softwareHandler.GetTileBuilderClass()(softwareHandler.GetSettings(), contextMenu)
	# 	if type(tileBuilder) is BaseTileBuilder:
	# 		return

	# 	currentTabIndex: int = self.tabsWidget.currentIndex()

	# 	if hasattr(self, 'tilesWidget') and self.tilesWidget:
	# 		self.tilesWidget.deleteLater()

	# 	app = QApplication.instance()
	# 	self.tilesWidget = self._createTilesWidget(app.GetSoftwareDescriptions(), tileBuilder, contextMenu, self)
	# 	self.tabsWidget.insertTab(0, self.tilesWidget, "Tiles")
		
	# 	self.tabsWidget.setCurrentIndex(currentTabIndex)

	def _createTilesWidget(self, descs: list[BaseDescriptor], tileBuilder: BaseTileBuilder, parent: QWidget) -> QWidget:
		tiles: list[QWidget] = list()

		def showContextMenu(desc):
			if menu := tileBuilder.GetContextMenu(desc):
				menu.exec(QCursor.pos())

		for desc in descs:
			desc.updated.connect(partial(self._onDescriptorUpdated, desc))
			tileWidget = tileBuilder.CreateTileWidget(desc, parent)
			
			tileWidget.descriptor = desc  # TODO: what-a-heck? make a setter for that
			tileWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
			tileWidget.customContextMenuRequested.connect(partial(lambda d, p: showContextMenu(d), desc))

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
	
	# def _switchToPluginSelection(self, swUID: str = ''):
	# 	app = QApplication.instance()
	# 	# TODO: this should probably has clearer handling
	# 	self.qavmSettings.SetSelectedSoftwareUID(swUID)
	# 	app.selectedSoftwareUID = swUID
	# 	# TODO: storing the setting without being sure that the plugin runs leads to a deadlock (start and crash)
	# 	self.qavmSettings.Save()
	# 	self.dialogsManager.ResetPreferencesWindow()
	# 	self.dialogsManager.GetPluginSelectionWindow().show()
	# 	self.close()
	
	# def _rescanSoftware(self):
	# 	app = QApplication.instance()
	# 	app.ResetSoftwareDescriptions()
	# 	self.UpdateTilesWidget()


	def _showPreferences(self):
		app = QApplication.instance()
		prefsWindow: QMainWindow = app.GetDialogsManager().GetPreferencesWindow()
		prefsWindow.show()
		prefsWindow.activateWindow()

	def _showAboutDialog(self):
		aboutDialog = QDialog(self)
		aboutDialog.setWindowTitle("About QAVM")
		aboutDialog.setMinimumSize(600, 400)
		aboutDialog.setModal(True)

		mainLayout = QVBoxLayout(aboutDialog)

		# === Top section: Icon + version info ===
		topLayout = QHBoxLayout()

		# App icon
		icon = QIcon("res/qavm_icon.png")  # Replace with your icon path or Qt resource
		pixmap = icon.pixmap(64, 64)
		iconLabel = QLabel()
		iconLabel.setPixmap(pixmap)
		iconLabel.setAlignment(Qt.AlignmentFlag.AlignTop)
		topLayout.addWidget(iconLabel)

		# Version info
		versionInfo = (
			f"<b>QAVM {GetQAVMVersionVariant()}</b><br>"
			f"Package: {GetPackageVersion()}<br>"
			f"Build: {GetBuildVersion()}<br><br>"
		)
		versionLabel = QLabel(versionInfo)
		versionLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
		versionLabel.setTextFormat(Qt.TextFormat.RichText)
		versionLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
		topLayout.addWidget(versionLabel)

		topLayout.addStretch()
		mainLayout.addLayout(topLayout)

		# === Scrollable plugin section ===
		scrollArea = QScrollArea()
		scrollArea.setWidgetResizable(True)
		pluginContainer = QWidget()
		pluginLayout = QVBoxLayout(pluginContainer)

		for plugin in self.pluginManager.GetPlugins():
			pluginVersion: str = plugin.GetVersionStr()
			pluginVariant: str = plugin.GetPluginVariant()
			if pluginVariant:
				pluginVersion += f" ({pluginVariant})"
			pluginText = (
				f"<b>Plugin:</b> {plugin.GetName()}"
				f"<br><b>Version:</b> {pluginVersion}"
				f"<br><b>UID:</b> {plugin.GetUID()}"
				f"<br><b>Executable:</b> <code>{plugin.GetExecutablePath()}</code>"
				f"<br><b>Developer:</b> {plugin.GetPluginDeveloper()}"
				f"<br><b>Website:</b> <a href='{plugin.GetPluginWebsite()}'>{plugin.GetPluginWebsite()}</a>"
			)
			pluginLabel = QLabel()
			pluginLabel.setTextFormat(Qt.TextFormat.RichText)
			pluginLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
			pluginLabel.setOpenExternalLinks(True)
			pluginLabel.setWordWrap(True)
			pluginLabel.setText(pluginText)
			pluginLayout.addWidget(pluginLabel)

		scrollArea.setWidget(pluginContainer)
		mainLayout.addWidget(scrollArea)

		# === OK Button ===
		buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
		buttonBox.accepted.connect(aboutDialog.accept)
		mainLayout.addWidget(buttonBox)

		aboutDialog.exec()