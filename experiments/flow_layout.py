import sys

from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont
from PyQt6.QtWidgets import QLabel, QSizePolicy, QMainWindow, QVBoxLayout, QApplication, QLayout, QWidget, QStyle, QScrollArea

# https://stackoverflow.com/a/18069897
class BubbleWidget(QLabel):
	def __init__(self, text, bgColor: QColor | None = None, rounding: float = 20, margin: int = 7):
		super(QLabel, self).__init__(text)
		self.rounding: float = rounding
		self.roundingMargin: int = margin
		self.bgColor: QColor | None = bgColor

		# self.mouseLeaveTimer: QTimer = QTimer(self, interval=50, timeout=self._mouseLeaveTimerCallback)

		# self.setContentsMargins(margin, margin, margin, margin)
		# self.setAlignment(Qt.AlignCenter)
		# self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
		
		# TODO: not a lot of sense without masking ondrag-pixmap in DraggableQLabel
		# path = QPainterPath()
		# path.addRoundedRect(QRectF(self.rect()), rounding, rounding)
		# self.maskRegion = QRegion(path.toFillPolygon().toPolygon())
		# self.setMask(self.maskRegion)
		
		# self.setMouseTracking(True)
	
	# def _mouseLeaveTimerCallback(self):
	# 	self.mouseLeaveTimer.stop()
	# 	self.update()

	# def mouseMoveEvent(self, e: QMouseEvent):
	# 	self.mouseLeaveTimer.start()
	# 	self.update()
	# 	return super().mouseMoveEvent(e)

	# def SetColor(self, bgColor: QColor | None):
	# 	self.bgColor = bgColor
	# 	self.update()
	
	# def SetText(self, txt: str):
	# 	self.setText(txt)
	# 	self.setFixedSize(1, 1) # doesn't work without manually shrinking it first
	# 	self.setFixedSize(self.sizeHint() + QSize(self.roundingMargin, self.roundingMargin) * 2)

	def paintEvent(self, evt: QPaintEvent):
		# painter: QPainter = QPainter(self)


		
		# penWidth: int = 2 # 2 if self.underMouse() else 1
		# p.setPen(QPen(QColor('black'), penWidth))
		# # if self.bgColor is not None:
		# # 	p.setBrush(self.bgColor)
		
		# p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		# p.drawRoundedRect(penWidth, penWidth, self.width() - penWidth * 2, self.height() - penWidth * 2, self.rounding, self.rounding)
		
		super(QLabel, self).paintEvent(evt)









# FlowLayout implementation is stolen from: https://stackoverflow.com/a/41643802/5765191
class FlowLayout(QLayout):
	def __init__(self, parent=None, margin=-1, hspacing=-1, vspacing=-1):
		super(FlowLayout, self).__init__(parent)
		self._hspacing = hspacing
		self._vspacing = vspacing
		self._items = []
		self.setContentsMargins(margin, margin, margin, margin)

	def __del__(self):
		del self._items[:]

	def addItem(self, item):
		self._items.append(item)

	def horizontalSpacing(self):
		if self._hspacing >= 0:
			return self._hspacing
		else:
			return self.smartSpacing(
				QStyle.PixelMetric.PM_LayoutHorizontalSpacing)

	def verticalSpacing(self):
		if self._vspacing >= 0:
			return self._vspacing
		else:
			return self.smartSpacing(
				QStyle.PixelMetric.PM_LayoutVerticalSpacing)

	def count(self):
		return len(self._items)

	def itemAt(self, index):
		if 0 <= index < len(self._items):
			return self._items[index]

	def takeAt(self, index):
		if 0 <= index < len(self._items):
			return self._items.pop(index)

	def expandingDirections(self):
		return Qt.Orientations(0)

	def hasHeightForWidth(self):
		return True

	def heightForWidth(self, width):
		return self.doLayout(QRect(0, 0, width, 0), True)

	def setGeometry(self, rect):
		super(FlowLayout, self).setGeometry(rect)
		self.doLayout(rect, False)

	def sizeHint(self):
		return self.minimumSize()

	def minimumSize(self):
		size = QSize()
		for item in self._items:
			size = size.expandedTo(item.minimumSize())
		left, top, right, bottom = self.getContentsMargins()
		size += QSize(left + right, top + bottom)
		return size

	def doLayout(self, rect, testonly):
		left, top, right, bottom = self.getContentsMargins()
		effective = rect.adjusted(+left, +top, -right, -bottom)
		x = effective.x()
		y = effective.y()
		lineheight = 0
		for item in self._items:
			widget = item.widget()
			hspace = self.horizontalSpacing()
			if hspace == -1:
				hspace = widget.style().layoutSpacing(
					QSizePolicy.PushButton,
					QSizePolicy.PushButton, Qt.Horizontal)
			vspace = self.verticalSpacing()
			if vspace == -1:
				vspace = widget.style().layoutSpacing(
					QSizePolicy.PushButton,
					QSizePolicy.PushButton, Qt.Vertical)
			nextX = x + item.sizeHint().width() + hspace
			if nextX - hspace > effective.right() and lineheight > 0:
				x = effective.x()
				y = y + lineheight + vspace
				nextX = x + item.sizeHint().width() + hspace
				lineheight = 0
			if not testonly:
				item.setGeometry(
					QRect(QPoint(x, y), item.sizeHint()))
			x = nextX
			lineheight = max(lineheight, item.sizeHint().height())
		return y + lineheight - rect.y() + bottom

	def smartSpacing(self, pm):
		parent = self.parent()
		if parent is None:
			return -1
		elif parent.isWidgetType():
			return parent.style().pixelMetric(pm, None, parent)
		else:
			return parent.spacing()
		








class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		
		TEXT = "I've heard there was a secred chord that David played and it pleased the Lord but you don't really care for music, do you?"
		self.setWindowTitle("Experiments - Flow Layout")
		self.resize(1420, 840)
		self.setMinimumSize(350, 250)
		
		self.mainArea = QScrollArea(self)
		self.mainArea.setWidgetResizable(True)
		widget = QWidget(self.mainArea)
		widget.setMinimumWidth(50)
		layout = FlowLayout(widget)
		self.words = []
		for word in TEXT.split():
			label = BubbleWidget(word, QColor('lightblue'))
			# label = QLabel(word)
			# label.setFont(QFont('SblHebrew', 30))
			label.setFixedWidth(label.sizeHint().width())
			self.words.append(label)
			layout.addWidget(label)
		self.mainArea.setWidget(widget)
		self.setCentralWidget(self.mainArea)

class ExperimentApp(QApplication):
	def __init__(self, argv):
		super(ExperimentApp, self).__init__(argv)

		self.mainWindow = MainWindow()
		self.mainWindow.show()

if __name__ == "__main__":
	try:
		app: ExperimentApp = ExperimentApp(sys.argv)
		sys.exit(app.exec())
	except Exception as e:
		print("ExperimentsApp crashed")