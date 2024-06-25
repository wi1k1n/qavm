import sys

from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont
from PyQt6.QtWidgets import QLabel, QSizePolicy, QMainWindow, QVBoxLayout, QApplication, QLayout, QWidget, QStyle, QScrollArea, QTabWidget, QFrame

from flow_layout import FlowLayout
from bubble import BubbleWidget
from animated_widget import AnimatedWidget, PulsingFrame

class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		
		self.setWindowTitle("Experiments - Flow Layout")
		self.resize(800, 600)
		self.setMinimumSize(350, 250)
		
		centralWidget: QTabWidget = QTabWidget()

		flWidget = self._createFlowLayoutWithBubbles(self)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget, self)

		centralWidget.addTab(PulsingFrame(), "Pulsing Frame")
		centralWidget.addTab(self._createC4DTile(), "C4D Tile")
		centralWidget.addTab(scrollWidget, "Flow Layout (with bubbles)")
		
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
		return AnimatedWidget(self)

class ExperimentApp(QApplication):
	def __init__(self, argv):
		super(ExperimentApp, self).__init__(argv)

		self.mainWindow = MainWindow()
		self.mainWindow.show()

if __name__ == "__main__":
	app: ExperimentApp = ExperimentApp(sys.argv)
	sys.exit(app.exec())