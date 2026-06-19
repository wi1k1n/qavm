import os  # TODO: Get rid of os.path in favor of pathlib
from pathlib import Path
from functools import partial
from typing import Type, Optional

from PyQt6.QtCore import Qt, QMargins, QPoint, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QCursor, QColor, QBrush, QPainter, QPen, QPolygon, QMouseEvent, QPaintEvent
from PyQt6.QtWidgets import (
	QMainWindow, QWidget, QLabel, QTabWidget, QScrollArea, QStatusBar, QTableWidgetItem, QTableWidget,
	QHeaderView, QMenu, QMenuBar, QStyledItemDelegate, QApplication, QAbstractItemView, QMessageBox,
	QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QLineEdit, QHBoxLayout,
	QSizePolicy, QTableView, QTableWidgetSelectionRange, QStyle, QStyleOptionViewItem,
)

from qavm.manager_plugin import PluginManager, SoftwareHandler, UID, QAVMWorkspace
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings
from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorDataImpl
from qavm.manager_tags import TagsManager, BaseTagImpl

from qavm.window_note_editor import NoteEditorDialog
from qavm.window_about import AboutDialog

from qavm.qavmapi import (
	BaseDescriptor, BaseSettings, BaseTileBuilder, BaseTableBuilder,
	BaseCustomView, SoftwareBaseSettings, BaseMenuItem, BaseBuilder, TableColumnInfo
)
from qavm.qavmapi.utils import PlatformMacOS, PlatformWindows, PlatformLinux
from qavm.qavmapi.gui import TagBubblesFlowWidget, GetThemeData, IsThemeDark
from qavm.utils_gui import FlowLayout
from qavm.utils_widgets import PopulateContextMenuTagsAndNotes, AssignTagUIDToDescriptor, TAG_MIME_TYPE
from qavm.qavm_version import GetBuildVersion, GetPackageVersion, GetQAVMVersion, GetQAVMVersionVariant

import qavm.logs as logs
logger = logs.logger

