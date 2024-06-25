from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtWidgets import QLayout

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