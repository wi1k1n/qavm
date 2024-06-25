import sys

from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont
from PyQt6.QtWidgets import QLabel, QSizePolicy, QMainWindow, QVBoxLayout, QApplication, QLayout, QWidget, QStyle, QScrollArea, QTabWidget

# Bubble implementation is taken from https://stackoverflow.com/a/18069897 and modified
class BubbleWidget(QLabel):
	def __init__(self, text, bgColor: QColor | None = None, rounding: float = 20, margin: int = 7):
		super().__init__(text)
		self.rounding: float = rounding
		self.roundingMargin: int = margin
		self.bgColor: QColor | None = bgColor
		self.setContentsMargins(margin, margin, margin, margin)

	def paintEvent(self, evt: QPaintEvent):
		p: QPainter = QPainter(self)
		penWidth: int = 1 # 2 if self.underMouse() else 1
		p.setPen(QPen(QColor('black'), penWidth))
		if self.bgColor is not None:
			p.setBrush(self.bgColor)
		p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
		p.drawRoundedRect(penWidth, penWidth, self.width() - penWidth * 2, self.height() - penWidth * 2, self.rounding, self.rounding)
		super().paintEvent(evt)









# FlowLayout implementation is taken from https://stackoverflow.com/a/41643802/5765191 and modified
class FlowLayout(QLayout):
	def __init__(self, parent=None, margin=0, hspacing=0, vspacing=0):
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
		return self._hspacing

	def verticalSpacing(self):
		return self._vspacing

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
		return self.doLayout(QRect(0, 0, width, 0), testonly=True)

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
			hspace = self.horizontalSpacing()
			vspace = self.verticalSpacing()
			nextX = x + item.sizeHint().width() + hspace
			if nextX - hspace > effective.right() and lineheight > 0:
				x = effective.x()
				y = y + lineheight + vspace
				nextX = x + item.sizeHint().width() + hspace
				lineheight = 0
			if not testonly:
				item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
			x = nextX
			lineheight = max(lineheight, item.sizeHint().height())
		return y + lineheight - rect.y() + bottom
		








class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		
		self.setWindowTitle("Experiments - Flow Layout")
		self.resize(800, 600)
		self.setMinimumSize(350, 250)
		
		centralWidget: QTabWidget = QTabWidget()

		flWidget = self._createFlowLayoutWithBubbles(self)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget, self)

		centralWidget.addTab(scrollWidget, "Flow Layout (with bubbles)")
		centralWidget.addTab(self._createC4DTile(), "C4D Tile")
		
		self.setCentralWidget(centralWidget)
		
		# self.setCentralWidget(flowLayoutWidget)
	
	def _createFlowLayoutWithBubbles(self, parent):
		TEXT = "I've heard there was a secred chord that David played and it pleased the Lord but you don't really care for music, do you?"
		
		flWidget = QWidget(parent)
		flWidget.setMinimumWidth(50)

		flowLayout = FlowLayout(flWidget, margin=1, hspacing=0, vspacing=0)
		flowLayout.setSpacing(0)

		self._words = []
		for word in TEXT.split():
			bubble = BubbleWidget(word, QColor('lightblue'))
			bubble.setFont(QFont('SblHebrew', 30))
			bubble.setFixedWidth(bubble.sizeHint().width())
			self._words.append(bubble)
			flowLayout.addWidget(bubble)

		return flWidget
	
	def _wrapWidgetInScrollArea(self, widget, parent):
		scrollWidget = QScrollArea(parent)
		scrollWidget.setWidgetResizable(True)
		scrollWidget.setWidget(widget)
		return scrollWidget
	
	def _createC4DTile(self):
		return QWidget(self)

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