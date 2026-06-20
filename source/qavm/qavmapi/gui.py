import datetime as dt
import html
import re
from pathlib import Path
from typing import TYPE_CHECKING
import markdown

from PyQt6.QtCore import (
	Qt, pyqtSignal, QPropertyAnimation, pyqtProperty, QEasingCurve, QPointF,
	QModelIndex, QSize, QRect, QTimer, QPoint,
)
from PyQt6.QtWidgets import (
	QApplication, QFrame, QPlainTextEdit, QPushButton, QVBoxLayout, QLabel, QTableWidgetItem, QListWidget, QScrollBar,
	QListWidgetItem, QLineEdit, QComboBox, QSizePolicy, QStyledItemDelegate, QStyleOptionViewItem,
	QStyledItemDelegate, QHBoxLayout, QDialog, QWidget, QMenu
)
from PyQt6.QtGui import (
	QColor, QKeyEvent, QMouseEvent, QCursor, QPainter, QPalette, QLinearGradient, QGradient, QAction, QFont
)

import pyperclip
from qt_material import apply_stylesheet, get_theme, list_themes

import qavm.qavmapi.utils as qutils
from qavm.utils_gui import BubbleWidget, FadeTooltip

class NumberTableWidgetItem(QTableWidgetItem):
	def __init__(self, value: int | float, format: str = '{}'):
		self.value: int | float = value
		self.format: str = format
		super().__init__(self.format.format(self.value))
	
	def __lt__(self, other):
		if isinstance(other, NumberTableWidgetItem):
			return self.value < other.value
		return super().__lt__(other)

class DateTimeTableWidgetItem(QTableWidgetItem):
	def __init__(self, date: dt.datetime, format: str):
		self.date: dt.datetime = date
		self.format: str = format
		super().__init__(self.date.strftime(self.format))

	def __lt__(self, other):
		if isinstance(other, DateTimeTableWidgetItem):
			return self.date < other.date
		return super().__lt__(other)
	
class PathTableWidgetItem(QTableWidgetItem):
	def __init__(self, path: Path, showExpandLinks: bool = True):
		self.path: Path = path
		if showExpandLinks:
			dirPrefix: str = ''
			dirPostfix: str = ''
			if qutils.IsPathSymlinkF(self.path):
				dirPrefix = '(S) '
				if target := qutils.GetSymlinkFTarget(self.path):
					dirPostfix = f' ( → {target})'
			elif qutils.IsPathSymlinkD(self.path):
				dirPrefix = '(L) '
				if target := qutils.GetSymlinkDTarget(self.path):
					dirPostfix = f' ( → {target})'
			elif qutils.IsPathJunction(self.path):
				dirPrefix = '(J) '
				if target := qutils.GetJunctionTarget(self.path):
					dirPostfix = f' ( → {target})'
			elif qutils.IsPathShortcut(self.path):
				dirPrefix = '(C) '
				if target := qutils.GetShortcutTarget(self.path):
					dirPostfix = f' ( → {target})'
		super().__init__(f"{dirPrefix}{str(self.path)}{dirPostfix}")

	def __lt__(self, other):
		if isinstance(other, PathTableWidgetItem):
			return str(self.path) < str(other.path)
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
	
class CopyableTextDialog(QDialog):
	MAX_WIDTH: int = 600

	def __init__(self, title: str, text: str, parent: QWidget = None):
		super().__init__(parent)
		self.setWindowTitle(title)
		self._text = text

		layout = QVBoxLayout(self)

		isMultiline = '\n' in text
		if isMultiline:
			self._textEdit = QPlainTextEdit(text)
			self._textEdit.setReadOnly(True)
		else:
			self._textEdit = QLineEdit(text)
			self._textEdit.setReadOnly(True)
		layout.addWidget(self._textEdit)

		btnLayout = QHBoxLayout()
		copyBtn = QPushButton("Copy")
		copyBtn.clicked.connect(self._copyText)
		btnLayout.addWidget(copyBtn)
		layout.addLayout(btnLayout)

		self._adjustWidth()

	def _adjustWidth(self):
		fm = self._textEdit.fontMetrics()
		if isinstance(self._textEdit, QLineEdit):
			textWidth = fm.horizontalAdvance(self._text)
		else:
			textWidth = max(fm.horizontalAdvance(line) for line in self._text.splitlines()) if self._text else 0
		margins = self.layout().contentsMargins()
		padding = margins.left() + margins.right() + 80  # scrollbar + inner padding
		self.setFixedWidth(min(textWidth + padding, CopyableTextDialog.MAX_WIDTH))

	def _copyText(self):
		pyperclip.copy(self._text)

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