# TODO: wtf, rename it please!
class MyTableViewHeader(QHeaderView):
	def __init__(self, orientation, parent=None):
		super().__init__(orientation, parent)
		self.setSortIndicatorShown(False)  # We paint the indicator manually
		self.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(self._showContextMenu)
		self.setSectionsMovable(True)

		self._mousePressedPos = None
		self._mousePressedSection = -1
		self._sectionMinimumWidths: list[int] = []

		self.sectionResized.connect(self._enforceMinWidth)

	def SetSectionMinimumWidths(self, minWidths: list[int]):
		self._sectionMinimumWidths = minWidths
		
	def _enforceMinWidth(self, logicalIndex, oldSize, newSize):
		min_width = self._sectionMinimumWidths[logicalIndex] if logicalIndex < len(self._sectionMinimumWidths) else None
		if min_width is not None and newSize < min_width:
			self.resizeSection(logicalIndex, min_width)

	def paintSection(self, painter: QPainter, rect: QRect, logicalIndex: int):
		super().paintSection(painter, rect, logicalIndex)

	def paintEvent(self, event: QPaintEvent):
		super().paintEvent(event)

		section = self.sortIndicatorSection()
		if section < 0 or self.isSectionHidden(section):
			return

		# Draw sort arrow overlay using the theme's primary color
		from qavm.qavmapi.gui import GetThemeData
		themeData = GetThemeData()
		color = QColor(themeData.get('primaryColor', '#ffffff')) if themeData else QColor('#ffffff')

		sectionPos = self.sectionViewportPosition(section)
		sectionSize = self.sectionSize(section)
		headerHeight = self.height()

		arrowSize = 8
		margin = 6
		centerY = headerHeight // 2
		xPos = sectionPos + sectionSize - arrowSize - margin

		painter = QPainter(self.viewport())
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		painter.setPen(Qt.PenStyle.NoPen)
		painter.setBrush(QBrush(color))

		if self.sortIndicatorOrder() == Qt.SortOrder.AscendingOrder:
			points = [
				QPoint(xPos + arrowSize // 2, centerY - arrowSize // 2),
				QPoint(xPos, centerY + arrowSize // 2),
				QPoint(xPos + arrowSize, centerY + arrowSize // 2),
			]
		else:
			points = [
				QPoint(xPos, centerY - arrowSize // 2),
				QPoint(xPos + arrowSize, centerY - arrowSize // 2),
				QPoint(xPos + arrowSize // 2, centerY + arrowSize // 2),
			]

		painter.drawPolygon(QPolygon(points))
		painter.end()

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
			
class _CellWidgetSortItem(QTableWidgetItem):
	""" Invisible placeholder item placed under a cell widget. Provides a stable sort key for the
	column while displaying no text, so nothing renders behind a transparent cell widget. """
	def __init__(self, sortKey: str):
		super().__init__('')
		self._sortKey: str = sortKey

	def __lt__(self, other):
		if isinstance(other, _CellWidgetSortItem):
			return self._sortKey < other._sortKey
		return super().__lt__(other)

# TODO: wtf, rename it please!
class MyTableWidget(QTableWidget):
	clickedLeft = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	clickedRight = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	clickedMiddle = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	doubleClickedLeft = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	doubleClickedRight = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers
	doubleClickedMiddle = pyqtSignal(int, int, Qt.KeyboardModifier)  # row, col, modifiers

	def __init__(self, descs: list[BaseDescriptor], tableBuilder: BaseTableBuilder, swHandler: SoftwareHandler, viewUID: str, parent: QMainWindow):
		super().__init__(parent)
		
		self.mainWindow: QMainWindow = parent
		self.swHandler: SoftwareHandler = swHandler
		self.viewUID: str = viewUID

		self.setAcceptDrops(True)  # accept tag bubbles dragged from the Tags palette

		self._setupTable(descs, tableBuilder, parent)

	def dragEnterEvent(self, event):
		if event.mimeData().hasFormat(TAG_MIME_TYPE):
			event.acceptProposedAction()
		else:
			event.ignore()

	def dragMoveEvent(self, event):
		if event.mimeData().hasFormat(TAG_MIME_TYPE):
			event.acceptProposedAction()
		else:
			event.ignore()

	def dropEvent(self, event):
		if not event.mimeData().hasFormat(TAG_MIME_TYPE):
			event.ignore()
			return
		tagUID: str = bytes(event.mimeData().data(TAG_MIME_TYPE).data()).decode('utf-8')
		row: int = self.indexAt(event.position().toPoint()).row()
		if row < 0:
			event.ignore()
			return
		descIdxItem = self.item(row, len(self._tableInfos))
		if descIdxItem is None:
			event.ignore()
			return
		descIdx: int = int(descIdxItem.text())
		if descIdx < 0 or descIdx >= len(self._descs):
			event.ignore()
			return
		desc: BaseDescriptor = self._descs[descIdx]
		AssignTagUIDToDescriptor(desc, tagUID)
		event.acceptProposedAction()

	def _tagUnderCursor(self, viewportPos: QPoint) -> BaseTagImpl | None:
		""" Returns the tag whose bubble is under `viewportPos` (the context-menu position), or None. """
		index = self.indexAt(viewportPos)
		if not index.isValid():
			return None
		cellWidget = self.cellWidget(index.row(), index.column())
		if isinstance(cellWidget, TagBubblesFlowWidget):
			return cellWidget.GetTagAt(cellWidget.mapFromGlobal(QCursor.pos()))
		return None

	def mousePressEvent(self, event: QMouseEvent):
		if event.button() == Qt.MouseButton.LeftButton:
			# print("Left button clicked")
			self.clickedLeft.emit(self.currentRow(), self.currentColumn(), QApplication.keyboardModifiers())
		elif event.button() == Qt.MouseButton.RightButton:
			# print("Right button clicked")
			self.clickedRight.emit(self.currentRow(), self.currentColumn(), QApplication.keyboardModifiers())
		elif event.button() == Qt.MouseButton.MiddleButton:
			# print("Middle button clicked")
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

	def keyPressEvent(self, event):
		if event.key() == Qt.Key.Key_N and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
			desc: BaseDescriptor | None = self._selectedRowDescriptor()
			if desc is not None:
				self.mainWindow._showNoteEditorDialog(desc)
				event.accept()
				return
		super().keyPressEvent(event)

	def _selectedRowDescriptor(self) -> BaseDescriptor | None:
		""" Returns the descriptor for the currently selected row, or None if there is no valid selection. """
		selectedRows: set = {idx.row() for idx in self.selectedIndexes()}
		if not selectedRows:
			return None
		row: int = selectedRows.pop()
		descIdxItem = self.item(row, len(self._tableInfos))
		if descIdxItem is None:
			return None
		descIdx: int = int(descIdxItem.text())
		if descIdx < 0 or descIdx >= len(self._descs):
			return None
		return self._descs[descIdx]

	def _setupTable(self, descs: list[BaseDescriptor], tableBuilder: BaseTableBuilder, parent: QMainWindow):
		self._descs = descs
		self._tableBuilder = tableBuilder
		self._tableInfos: list[TableColumnInfo] = tableBuilder.GetTableColumnInfo()

		headers: list[str] = list(map(lambda info: info.title, self._tableInfos))

		header = MyTableViewHeader(Qt.Orientation.Horizontal, self)
		# TODO: move this to MyTableViewHeader
		header.setStretchLastSection(True)
		header.setMinimumSectionSize(0)
		header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

		self.setHorizontalHeader(header)
		self.setRowCount(len(descs))
		self.setColumnCount(len(headers) + 1)
		self.setHorizontalHeaderLabels(headers + ['descIdx'])
		self.hideColumn(len(headers))  # hide descIdx column
		self.setItemDelegate(tableBuilder.GetItemDelegateClass()(self))

		self.setSortingEnabled(True)
		self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
		self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

		self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
		self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

		self._applyRowSelectionStyle()

		self.doubleClickedLeft.connect(partial(self._onTableItemDoubleClickedLeft, self, tableBuilder))
		self.clickedMiddle.connect(partial(self._onTableItemClickedMiddle, self, tableBuilder))

		def showContextMenu(pos):
			selectedRowsUnique: set = {idx.row() for idx in self.selectedIndexes()}
			if not selectedRowsUnique:
				return
			currentRow = selectedRowsUnique.pop()
			item = self.item(currentRow, len(headers))
			if item:
				descIdx: int = int(item.text())
				desc: BaseDescriptor = descs[descIdx]
				if menu := tableBuilder.GetContextMenu(desc):
					tagUnderCursor: BaseTagImpl | None = self._tagUnderCursor(pos)
					PopulateContextMenuTagsAndNotes(menu, desc, self.mainWindow, self, self.swHandler.pluginID, self.swHandler.GetID(), self.viewUID, tagUnderCursor)
					menu.exec(QCursor.pos())

		for r, desc in enumerate(descs):
			self._populateRow(r, desc, r)
			desc.descDataUpdated.connect(partial(self._onUpdateTableRowRequired, desc))

		# Apply per-column widths info after items are populated
		header.SetSectionMinimumWidths(list(map(lambda info: info.minWidth, self._tableInfos)))
		colDefaultWidths: list[int] = list(map(lambda info: info.defaultWidth, self._tableInfos))
		if len(colDefaultWidths) == len(headers):
			for col, defW in enumerate(colDefaultWidths):
				if defW > 0:
					header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
					header.resizeSection(col, defW)
					
		header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

		# Cell widgets (e.g. tag bubbles) wrap based on column width and need realignment on sort.
		header.sectionResized.connect(self._onSectionResized)
		header.sortIndicatorChanged.connect(self._onSortIndicatorChanged)
		self._recomputeAllRowHeights()

		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(showContextMenu)

	def _applyRowSelectionStyle(self):
		""" Forces a single, uniform selection color for the whole row.

		qt_material styles `QTableView::item:selected:focus` (the current cell) brighter than the rest of
		the `:selected` row, so with ClickFocus the clicked cell stands out. Overriding both states with the
		same color makes selection appear per-row instead of per-cell. """
		themeData = GetThemeData() or {}
		primaryLightColor: QColor = QColor(themeData.get('primaryLightColor') or "#677bec")
		S_MLT = 0.8
		L_MLT = 0.5 if IsThemeDark() else 1.0
		primaryLightColor.setHsl(primaryLightColor.hue(), int(primaryLightColor.saturation() * S_MLT), int(primaryLightColor.lightness() * L_MLT))

		primaryTextColor: str = themeData.get('primaryTextColor') or '#ffffff'

		# qt_material's `QHeaderView::section` uses a large `padding: 0 24px`, which clips the (centered)
		# header title on both sides even when the column is wide enough. Reduce the horizontal padding
		# while re-specifying the section's background/borders so qt_material's styling isn't dropped.
		secondaryColor: str = themeData.get('secondaryColor') or '#31363b'
		secondaryDarkColor: str = themeData.get('secondaryDarkColor') or '#232629'
		secondaryTextColor: str = themeData.get('secondaryTextColor') or '#e0e0e0'

		self.setStyleSheet(
			f'QTableView::item:selected, QTableView::item:selected:focus {{'
			f' background-color: {primaryLightColor.name()};'
			f' selection-background-color: {primaryLightColor.name()};'
			f' color: {primaryTextColor};'
			f' selection-color: {primaryTextColor};'
			f' }}'
			f'QHeaderView::section {{'
			f' padding: 0 4px;'
			f' background-color: {secondaryColor};'
			f' color: {secondaryTextColor};'
			f' text-transform: uppercase;'
			f' border-right: 1px solid {secondaryDarkColor};'
			f' border-bottom: 1px solid {secondaryDarkColor};'
			f' }}'
		)

	def _populateRow(self, row: int, desc: BaseDescriptor, descIdx: int):
		for c, tableInfo in enumerate(self._tableInfos):
			cellValue = tableInfo.cellDataGetter(desc) if callable(tableInfo.cellDataGetter) else ''
			if isinstance(cellValue, QWidget):
				getSortKey = getattr(cellValue, 'GetSortKey', None)
				sortKey: str = str(getSortKey()) if callable(getSortKey) else ''
				self.setItem(row, c, _CellWidgetSortItem(sortKey))
				self.setCellWidget(row, c, cellValue)
			else:
				if self.cellWidget(row, c) is not None:
					self.removeCellWidget(row, c)
				if not isinstance(cellValue, QTableWidgetItem):
					cellValue = QTableWidgetItem(cellValue)
				self.setItem(row, c, cellValue)
		self.setItem(row, len(self._tableInfos), QTableWidgetItem(str(descIdx)))
		self._adjustRowHeight(row)

	def _adjustRowHeight(self, row: int):
		""" Sizes the row to fit any variable-height cell widgets, capped by the builder's max row height. """
		maxHeight: int = self._tableBuilder.GetRowMaximumHeight()
		desiredHeight: int = 0
		hasWidget: bool = False
		for c in range(len(self._tableInfos)):
			widget: QWidget | None = self.cellWidget(row, c)
			if widget is not None and widget.hasHeightForWidth():
				hasWidget = True
				desiredHeight = max(desiredHeight, widget.heightForWidth(self.columnWidth(c)))
		if hasWidget:
			self.setRowHeight(row, max(min(desiredHeight, maxHeight), 1))
		else:
			self.resizeRowToContents(row)

	def _recomputeAllRowHeights(self):
		for row in range(self.rowCount()):
			self._adjustRowHeight(row)

	def _onSectionResized(self, logicalIndex: int, oldSize: int, newSize: int):
		# Column width affects how the flow-laid-out cell widgets wrap, so row heights must be recomputed.
		self._recomputeAllRowHeights()

	def _rebuildCellWidgets(self):
		""" Re-creates cell widgets for every row from the (possibly reordered) hidden descIdx column.

		QTableWidget does not move cell widgets when sorting, so after a sort the widgets must be rebuilt
		to stay aligned with their rows. """
		descIdxColumn: int = len(self._tableInfos)
		for row in range(self.rowCount()):
			item = self.item(row, descIdxColumn)
			if item is None:
				continue
			try:
				descIdx: int = int(item.text())
			except ValueError:
				continue
			desc: BaseDescriptor = self._descs[descIdx]
			for c, tableInfo in enumerate(self._tableInfos):
				cellValue = tableInfo.cellDataGetter(desc) if callable(tableInfo.cellDataGetter) else ''
				if isinstance(cellValue, QWidget):
					self.setCellWidget(row, c, cellValue)
				elif self.cellWidget(row, c) is not None:
					self.removeCellWidget(row, c)
			self._adjustRowHeight(row)

	def _onSortIndicatorChanged(self, logicalIndex: int, order: Qt.SortOrder):
		# Defer until after QTableWidget finishes reordering items, then realign cell widgets.
		QTimer.singleShot(0, self._rebuildCellWidgets)

	def GetViewState(self) -> dict:
		""" Returns the persistable UI state of the table (sorting, column order/visibility/widths). """
		header = self.horizontalHeader()
		dataColumnCount: int = len(self._tableInfos)  # exclude the hidden descIdx column
		columnWidths: dict[str, int] = {}
		columnHidden: dict[str, bool] = {}
		for col in range(dataColumnCount):
			columnWidths[str(col)] = self.columnWidth(col)
			columnHidden[str(col)] = self.isColumnHidden(col)
		# Logical indices ordered by their current visual position (data columns only).
		columnOrder: list[int] = sorted(range(dataColumnCount), key=lambda c: header.visualIndex(c))
		return {
			'sort_column': header.sortIndicatorSection(),
			'sort_order': header.sortIndicatorOrder().value,
			'column_widths': columnWidths,
			'column_hidden': columnHidden,
			'column_order': columnOrder,
		}

	def ApplyViewState(self, state: dict):
		""" Restores a previously persisted UI state (sorting, column order/visibility/widths). """
		if not isinstance(state, dict):
			return
		header = self.horizontalHeader()
		dataColumnCount: int = len(self._tableInfos)

		# Column order (data columns only): place each logical index at its saved visual position.
		columnOrder = state.get('column_order', None)
		if isinstance(columnOrder, list):
			visualPos: int = 0
			for logicalIdx in columnOrder:
				if not isinstance(logicalIdx, int) or not (0 <= logicalIdx < dataColumnCount):
					continue
				currentVisual: int = header.visualIndex(logicalIdx)
				if currentVisual != -1 and currentVisual != visualPos:
					header.moveSection(currentVisual, visualPos)
				visualPos += 1

		columnWidths = state.get('column_widths', {})
		if isinstance(columnWidths, dict):
			for colStr, width in columnWidths.items():
				try:
					col = int(colStr)
				except (ValueError, TypeError):
					continue
				if 0 <= col < dataColumnCount and isinstance(width, int) and width > 0:
					header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
					self.setColumnWidth(col, width)

		columnHidden = state.get('column_hidden', {})
		if isinstance(columnHidden, dict):
			for colStr, hidden in columnHidden.items():
				try:
					col = int(colStr)
				except (ValueError, TypeError):
					continue
				if 0 <= col < dataColumnCount and isinstance(hidden, bool):
					self.setColumnHidden(col, hidden)

		sortColumn = state.get('sort_column', -1)
		sortOrder = state.get('sort_order', None)
		if isinstance(sortColumn, int) and 0 <= sortColumn < dataColumnCount and sortOrder is not None:
			order = Qt.SortOrder.AscendingOrder if sortOrder == Qt.SortOrder.AscendingOrder.value else Qt.SortOrder.DescendingOrder
			self.sortByColumn(sortColumn, order)


	def _onUpdateTableRowRequired(self, desc: BaseDescriptor):
		try:
			descIdx: int = self._descs.index(desc)
		except ValueError:
			return
		descIdxColumn: int = len(self._tableInfos)
		targetRow: int = -1
		for row in range(self.rowCount()):
			item = self.item(row, descIdxColumn)
			if item and item.text() == str(descIdx):
				targetRow = row
				break
		if targetRow < 0:
			return
		sortingEnabled: bool = self.isSortingEnabled()
		self.setSortingEnabled(False)
		self._populateRow(targetRow, desc, descIdx)
		self.setSortingEnabled(sortingEnabled)

	def _onTableItemDoubleClickedLeft(self, tableWidget: QTableWidget, tableBuilder: BaseTableBuilder, row: int, col: int, modifiers: Qt.KeyboardModifier):
		if row < 0 or col < 0:
			return
		# app = QApplication.instance()
		# descIdx: int = int(tableWidget.item(row, len(tableBuilder.GetTableCaptions())).text())
		# tableBuilder.HandleClick(app.GetSoftwareDescriptors()[descIdx], row, col, True, 0, QApplication.keyboardModifiers())

	def _onTableItemClickedMiddle(self, tableWidget: QTableWidget, tableBuilder: BaseTableBuilder, row: int, col: int, modifiers: Qt.KeyboardModifier):
		if row < 0 or col < 0:
			return
		# app = QApplication.instance()
		# descIdx: int = int(tableWidget.item(row, len(tableBuilder.GetTableCaptions())).text())
		# tableBuilder.HandleClick(app.GetSoftwareDescriptors()[descIdx], row, col, False, 2, QApplication.keyboardModifiers())

	def showEvent(self, event):
		# When the table becomes visible/activated (for example when switching tabs),
		# the layout may change — recompute row heights after the show event so
		# variable-height cell widgets wrap correctly.
		super().showEvent(event)
		QTimer.singleShot(0, self._recomputeAllRowHeights)

	def focusInEvent(self, event):
		# Also recompute when the widget receives focus, which can happen when
		# the user activates the table inside a container.
		super().focusInEvent(event)
		QTimer.singleShot(0, self._recomputeAllRowHeights)
	


