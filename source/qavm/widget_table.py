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
from qavm.manager_descriptor_data import DescriptorDataManager, DescriptorData
from qavm.manager_tags import TagsManager, Tag

from qavm.window_note_editor import NoteEditorDialog
from qavm.window_about import AboutDialog

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

	def __init__(self, descs: list[BaseDescriptor], tableBuilder: BaseTableBuilder, parent: QMainWindow):
		super().__init__(parent)

		self._setupTable(descs, tableBuilder, parent)

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

		header = MyTableViewHeader(Qt.Orientation.Horizontal, self)
		# TODO: move this to MyTableViewHeader
		header.setStretchLastSection(True)
		header.setMinimumSectionSize(150)
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
				if menu := tableBuilder.GetContextMenu(descs[descIdx]):
					menu.exec(QCursor.pos())

		for r, desc in enumerate(descs):
			for c, header in enumerate(headers):
				tableWidgetItem = tableBuilder.GetTableCellValue(desc, c)
				if not isinstance(tableWidgetItem, QTableWidgetItem):
					tableWidgetItem = QTableWidgetItem(tableWidgetItem)
				self.setItem(r, c, tableWidgetItem)
			self.setItem(r, len(headers), QTableWidgetItem(str(r)))

		self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.customContextMenuRequested.connect(showContextMenu)

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
	


