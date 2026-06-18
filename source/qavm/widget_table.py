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
	QSizePolicy, QTableView, QTableWidgetSelectionRange, 
)

from qavm.manager_plugin import PluginManager, SoftwareHandler, UID, QAVMWorkspace
from qavm.manager_settings import SettingsManager, QAVMGlobalSettings
from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorDataImpl
from qavm.manager_tags import TagsManager, BaseTagImpl

from qavm.window_note_editor import NoteEditorDialog
from qavm.window_about import AboutDialog

from qavm.qavmapi import (
	BaseDescriptor, BaseSettings, BaseTileBuilder, BaseTableBuilder,
	BaseCustomView, SoftwareBaseSettings, BaseMenuItem, BaseBuilder, 
)
from qavm.qavmapi.utils import PlatformMacOS, PlatformWindows, PlatformLinux
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
		descIdxItem = self.item(row, len(self._headers))
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

	def _setupTable(self, descs: list[BaseDescriptor], tableBuilder: BaseTableBuilder, parent: QMainWindow):
		headers: list[str] = tableBuilder.GetTableCaptions()

		self._descs = descs
		self._tableBuilder = tableBuilder
		self._headers = headers

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
		self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

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
					PopulateContextMenuTagsAndNotes(menu, desc, self.mainWindow, self, self.swHandler.pluginID, self.swHandler.GetID(), self.viewUID)
					menu.exec(QCursor.pos())

		for r, desc in enumerate(descs):
			self._populateRow(r, desc, r)
			desc.descDataUpdated.connect(partial(self._onUpdateTableRowRequired, desc))

		# Apply per-column minimum widths after items are populated
		colMinWidths: list[int] | None = tableBuilder.GetColumnMinimumWidths()
		if colMinWidths:
			hdr = self.horizontalHeader()
			for col in range(min(len(colMinWidths), len(headers))):
				minW = colMinWidths[col]
				if minW > 0:
					hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
					hdr.resizeSection(col, max(hdr.sectionSize(col), minW))

		# Cell widgets (e.g. tag bubbles) wrap based on column width and need realignment on sort.
		header.sectionResized.connect(self._onSectionResized)
		header.sortIndicatorChanged.connect(self._onSortIndicatorChanged)
		self._recomputeAllRowHeights()

		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(showContextMenu)

	def _populateRow(self, row: int, desc: BaseDescriptor, descIdx: int):
		headers: list[str] = self._headers
		tableBuilder: BaseTableBuilder = self._tableBuilder
		for c in range(len(headers)):
			cellValue = tableBuilder.GetTableCellValue(desc, c)
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
		self.setItem(row, len(headers), QTableWidgetItem(str(descIdx)))
		self._adjustRowHeight(row)

	def _adjustRowHeight(self, row: int):
		""" Sizes the row to fit any variable-height cell widgets, capped by the builder's max row height. """
		maxHeight: int = self._tableBuilder.GetRowMaximumHeight()
		desiredHeight: int = 0
		hasWidget: bool = False
		for c in range(len(self._headers)):
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
		descIdxColumn: int = len(self._headers)
		tableBuilder: BaseTableBuilder = self._tableBuilder
		for row in range(self.rowCount()):
			item = self.item(row, descIdxColumn)
			if item is None:
				continue
			try:
				descIdx: int = int(item.text())
			except ValueError:
				continue
			desc: BaseDescriptor = self._descs[descIdx]
			for c in range(len(self._headers)):
				cellValue = tableBuilder.GetTableCellValue(desc, c)
				if isinstance(cellValue, QWidget):
					self.setCellWidget(row, c, cellValue)
				elif self.cellWidget(row, c) is not None:
					self.removeCellWidget(row, c)
			self._adjustRowHeight(row)

	def _onSortIndicatorChanged(self, logicalIndex: int, order: Qt.SortOrder):
		# Defer until after QTableWidget finishes reordering items, then realign cell widgets.
		QTimer.singleShot(0, self._rebuildCellWidgets)


	def _onUpdateTableRowRequired(self, desc: BaseDescriptor):
		try:
			descIdx: int = self._descs.index(desc)
		except ValueError:
			return
		descIdxColumn: int = len(self._headers)
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
		app = QApplication.instance()
		descIdx: int = int(tableWidget.item(row, len(tableBuilder.GetTableCaptions())).text())
		# tableBuilder.HandleClick(app.GetSoftwareDescriptors()[descIdx], row, col, True, 0, QApplication.keyboardModifiers())

	def _onTableItemClickedMiddle(self, tableWidget: QTableWidget, tableBuilder: BaseTableBuilder, row: int, col: int, modifiers: Qt.KeyboardModifier):
		if row < 0 or col < 0:
			return
		app = QApplication.instance()
		descIdx: int = int(tableWidget.item(row, len(tableBuilder.GetTableCaptions())).text())
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
	


