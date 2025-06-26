import datetime as dt
from pathlib import Path

from PyQt6.QtCore import (
	Qt, pyqtSignal, QPropertyAnimation, pyqtProperty, QEasingCurve, QPointF,
	QModelIndex, 
)
from PyQt6.QtWidgets import (
	QApplication, QFrame, QVBoxLayout, QLabel, QTableWidgetItem, QListWidget, QScrollBar,
	QListWidgetItem, QLineEdit, QComboBox, QSizePolicy, QStyledItemDelegate, QStyleOptionViewItem,
	QStyledItemDelegate,
)
from PyQt6.QtGui import (
	QColor, QKeyEvent, QMouseEvent, QCursor, QPainter, QPalette, QLinearGradient, QGradient,
)

from qt_material import apply_stylesheet, get_theme, list_themes

import qavm.qavmapi.utils as qutils

class DateTimeTableWidgetItem(QTableWidgetItem):
	def __init__(self, date: dt.datetime, format: str):
		self.date: dt.datetime = date
		self.format: str = format
		super().__init__(self.date.strftime(self.format))

	def __lt__(self, other):
		if isinstance(other, DateTimeTableWidgetItem):
			return self.date < other.date
		return super().__lt__(other)

# Copied from experiments on 26th of June 2024
class StaticBorderWidget(QFrame):
	def __init__(self, color: QColor, parent=None):
		super().__init__(parent)

		self._color = color
		self.setStyleSheet(self._getBackgroundColorStyle())
		self.setLayout(QVBoxLayout(self))

	def _getBackgroundColorStyle(self):
		cssColorString = f"rgba({self._color.red()}, {self._color.green()}, {self._color.blue()}, {self._color.alpha()})"
		return (f"background-color: {cssColorString}")

# Copied from experiments on 19th of May 2025
class RunningBorderWidget(QFrame):
	def __init__(self, accentColor: QColor, tailColor: QColor, parent=None):
		super().__init__(parent)

		self._accentColor = accentColor
		self._tailColor = tailColor
		
		self.setStyleSheet(self._getBackgroundColorGradientStyle(0))

		self._bgGradientDirection = 0
		self.bgGradientAnim = QPropertyAnimation(self, b'bgGradientDirection')
		self.bgGradientAnim.setStartValue(360)
		self.bgGradientAnim.setEndValue(0)
		self.bgGradientAnim.setDuration(2000)
		self.bgGradientAnim.setLoopCount(-1)
		self.bgGradientAnim.start()

		self.setLayout(QVBoxLayout(self))

	def _getBackgroundColorGradientStyle(self, direction):
		cssAccentColorString = f"rgba({self._accentColor.red()}, {self._accentColor.green()}, {self._accentColor.blue()}, {self._accentColor.alpha()})"
		cssTailColorString = f"rgba({self._tailColor.red()}, {self._tailColor.green()}, {self._tailColor.blue()}, {self._tailColor.alpha()})"
		return ("background-color: qconicalgradient("
																f"cx: 0.5, cy: 0.5, angle: {direction}, "
																f"stop: 0.00 {cssAccentColorString}, "
																f"stop: 0.10 {cssTailColorString}, "
																f"stop: 0.90 {cssTailColorString}, "
																f"stop: 1.00 {cssAccentColorString});")
	
	@pyqtProperty(int)
	def bgGradientDirection(self):
		return self._bgGradientDirection
	
	@bgGradientDirection.setter
	def bgGradientDirection(self, dir):
		self._bgGradientDirection = dir
		self.setStyleSheet(self._getBackgroundColorGradientStyle(dir))

class ClickableLabel(QLabel):
	# TODO: change this to get modifier keys from the event instead
	clickedLeft = pyqtSignal(bool, bool, bool)  # ctrl, alt, shift
	clickedRight = pyqtSignal(bool, bool, bool)  # ctrl, alt, shift
	clickedMiddle = pyqtSignal(bool, bool, bool)  # ctrl, alt, shift
	
	clickedAny = pyqtSignal(bool, bool, bool)  # ctrl, alt, shift

	def __init__(self, parent=None):
		super().__init__(parent)

	def mousePressEvent(self, evt):
		# get modifier keys
		ctrl = bool(evt.modifiers() & Qt.KeyboardModifier.ControlModifier)
		alt = bool(evt.modifiers() & Qt.KeyboardModifier.AltModifier)
		shift = bool(evt.modifiers() & Qt.KeyboardModifier.ShiftModifier)
		
		self.clickedAny.emit(ctrl, alt, shift)
		if evt.button() == Qt.MouseButton.LeftButton:
			self.clickedLeft.emit(ctrl, alt, shift)
		elif evt.button() == Qt.MouseButton.RightButton:
			self.clickedRight.emit(ctrl, alt, shift)
		elif evt.button() == Qt.MouseButton.MiddleButton:
			self.clickedMiddle.emit(ctrl, alt, shift)
		super().mousePressEvent(evt)


