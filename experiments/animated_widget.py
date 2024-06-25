from PyQt6.QtCore import QPropertyAnimation, pyqtProperty, QPoint
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont, QPalette
from PyQt6.QtWidgets import QLabel, QSizePolicy, QMainWindow, QVBoxLayout, QApplication, QLayout, QWidget, QStyle, QScrollArea, QTabWidget

class AnimatedWidget(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.resize(600, 600)

		# # https://stackoverflow.com/a/31792766
		# self.child = QWidget(self)
		# self.child.setStyleSheet("background-color:red;border-radius:15px;")
		# self.child.resize(100, 100)

		# self.anim = QPropertyAnimation(self.child, b"pos")
		# self.anim.setEndValue(QPoint(400, 400))
		# self.anim.setDuration(1500)
		# self.anim.start()

		# https://www.pythonguis.com/tutorials/qpropertyanimation/
		color1 = QColor(255, 0, 0)
		color2 = QColor(0, 255, 0)

		self.color_anim = QPropertyAnimation(self, b'backColor')
		self.color_anim.setStartValue(color1)
		self.color_anim.setKeyValueAt(0.5, color2)
		self.color_anim.setEndValue(color1)
		self.color_anim.setDuration(1000)
		self.color_anim.setLoopCount(-1)
		self.color_anim.start()

	@pyqtProperty(int)
	def backColor(self):
		return self.palette().color(QPalette.Background)
	
	@backColor.setter
	def backColor(self, color):
		pal = self.palette()
		pal.setColor(QPalette.Background, color)
		self.setPalette(pal)