class ClickableSubmenuMenu(QMenu):
	"""A QMenu subclass that allows the top-level menu entry to be clicked while
	also exposing a submenu. Based on clickable_submenu.py experiment.
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.click_handlers: dict[QAction, callable] = {}

	def setClickHandler(self, action: QAction, handler: callable):
		self.click_handlers[action] = handler

	def mouseReleaseEvent(self, event):
		action = self.actionAt(event.position().toPoint())
		if action in self.click_handlers:
			try:
				self.click_handlers[action]()
			except Exception:
				print('ClickableSubmenuMenu: click handler failed')
			self.close()
			return
		super().mouseReleaseEvent(event)


def PickContrastingTextColor(bgColor: QColor | None) -> QColor:
	""" Returns black or white depending on the perceived luminance (ITU-R BT.601) of the background color. """
	if bgColor is None:
		return QColor('black')
	luminance: float = (0.299 * bgColor.red() + 0.587 * bgColor.green() + 0.114 * bgColor.blue()) / 255.0
	return QColor('black') if luminance > 0.55 else QColor('white')


class HoverFadeTooltipMixin(QWidget if TYPE_CHECKING else object):
	""" Mixin that lazily shows a rich-text FadeTooltip after the mouse hovers for TOOLTIP_DELAY_MS.

	Mix into any QWidget subclass (e.g. QWidget, QLabel) and call _InitHoverTooltip() from the host's
	__init__. Subclasses drive the hover timer from their own mouse handlers via _ScheduleTooltip() /
	_CancelTooltip() and supply the tooltip content by overriding _GetTooltipHtml() (return None or ''
	to suppress it). This centralises the hover-timer + FadeTooltip plumbing that is otherwise duplicated
	across widgets.

	When persistentTooltip=True the tooltip becomes interactive (selectable text, clickable links) and stays
	visible while the cursor is over either this widget or the tooltip itself, so the user can move onto it. """
	TOOLTIP_DELAY_MS: int = 300
	TOOLTIP_PERSIST_GRACE_MS: int = 250  # time to travel from the widget onto the persistent tooltip

	def _InitHoverTooltip(self, persistentTooltip: bool = False) -> None:
		""" Sets up the hover/hide timers and tooltip state. Call from the host widget's __init__. """
		self.setMouseTracking(True)
		self._persistentTooltip: bool = persistentTooltip
		self._tooltip: FadeTooltip | None = None
		self._hoverTimer: QTimer = QTimer(self)
		self._hoverTimer.setSingleShot(True)
		self._hoverTimer.timeout.connect(self._showTooltip)
		# Grace timer used only in persistent mode to bridge the gap between leaving the widget and
		# entering the tooltip (and to dismiss the tooltip shortly after the cursor leaves it).
		self._hideTimer: QTimer = QTimer(self)
		self._hideTimer.setSingleShot(True)
		self._hideTimer.timeout.connect(self._hideTooltipNow)

	def _ScheduleTooltip(self) -> None:
		""" (Re)starts the hover delay timer after which the tooltip is shown. """
		self._hideTimer.stop()
		self._hoverTimer.start(self.TOOLTIP_DELAY_MS)

	def _CancelTooltip(self) -> None:
		""" Stops a pending tooltip and dismisses the visible one (after a grace period when persistent). """
		self._hoverTimer.stop()
		if not self._tooltip:
			return
		if self._persistentTooltip:
			# Allow the cursor to reach the tooltip before hiding it.
			self._hideTimer.start(self.TOOLTIP_PERSIST_GRACE_MS)
		else:
			self._tooltip.hideWithFade()

	def _hideTooltipNow(self) -> None:
		if self._tooltip:
			self._tooltip.hideWithFade()

	def _GetTooltipHtml(self) -> str | None:
		""" Returns the rich-text (HTML) tooltip content, or None/'' to suppress the tooltip. """
		return None

	def _showTooltip(self) -> None:
		tooltipHtml: str | None = self._GetTooltipHtml()
		if not tooltipHtml:
			return
		if self._tooltip is None:
			self._tooltip = FadeTooltip(self, interactive=self._persistentTooltip)
			if self._persistentTooltip:
				self._tooltip.mouseEntered.connect(self._hideTimer.stop)
				self._tooltip.mouseLeft.connect(self._onTooltipLeft)
		# Stop any pending hide and compute a position that centers the tooltip
		# horizontally on the cursor (with a small vertical offset). Clamp to
		# the primary screen's available geometry so the tooltip remains on-screen.
		self._hideTimer.stop()
		# Pre-measure the tooltip size by setting the text and adjusting.
		self._tooltip.setText(tooltipHtml)
		self._tooltip.adjustSize()
		tip_w = self._tooltip.width()
		tip_h = self._tooltip.height()
		cursor_pos = QCursor.pos()
		x = cursor_pos.x() - tip_w // 2
		y = cursor_pos.y() + 18
		
		screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
		if screen is not None:
			geo = screen.availableGeometry()
			x = max(geo.left(), min(x, geo.right() - tip_w))
			y = max(geo.top(), min(y, geo.bottom() - tip_h))
		self._tooltip.showText(tooltipHtml, QPoint(x, y))

	def _onTooltipLeft(self) -> None:
		# Cursor left the persistent tooltip; dismiss it after the grace period (cancelled if it returns).
		self._hideTimer.start(self.TOOLTIP_PERSIST_GRACE_MS)

	def leaveEvent(self, event):
		self._CancelTooltip()
		super().leaveEvent(event)