class DeletableListWidget(QListWidget):
	itemDeleted = pyqtSignal(QListWidgetItem)

	def keyPressEvent(self, event: QKeyEvent) -> None:
		if event.key() == Qt.Key.Key_Delete:
			for item in self.selectedItems():
				self.takeItem(self.row(item))
				self.itemDeleted.emit(item)
		else:
			super().keyPressEvent(event)

class EmptySpaceDoubleClickableListWidget(DeletableListWidget):
	def mouseDoubleClickEvent(self, event):
		item = self.itemAt(event.pos())

		if item is None:
			# Clicked on empty space -> Add new editable item
			new_item = QListWidgetItem("Enter path")
			new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsEditable)
			self.addItem(new_item)
			self.editItem(new_item)
		else:
			# Default behavior (optional: start editing existing item)
			super().mouseDoubleClickEvent(event)

class PathsListWidget(EmptySpaceDoubleClickableListWidget):
	urlDropped = pyqtSignal(str)  # Signal emitted when a url is dropped

	def __init__(self, parent=None):
		super().__init__(parent)
		
		self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
		self.setEditTriggers(QListWidget.EditTrigger.DoubleClicked)
		self.setAcceptDrops(True)

	def DoAcceptPath(self, path: str) -> bool:
		""" Override this method to accept or reject the path. """
		return True
		
	def dragEnterEvent(self, event):
		if event.mimeData().hasUrls():
			event.acceptProposedAction()

	def dragMoveEvent(self, event):
		event.acceptProposedAction()

	def dropEvent(self, event):
		if event.mimeData().hasUrls():
			for url in event.mimeData().urls():
				localPathStr: str = url.toLocalFile()
				if self.DoAcceptPath(localPathStr):
					self.urlDropped.emit(localPathStr)
		event.acceptProposedAction()

class FolderPathsListWidget(PathsListWidget):
	""" A list widget that accepts only folder paths to be dropped on. """
	def DoAcceptPath(self, path: str) -> bool:
		""" Accept only folders, reject files. """
		return Path(path).is_dir()
	

class AnimatedRowGradientDelegate(QStyledItemDelegate):
	""" A delegate that animates the background gradient of the entire row in a table widget. """
	def __init__(self, parent = None):
		super().__init__(parent)
		self._pos = 0.0

		self.type = 1  # 0 - bouncing, 1 - wrapping  # TODO: make it configurable and enum
		
		self.anim = QPropertyAnimation(self, b"pos", self)

		if self.type == 0:
			self.anim.setDuration(10000)
			self.anim.setKeyValueAt(0.0, 0.0)
			self.anim.setKeyValueAt(0.5, 1.0)
			self.anim.setKeyValueAt(1.0, 0.0)
		elif self.type == 1:
			self.anim.setDuration(5000)
			self.anim.setKeyValueAt(0.0, 1.0)
			self.anim.setKeyValueAt(1.0, 0.0)
		
		self.anim.setLoopCount(-1)
		self.anim.setEasingCurve(QEasingCurve.Type.Linear)
		self.anim.start()
	
	def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
		tableWidget = option.widget
		row = index.row()
		descIdx: int = int(tableWidget.item(row, tableWidget.columnCount() - 1).text())
		if self.IsSpecialPaint(descIdx):
			return self._doPpaint(painter, option, index)

		QStyledItemDelegate.paint(self, painter, option, index)

	def IsSpecialPaint(self, descIdx: int):
		raise NotImplementedError("IsSpecialPaint method should be implemented in a subclass")

	def _doPpaint(self, painter: QPainter, option, index):
		table = option.widget  # or maybe use self.parent() instead?
		if table is None:
			return super().paint(painter, option, index)

		tableContentColumnsWidth = sum(table.columnWidth(c) for c in range(table.columnCount()))
		# scrollBarVerticalWidth = table.verticalScrollBar().width() if table.verticalScrollBar().isVisible() else 0
		# verticalHeaderWidth = table.verticalHeader().width()
		
		hScrollBar: QScrollBar = table.horizontalScrollBar()
		# scrollOffPercent = hScrollBar.value() / max(hScrollBar.maximum(), 1)
		# scrollOffset = hScrollBar.sliderPosition()
		scrollOffset = hScrollBar.value()

		# left = 0 - scrollOffset
		# right = 2 * tableContentColumnsWidth - scrollOffset
		
		left = -tableContentColumnsWidth * self._pos - scrollOffset
		right = 2 * tableContentColumnsWidth - tableContentColumnsWidth * self._pos - scrollOffset
		
		grad = QLinearGradient(QPointF(left, 0), QPointF(right, 0))
		
		grad.setCoordinateMode(QGradient.CoordinateMode.LogicalMode)
		grad.setSpread(QGradient.Spread.PadSpread)

		if self.type == 0:
			colorMid = QColor(255, 255, 255)  # TODO: get background color from theme
			colorEnd = QColor(Qt.GlobalColor.darkGreen)
			colorEnd.setAlpha(75)
			stripeWPercent = 0.35

			grad.setColorAt(0.0, colorMid)
			grad.setColorAt(0.5 - stripeWPercent / 2, colorMid)
			grad.setColorAt(0.5, colorEnd)
			grad.setColorAt(0.5 + stripeWPercent / 2, colorMid)
			grad.setColorAt(1.0, colorMid)
		elif self.type == 1:
			colorMidMy = QColor(255, 255, 255)
			colorEndMy = QColor(Qt.GlobalColor.darkGreen)
			colorEndMy.setAlpha(75)
			stripeWPercent = 0.35

			colorEnd1 = colorEndMy
			colorMid = colorMidMy
			colorEnd2 = colorEndMy
			grad.setColorAt(0.0, colorEnd1)
			grad.setColorAt(0.0 + stripeWPercent / 2, colorMid)
			grad.setColorAt(0.5 - stripeWPercent / 2, colorMid)
			grad.setColorAt(0.5, colorEnd2)
			grad.setColorAt(0.5 + stripeWPercent / 2, colorMid)
			grad.setColorAt(1.0 - stripeWPercent / 2, colorMid)
			grad.setColorAt(1.0, colorEnd1)

		painter.save()
		painter.fillRect(option.rect, grad)
		# painter.setPen(option.palette.color(option.palette.ColorRole.Text))
		# painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, index.data())
		painter.restore()
		return super().paint(painter, option, index)

	def getPos(self) -> float:
		return self._pos
	
	def setPos(self, v: float):
		tableWidget = self.parent()
		if tableWidget is None:
			return
		
		self._pos = v
		tableWidget.viewport().update()  # this is likely expensive, so should be better solution for multiple rows repainting
		return
	
		# repaint exactly the span of the whole row
		# first = tableWidget.model().index(self.target_row, 0)
		# last  = tableWidget.model().index(self.target_row, tableWidget.columnCount() - 1)
		first = tableWidget.model().index(0, 0)
		last  = tableWidget.model().index(tableWidget.rowCount(), tableWidget.columnCount() - 1)
		row_rect = (tableWidget.visualRect(first).united(tableWidget.visualRect(last)))
		tableWidget.viewport().update(row_rect)

	pos = pyqtProperty(float, getPos, setPos)


