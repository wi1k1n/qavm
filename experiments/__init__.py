import sys
from enum import Enum

from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont
from PyQt6.QtWidgets import QLabel, QSizePolicy, QMainWindow, QVBoxLayout, QApplication, QLayout, QWidget, QStyle, QScrollArea, QTabWidget, QFrame, QHBoxLayout, QGridLayout

from flow_layout import FlowLayout
from bubble import BubbleWidget
from animated_widget import StaticBorderWidget, PulsingBorderWidget, RunningBorderWidget
from dnd_widget import DragDropWidget

from qt_material import apply_stylesheet

class C4DTileAnimationType(Enum):
	NONE = 0
	STATIC = 1
	RUNNING = 2
	PULSING = 3
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
		wrapWidget = QWidget(parent)
		wrapLayout = QGridLayout(wrapWidget)

		for idxType, type in enumerate([C4DTileAnimationType.NONE, C4DTileAnimationType.STATIC, C4DTileAnimationType.RUNNING, C4DTileAnimationType.PULSING]):
			for idxColor, color in enumerate([QColor('red'), QColor('orange'), QColor('green')]):
				wrapLayout.addWidget(self._createC4DTile(type, color, parent), idxType, idxColor)

		return wrapWidget
	
	def _createC4DTile(self, type: C4DTileAnimationType, accentColor: QColor, parent: QWidget):
		descWidget = self._createC4DDescWidget(self)
		if type == C4DTileAnimationType.NONE:
			return descWidget
		
		animatedBorderWidget = self._wrapWidgetInAnimatedBorder(descWidget, type, accentColor, self)
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
	
	def _wrapWidgetInAnimatedBorder(self, widget, type: C4DTileAnimationType, accentColor: QColor, parent):
		tailColor = QColor(accentColor)
		tailColor.setAlpha(30)

		if type == C4DTileAnimationType.STATIC:
			animBorderWidget = StaticBorderWidget(accentColor)
		elif type == C4DTileAnimationType.RUNNING:
			animBorderWidget = RunningBorderWidget(accentColor, tailColor, parent)
		elif type == C4DTileAnimationType.PULSING:
			animBorderWidget = PulsingBorderWidget(accentColor, tailColor, parent)
		else:
			raise ValueError("Invalid C4DTileAnimationType")

		borderThickness = 5
		animBorderLayout = animBorderWidget.layout()
		animBorderLayout.setContentsMargins(borderThickness, borderThickness, borderThickness, borderThickness)
		animBorderLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
		animBorderLayout.addWidget(widget)

		innerSize = widget.sizeHint()
		fullWidth = innerSize.width() + 2 * borderThickness
		fullHeight = innerSize.height() + 2 * borderThickness
		animBorderWidget.setFixedSize(QSize(fullWidth, fullHeight))

		return animBorderWidget


class ExperimentApp(QApplication):
	def __init__(self, argv):
		super(ExperimentApp, self).__init__(argv)

		self.mainWindow = MainWindow()
		self.mainWindow.show()

if __name__ == "__main__":
	app: ExperimentApp = ExperimentApp(sys.argv)
	apply_stylesheet(app, theme='light_purple.xml')
	# apply_stylesheet(app, theme='dark_purple.xml')
	sys.exit(app.exec())