class HoverFadeTooltipWidget(HoverFadeTooltipMixin, QWidget):
	""" QWidget that lazily shows a rich-text FadeTooltip on hover (see HoverFadeTooltipMixin). """
	def __init__(self, parent: QWidget | None = None, persistentTooltip: bool = False):
		super().__init__(parent)
		self._InitHoverTooltip(persistentTooltip)


class TagBubblesFlowWidget(HoverFadeTooltipWidget):
	""" Flow-laid-out collection of colorful tag bubbles for use inside table cells and tiles.

	Bubbles wrap onto multiple lines so none are clipped horizontally. The total height is capped by
	maxHeight; tags that don't fit are collapsed into a trailing '+N' bubble. The container receives
	mouse events to provide per-tag hover tooltips and Ctrl+LMB editing, while forwarding all other
	mouse interactions (plain click, context menu, tag drag-n-drop) to the underlying table/tile so
	row selection and existing behaviour keep working. Intended to be returned from
	BaseTableBuilder.GetTableCellValue and consumed via QTableWidget.setCellWidget. """
	HSPACING: int = 2
	VSPACING: int = 2
	MARGIN: int = 2
	BUBBLE_ROUNDING: float = 10.0
	BUBBLE_MARGIN: int = 5

	# Emitted when the bubbles re-wrap into a different total height after being laid out at the
	# widget's actual width. The actual cell width is slightly narrower than the column width used
	# for the initial row-height estimate, so the host (e.g. the table) must re-measure the row.
	contentHeightChanged = pyqtSignal()

	def __init__(self, tags: list, maxHeight: int, parent: QWidget | None = None):
		super().__init__(parent, persistentTooltip=True)
		self._maxHeight: int = max(maxHeight, 1)
		self._lastContentHeight: int = -1
		self.setAutoFillBackground(False)

		self._tags: list = list(tags)
		self._tagNames: list[str] = [tag.GetName() for tag in tags]
		self._tagOrders: list[int] = [tag.GetOrder() for tag in tags]
		self._bubbles: list[BubbleWidget] = [
			self._createBubble(tag.GetName(), QColor(tag.GetColor()) if tag.GetColor() else None)
			for tag in tags
		]
		self._overflowBubble: BubbleWidget | None = None
		self._emptyPlaceholder: QLabel | None = None

		self._hoveredIndex: int = -1

	def GetSortKey(self) -> str:
		""" Returns a stable key used to sort the Tags column (comma-joined, lower-cased tag names). """
		SORT_WIDTH = 20  # enough for 64-bit unsigned integers
		orders: list[int] = self._tagOrders if self._tagOrders else [pow(10, SORT_WIDTH) - 1]
		return ', '.join(f"{x:0{SORT_WIDTH}d}" for x in orders).lower()

	def _createBubble(self, text: str, bgColor: QColor | None) -> BubbleWidget:
		bubble: BubbleWidget = BubbleWidget(text, bgColor=bgColor, rounding=self.BUBBLE_ROUNDING, margin=self.BUBBLE_MARGIN)
		bubble.setParent(self)
		bubble.setStyleSheet(f'color: {PickContrastingTextColor(bgColor).name()};')
		bubble.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
		return bubble

	def _ensureOverflowBubble(self) -> QWidget:
		"""Create a lightweight overflow label with no background/border.
		This appears as plain "+N" text (no bubble background).
		"""
		if self._overflowBubble is None:
			lbl = QLabel('', self)
			lbl.setContentsMargins(self.BUBBLE_MARGIN, self.BUBBLE_MARGIN, self.BUBBLE_MARGIN, self.BUBBLE_MARGIN)
			accent_color = '#9e9e9e'
			if themeData := GetThemeData():
				accent_color = themeData.get('primaryColor', '#ffffff')
			lbl.setStyleSheet(f'color: {accent_color}; background: transparent; border: 1px solid {accent_color}; border-radius: {int(self.BUBBLE_ROUNDING)}px;')
			lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
			self._overflowBubble = lbl
		return self._overflowBubble

	def _ensureEmptyPlaceholder(self) -> QWidget:
		""" Creates (once) a plain '-' label shown when there are no tags. """
		if self._emptyPlaceholder is None:
			lbl = QLabel('-', self)
			lbl.setContentsMargins(self.BUBBLE_MARGIN, self.BUBBLE_MARGIN, self.BUBBLE_MARGIN, self.BUBBLE_MARGIN)
			lbl.setStyleSheet('background: transparent;')
			lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
			self._emptyPlaceholder = lbl
		return self._emptyPlaceholder

	def _doLayout(self, width: int, apply: bool) -> int:
		""" Lays out the bubbles within the given width, capped by maxHeight.

		When apply is True the child bubbles are geometried and shown/hidden; otherwise this only
		measures. Returns the total height (clamped to maxHeight) the content occupies. """
		m, hsp, vsp = self.MARGIN, self.HSPACING, self.VSPACING
		maxH: int = self._maxHeight
		bubbles: list[BubbleWidget] = self._bubbles
		n: int = len(bubbles)
		effRight: int = max(width - m, m + 1)

		if n == 0:
			placeholder: QWidget = self._ensureEmptyPlaceholder()
			pw, ph = placeholder.sizeHint().width(), placeholder.sizeHint().height()
			if apply:
				placeholder.setGeometry(QRect(m, m, pw, ph))
				placeholder.setVisible(True)
			return min(m + ph + m + self.MARGIN * 2 + self.VSPACING * 2, maxH)

		placements: list[tuple[QWidget, QRect]] = []
		x: int = m
		y: int = m
		lineHeight: int = 0
		hiddenStart: int = n

		i: int = 0
		while i < n:
			sz: QSize = bubbles[i].sizeHint()
			bw, bh = sz.width(), sz.height()
			if placements and x + bw > effRight and lineHeight > 0:
				nextY: int = y + lineHeight + vsp
				if nextY + bh + m > maxH:
					hiddenStart = i
					break
				x, y, lineHeight = m, nextY, 0
			placements.append((bubbles[i], QRect(x, y, bw, bh)))
			x += bw + hsp
			lineHeight = max(lineHeight, bh)
			i += 1

		if hiddenStart < n:
			hiddenCount: int = n - hiddenStart
			overflow: BubbleWidget = self._ensureOverflowBubble()
			overflow.setText(f'+{hiddenCount}')
			ow, oh = overflow.sizeHint().width(), overflow.sizeHint().height()
			# Make room for the overflow bubble at the end of the current (last) row.
			while placements and x + ow > effRight:
				poppedRect: QRect = placements[-1][1]
				if poppedRect.y() != y:
					break
				placements.pop()
				hiddenCount += 1
				overflow.setText(f'+{hiddenCount}')
				ow, oh = overflow.sizeHint().width(), overflow.sizeHint().height()
				x = poppedRect.x()
			placements.append((overflow, QRect(x, y, ow, oh)))
			lineHeight = max(lineHeight, oh)

		if apply:
			visible: set[int] = set()
			for w, rect in placements:
				w.setGeometry(rect)
				w.setVisible(True)
				visible.add(id(w))
			for b in bubbles:
				if id(b) not in visible:
					b.setVisible(False)
			if self._overflowBubble is not None and id(self._overflowBubble) not in visible:
				self._overflowBubble.setVisible(False)

		# add a tiny padding to avoid clipping by table cell borders/rounding
		return min(y + lineHeight + m + self.MARGIN * 2 + self.VSPACING * 2, maxH)

	def hasHeightForWidth(self) -> bool:
		return True

	def heightForWidth(self, width: int) -> int:
		return self._doLayout(width, apply=False)

	def sizeHint(self) -> QSize:
		w: int = self.width() if self.width() > 0 else 200
		return QSize(w, self.heightForWidth(w))

	def minimumSizeHint(self) -> QSize:
		if not self._bubbles:
			return QSize(0, 2 * self.MARGIN)
		first: QSize = self._bubbles[0].sizeHint()
		return QSize(first.width() + 2 * self.MARGIN, first.height() + 2 * self.MARGIN)

	def resizeEvent(self, event):
		contentHeight: int = self._doLayout(self.width(), apply=True)
		super().resizeEvent(event)
		# The widget is laid out at its real (cell) width here, which can wrap a bubble that the
		# column-width-based estimate thought would fit. Notify the host so it can grow the row.
		if contentHeight != self._lastContentHeight:
			self._lastContentHeight = contentHeight
			self.contentHeightChanged.emit()

	# region Interaction (hover tooltip + Ctrl+LMB edit)
	def _tagIndexAt(self, pos: QPoint) -> int:
		""" Returns the index into self._tags of the visible tag bubble at pos, or -1 if none. """
		for i, bubble in enumerate(self._bubbles):
			if bubble.isVisible() and bubble.geometry().contains(pos):
				return i
		return -1

	def GetTagAt(self, pos: QPoint):
		""" Returns the tag whose visible bubble is at the given local position, or None. """
		idx: int = self._tagIndexAt(pos)
		return self._tags[idx] if 0 <= idx < len(self._tags) else None

	def mouseMoveEvent(self, event: QMouseEvent):
		idx: int = self._tagIndexAt(event.pos())
		if idx != self._hoveredIndex:
			self._hoveredIndex = idx
			self._CancelTooltip()
			if idx >= 0:
				self._ScheduleTooltip()
		# Let the underlying table/tile keep handling hover and rubber-band selection.
		event.ignore()

	def mousePressEvent(self, event: QMouseEvent):
		isCtrlLeft: bool = (event.button() == Qt.MouseButton.LeftButton
							and bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
		if isCtrlLeft:
			idx: int = self._tagIndexAt(event.pos())
			if idx >= 0:
				self._CancelTooltip()
				event.accept()
				self._openTagEditor(self._tags[idx])
				return
		# Anything else (plain click, right click, drag) belongs to the table/tile underneath.
		event.ignore()

	def leaveEvent(self, event):
		self._hoveredIndex = -1
		super().leaveEvent(event)

	def _openTagEditor(self, tag) -> None:
		# Lazy import to avoid a qavmapi -> app-window import cycle at module load time.
		from qavm.window_tag_editor import OpenTagEditorDialog
		OpenTagEditorDialog(tag, self)

	def _GetTooltipHtml(self) -> str | None:
		if self._hoveredIndex < 0 or self._hoveredIndex >= len(self._tags):
			return None
		return self._buildTooltipHtml(self._tags[self._hoveredIndex])

	def _buildTooltipHtml(self, tag) -> str:
		""" Tooltip: hovered tag's description, a separator, then the full list of the descriptor's tags. """
		def swatch(colorStr: str) -> str:
			return f'<span style="display:inline-block;width:1.1em;height:0.9em;background-color:{colorStr};margin-right:0.3em;border-radius:2px;vertical-align:middle;">{"&nbsp;"*5}</span>' if colorStr else ''

		header: str = f'{swatch(tag.GetColor())} <b>{html.escape(tag.GetName())}</b>'
		if description := tag.GetDescription() if hasattr(tag, 'GetDescription') else '':
			header += f'<div style="margin-top:4px;margin-bottom:6px;">{PlainTextToTooltipHtml(description)}</div>'

		# Build a simple table for the tag list: marker | color | name
		rows: list[str] = []
		for t in self._tags:
			marker: str = '&rarr;' if t is tag else '&bull;'
			color_cell = swatch(t.GetColor() or "")
			name_cell = html.escape(t.GetName())
			rows.append(f'<tr><td style="padding:2px 6px;width:1%">{marker}</td><td style="padding:2px 6px;width:1%">{color_cell}</td><td style="padding:2px 6px;">{name_cell}</td></tr>')

		table_html = (
			f'<div>{header}</div>'
			f'<hr style="margin:6px 0;">'
			f'<table style="border-collapse:collapse;font-size:90%;">'
			+ ''.join(rows)
			+ '</table>'
		)
		return table_html
	# endregion


class DescNotesWidget(HoverFadeTooltipWidget):
	""" Displays a descriptor's small note as a single label and, on hover, shows a FadeTooltip with the
	small note followed by the detailed note (rendered as escaped plain text).

	In the common case it renders just like a plain note label. Mouse interactions other than hover are
	forwarded to the underlying table/tile so row selection, context menus and drag-n-drop keep working.
	Intended to be used both as a tile widget and as a table cell widget (via QTableWidget.setCellWidget);
	GetSortKey enables sorting the Note column. """
	MARGIN: int = 0

	def __init__(self, noteSmall: str, noteDetail: str = '', parent: QWidget | None = None,
				alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter, font: QFont | None = None,
				persistentTooltip: bool = False):
		super().__init__(parent, persistentTooltip=persistentTooltip)
		self._noteSmall: str = noteSmall or ''
		self._noteDetail: str = noteDetail or ''

		self._label: QLabel = QLabel(self._noteSmall, self)
		self._label.setAlignment(alignment)
		self._label.setWordWrap(True)
		if font is not None:
			self._label.setFont(font)
		# The label is decorative; all mouse events go through the container (and on to the table/tile).
		self._label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

	def resizeEvent(self, event):
		""" Stretch the label to cover the full widget rect so alignment applies relative to the whole area.
		This matters in table cells where setCellWidget sizes the widget to the row height. """
		self._label.setGeometry(self.rect())
		super().resizeEvent(event)

	def sizeHint(self) -> QSize:
		return self._label.sizeHint()

	def minimumSizeHint(self) -> QSize:
		return self._label.minimumSizeHint()

	def GetSortKey(self) -> str:
		""" Returns a stable key used to sort the Note column (lower-cased small note). """
		return self._noteSmall.lower()

	def mouseMoveEvent(self, event: QMouseEvent):
		if self._noteSmall or self._noteDetail:
			self._ScheduleTooltip()
		# Let the underlying table/tile keep handling hover and rubber-band selection.
		event.ignore()

	def mousePressEvent(self, event: QMouseEvent):
		# Clicks, context menus and drags belong to the table/tile underneath.
		event.ignore()

	def _GetTooltipHtml(self) -> str | None:
		if not self._noteSmall and not self._noteDetail:
			return None
		parts: list[str] = []
		if self._noteSmall:
			parts.append(f'<div><b>{html.escape(self._noteSmall)}</b></div>')
		if self._noteDetail:
			if self._noteSmall:
				parts.append('<hr style="margin:6px 0;">')
			# The detailed note is plain text entered by the user; escape it and keep its line breaks.
			parts.append(f'<div>{PlainTextToTooltipHtml(self._noteDetail)}</div>')
		return ''.join(parts)


_ANCHOR_RE = re.compile(r'<a\b[^>]*>.*?</a>', re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r'<[^>]+>')
_URL_RE = re.compile(r'(?:https?://|www\.)[^\s<>"\'\)\]]+', re.IGNORECASE)

def _linkifyPlainText(text: str) -> str:
	def _repl(match: re.Match) -> str:
		url: str = match.group(0)
		trailing: str = ''
		while url and url[-1] in '.,;:!?\'")]}':
			trailing = url[-1] + trailing
			url = url[:-1]
		if not url:
			return match.group(0)
		href: str = url if url.lower().startswith(('http://', 'https://')) else f'http://{url}'
		return f'<a href="{href}">{url}</a>{trailing}'
	return _URL_RE.sub(_repl, text)

def _linkifyOutsideTags(text: str) -> str:
	""" Linkifies URLs found in the text nodes only, leaving existing HTML tags untouched. """
	result: list[str] = []
	pos: int = 0
	for tagMatch in _TAG_RE.finditer(text):
		result.append(_linkifyPlainText(text[pos:tagMatch.start()]))
		result.append(tagMatch.group(0))
		pos = tagMatch.end()
	result.append(_linkifyPlainText(text[pos:]))
	return ''.join(result)

def LinkifyText(text: str) -> str:
	""" Wraps bare URLs (http(s):// or www.) in <a> tags, skipping URLs already inside <a>...</a> anchors
	and inside HTML tags. Intended for rich-text tooltips. """
	if not text:
		return text
	result: list[str] = []
	pos: int = 0
	# for anchorMatch in _ANCHOR_RE.finditer(text):
	# 	result.append(_linkifyOutsideTags(text[pos:anchorMatch.start()]))
	# 	result.append(anchorMatch.group(0))
	# 	pos = anchorMatch.end()
	result.append(_linkifyOutsideTags(text[pos:]))
	return ''.join(result)

def AreTooltipLinksClickable() -> bool:
	""" Returns whether the global setting to make tooltip links clickable is enabled. """
	try:
		app = QApplication.instance()
		return bool(app.GetSettingsManager().GetQAVMSettings().GetTooltipLinksClickable())
	except Exception:
		return False

def LinkifyTextIfEnabled(text: str) -> str:
	""" Linkifies URLs in the given rich text when the 'tooltip_links_clickable' global setting is on. """
	if not text or not AreTooltipLinksClickable():
		return text
	return LinkifyText(text)

def MarkdownTextToTooltipHtml(text: str) -> str:
	""" Converts user-entered markdown text into rich text for tooltips.

	Uses the markdown library to convert markdown to HTML, then linkifies any URLs in the resulting HTML
	when the global setting is on. """
	htmlText: str = markdown.markdown(text)
	return LinkifyTextIfEnabled(htmlText)

def PlainTextToTooltipHtml(text: str) -> str:
	return MarkdownTextToTooltipHtml(text)
	""" Converts user-entered plain text (notes, tag descriptions) into safe rich text for tooltips.

	The text is HTML-escaped (users never enter HTML via the note/tag editors), URLs are optionally made
	clickable when the global setting is on, and newlines are turned into <br> so multi-line text keeps its
	line breaks. """
	if not text:
		return text
	escaped: str = html.escape(text)
	linkified: str = LinkifyTextIfEnabled(escaped)
	return linkified.replace('\n', '<br>')

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
		
	styleExtraHeaderSortIndicator = """
		QHeaderView::down-arrow {
			image: none;
			width: 0px;
			height: 0px;
		}
		QHeaderView::up-arrow {
			image: none;
			width: 0px;
			height: 0px;
		}
	"""

	# Append custom style to override scrollbar thickness
	app.setStyleSheet(app.styleSheet() + styleExtraScrollBar + styleExtraLineEdit + styleExtraTreeview + styleExtraHeaderSortIndicator)

def GetThemesList() -> list[str]:
	return list_themes()

def GetThemeData() -> dict[str, str | None] | None:
	return get_theme(GetThemeName())