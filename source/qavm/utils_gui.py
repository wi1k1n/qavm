from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QPropertyAnimation
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont
from PyQt6.QtWidgets import QLabel, QLayout, QWidget, QWidgetItem


# Copied from experiments on 26th of June 2024
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
	
	def insertWidget(self, index: int, widget: QWidget):
		self.addWidget(widget)
		last = self._items.pop()
		self._items.insert(index, last)
		self.update()

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

# Copied from experiments on 26th of June 2024
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

# Copied from experiments (fadein_tooltip) and adapted for production use
class FadeTooltip(QLabel):
	""" A tooltip-like label that fades in/out. Supports rich text (HTML). """
	def __init__(self, parent: QWidget | None = None):
		super().__init__(parent, Qt.WindowType.ToolTip)
		self.setWindowFlags(Qt.WindowType.ToolTip)
		self.setStyleSheet("background-color: #2b2b2b; color: #f0f0f0; border: 1px solid #555; padding: 6px; border-radius: 4px;")
		self.setFont(QFont("Arial", 10))
		self.setTextFormat(Qt.TextFormat.RichText)
		self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

		self.animation = QPropertyAnimation(self, b"windowOpacity")
		self.animation.setDuration(300)
		self.animation.finished.connect(self._onAnimationFinished)
		self._fadingOut: bool = False

	def showText(self, text: str, pos: QPoint):
		self._fadingOut = False
		self.setText(text)
		self.adjustSize()
		self.move(pos)
		self.setWindowOpacity(0.0)
		self.show()

		self.animation.stop()
		self.animation.setStartValue(self.windowOpacity())
		self.animation.setEndValue(1.0)
		self.animation.start()

	def hideWithFade(self):
		if not self.isVisible():
			return
		self._fadingOut = True
		self.animation.stop()
		self.animation.setStartValue(self.windowOpacity())
		self.animation.setEndValue(0.0)
		self.animation.start()

	def _onAnimationFinished(self):
		if self._fadingOut:
			self.hide()
			self._fadingOut = False