class RunningDescriptorAnimatedRowGradientDelegate(AnimatedRowGradientDelegate):
	def IsSpecialPaint(self, descIdx: int):
		return False  # TODO: temporarily disabled to get rid of crash
		descs = QApplication.instance().GetSoftwareDescriptors()
		if descIdx >= len(descs):
			return False
		
		return qutils.IsProcessRunning(descs[descIdx].UID)


DEFAULT_THEME_MODE = 'light'  # Default theme mode, can be 'light' or 'dark'
DEFAULT_THEME_COLOR = 'purple'  # Default theme color, can be 'purple', 'pink', 'green', etc.

def GetDefaultTheme() -> str:
	return f'{DEFAULT_THEME_MODE}_{DEFAULT_THEME_COLOR}.xml'

g_CurrentTheme: str = GetDefaultTheme()
def GetThemeName() -> str:
	return g_CurrentTheme

def IsThemeDark() -> bool:
	return 'dark' in g_CurrentTheme

def SetTheme(theme: str) -> None:
	global g_CurrentTheme
	app: QApplication = QApplication.instance()
	
	apply_stylesheet(app, theme=theme, extra={'density_scale': '-1'})
	g_CurrentTheme = theme
	
	# TODO: use secondColor as a background color for the scrollbar
	styleExtraScrollBar = """
		QScrollBar:vertical {
			width: 14px;
			margin: 0px;
		}

		QScrollBar:horizontal {
			height: 14px;
			margin: 0px;
		}

		QScrollBar::handle:vertical {
			min-height: 20px;
			background-color: #888;
			border-radius: 7px;
		}

		QScrollBar::handle:horizontal {
			min-width: 20px;
			background-color: #888;
			border-radius: 7px;
		}

		QScrollBar::add-line,
		QScrollBar::sub-line {
			background: none;
			border: none;
		}

		QScrollBar::add-page,
		QScrollBar::sub-page {
			background: none;
		}
	"""

	styleExtraLineEdit = ""
	if IsThemeDark():
		styleExtraLineEdit = """
		QLineEdit, QComboBox {
				color: white;
		}
		"""
	else:
		styleExtraLineEdit = """
		QLineEdit, QComboBox {
				color: black;
		}
		"""

	styleExtraTreeview = """
		QTreeView::item {
			padding: 0px 0px;
			height: 10px;
		}
		QTreeView::branch {
			padding: 0px;
			margin: 0px;
		}
	"""
		
	# Append custom style to override scrollbar thickness
	app.setStyleSheet(app.styleSheet() + styleExtraScrollBar + styleExtraLineEdit + styleExtraTreeview)

def GetThemesList() -> list[str]:
	return list_themes()

def GetThemeData() -> dict[str, str | None] | None:
	return get_theme(GetThemeName())