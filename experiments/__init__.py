import sys

from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont
from PyQt6.QtWidgets import QLabel, QSizePolicy, QMainWindow, QVBoxLayout, QApplication, QLayout, QWidget, QStyle, QScrollArea, QTabWidget, QFrame

from flow_layout import FlowLayout
from bubble import BubbleWidget
from animated_widget import AnimatedWidget, RunningBorderWidget
from dnd_widget import DragDropWidget

class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		
		self.setWindowTitle("Experiments")
		self.resize(800, 600)
		self.setMinimumSize(350, 250)
		
		tabsWidget: QTabWidget = QTabWidget()

		tilesWidget = self._createC4DTiles(self)
		tabsWidget.addTab(tilesWidget, "C4D Tile")
		
		flWidget = self._createFlowLayoutWithBubbles(self)
		scrollWidget = self._wrapWidgetInScrollArea(flWidget, self)
		tabsWidget.addTab(scrollWidget, "Flow Layout (with bubbles)")
		
		tabsWidget.addTab(DragDropWidget(), "Drag-n-drop area")
		
		self.setCentralWidget(tabsWidget)
	
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
	
	def _createC4DTiles(self, parent: QWidget):
		c4dTileWidget = self._createC4DTile(parent)
		return c4dTileWidget
	
	def _createC4DTile(self, parent: QWidget):
		descWidget = self._createC4DDescWidget(self)
		animatedBorderWidget = self._wrapWidgetInAnimatedBorder(descWidget, self)
		return animatedBorderWidget

	def _createC4DDescWidget(self, parent: QWidget):
		descWidget = QWidget(parent)

		parentBGColor = parent.palette().color(parent.backgroundRole())
		descWidget.setStyleSheet(f"background-color: {parentBGColor.name()};")
		# DEBUG # descWidget.setStyleSheet("background-color: rgb(200, 200, 255);")
		
		descLayout = QVBoxLayout(descWidget)
		descLayout.setContentsMargins(0, 0, 0, 0)
		descLayout.setSpacing(0)

		for word in ['R2024.9', 'adsf153fa2g1', '26-Jun-2024']:
			label = QLabel(word)
			label.setFont(QFont('SblHebrew', 18))
			label.setAlignment(Qt.AlignmentFlag.AlignCenter)
			# DEBUG # label.setStyleSheet("background-color: pink;")
			descLayout.addWidget(label)

		descWidget.setFixedSize(descWidget.minimumSizeHint())

		return descWidget
	
	def _wrapWidgetInAnimatedBorder(self, widget, parent):
		accentColor = QColor(50, 255, 50, 255)
		tailColor = QColor(50, 255, 50, 30)
		animBorderWidget = RunningBorderWidget(accentColor, tailColor, parent)
		animBorderLayout = animBorderWidget.layout()
		borderThickness = 5
		animBorderLayout.setContentsMargins(borderThickness, borderThickness, borderThickness, borderThickness)
		animBorderLayout.addWidget(widget)
		animBorderWidget.setFixedSize(animBorderWidget.minimumSizeHint())
		return animBorderWidget

	# def _createC4DTile(self):
		
	# 	w = QWidget(self)
	# 	lo = QVBoxLayout(w)

	# 	for idx in range(1, 2):
	# 		pulsingBCWidget = AnimatedWidget(self, [f"AnimatedWidget#{idx}", "R22", "R23", "R24", "R25"])
	# 		lo.addWidget(pulsingBCWidget)

	# 	return w

class ExperimentApp(QApplication):
	def __init__(self, argv):
		super(ExperimentApp, self).__init__(argv)

		self.mainWindow = MainWindow()
		self.mainWindow.show()

if __name__ == "__main__":
	app: ExperimentApp = ExperimentApp(sys.argv)
	sys.exit(app.exec())