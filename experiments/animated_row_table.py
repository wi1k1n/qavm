import sys
from PyQt6.QtWidgets import (
	QApplication, QTableWidget, QTableWidgetItem, QStyledItemDelegate, QScrollBar, QVBoxLayout,
	QWidget, QAbstractItemView
)
from PyQt6.QtCore import (
	Qt, QPropertyAnimation, pyqtProperty, QEasingCurve, QPointF
)
from PyQt6.QtGui import (
	QPainter, QLinearGradient, QGradient, QColor
)

class FullRowGradientDelegate(QStyledItemDelegate):
	def __init__(self, parent=None, target_row=1):
		super().__init__(parent)
		self._pos = 0.0
		self.target_row = target_row

		# Animate pos 0→1→0 over 4s, looping forever
		self.anim = QPropertyAnimation(self, b"pos", self)
		self.anim.setDuration(4000)
		self.anim.setKeyValueAt(0.0, 0.0)
		self.anim.setKeyValueAt(0.5, 1.0)
		self.anim.setKeyValueAt(1.0, 0.0)
		self.anim.setLoopCount(-1)
		self.anim.setEasingCurve(QEasingCurve.Type.Linear)
		self.anim.start()

	def paint(self, painter: QPainter, option, index):
		# only custom-paint our target row
		if index.row() != self.target_row:
			super().paint(painter, option, index)
			return

		table: QTableWidget = self.parent()  # QTableWidget

		stripeWPercent = 0.1
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

		colorEnd1 = QColor(255, 20, 20)
		colorMid = QColor(100, 255, 100)
		colorEnd2 = QColor(0, 100, 0)
		grad.setColorAt(0.0, colorEnd1)
		grad.setColorAt(0.0 + stripeWPercent / 2, colorMid)
		grad.setColorAt(0.5 - stripeWPercent / 2, colorMid)
		grad.setColorAt(0.5, colorEnd2)
		grad.setColorAt(0.5 + stripeWPercent / 2, colorMid)
		grad.setColorAt(1.0 - stripeWPercent / 2, colorMid)
		grad.setColorAt(1.0, colorEnd1)

		painter.save()
		painter.fillRect(option.rect, grad)
		painter.setPen(option.palette.color(option.palette.ColorRole.Text))
		painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter, index.data())
		painter.restore()

	def getPos(self) -> float:
		return self._pos

	def setPos(self, v: float):
		self._pos = v
		# repaint exactly the span of the whole row
		first = self.parent().model().index(self.target_row, 0)
		last  = self.parent().model().index(self.target_row, self.parent().columnCount() - 1)
		row_rect = (self.parent().visualRect(first).united(self.parent().visualRect(last)))
		self.parent().viewport().update(row_rect)

	pos = pyqtProperty(float, getPos, setPos)

def main():
	app = QApplication(sys.argv)

	layout: QVBoxLayout = QVBoxLayout()
	layout.setContentsMargins(50, 80, 120, 150)

	mainWidget = QWidget()
	mainWidget.setLayout(layout)

	table = QTableWidget(3, 3)
	table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
	table.setWindowTitle("PyQt6: Full-Row Gradient + Scrolling")
	for r in range(3):
		for c in range(3):
			it = QTableWidgetItem(f"R{r+1}C{c+1}")
			it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
			table.setItem(r, c, it)

	# make columns wide so you can scroll
	for c in range(3):
		table.setColumnWidth(c, 200)

	# install our scroll-aware gradient delegate on row 1
	delegate = FullRowGradientDelegate(table, target_row=1)
	table.setItemDelegateForRow(1, delegate)

	table.resize(400, 200)

	layout.addWidget(table)
	
	mainWidget.show()
	sys.exit(app.exec())

if __name__ == "__main__":
	main()
