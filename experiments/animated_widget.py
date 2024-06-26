import math

from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QPoint, QRect, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont, QPalette
from PyQt6.QtWidgets import QLabel, QSizePolicy, QMainWindow, QVBoxLayout, QApplication, QLayout, QWidget, QStyle, QScrollArea, QTabWidget, QFrame

class RunningBorderWidget(QFrame):
	def __init__(self, accentColor: QColor, tailColor: QColor, parent=None):
		super().__init__(parent)

		self._accentColor = accentColor
		self._tailColor = tailColor
		
		self.setStyleSheet(self._getBackgroundColorGradientStyle(0))

		self._backgroundGradientDirection = 0
		self.color_anim = QPropertyAnimation(self, b'bgGradientDirection')
		self.color_anim.setStartValue(360)
		self.color_anim.setEndValue(0)
		self.color_anim.setDuration(2000)
		self.color_anim.setLoopCount(-1)
		self.color_anim.start()

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
		return self._backgroundGradientDirection
	
	@bgGradientDirection.setter
	def bgGradientDirection(self, dir):
		self._backgroundGradientDirection = dir
		self.setStyleSheet(self._getBackgroundColorGradientStyle(dir))


class AnimatedWidget(QFrame):
	def __init__(self, parent=None, texts=[]):
		super().__init__(parent)
		# self.resize(600, 600)

												# "border: 10px solid qlineargradient(x1: 0, x2: 1, stop: 0 red, stop: 1 blue);"
		self.setStyleSheet(self._getBackgroundColorGradientStyle(0)
												# "border: 10px solid;"
												# "border-image-slice: 1;"
												# "border-width: 5px;"
												# "border-image-source: linear-gradient(to left, #743ad5, #d53a9d);"
		)
		# # use for a container widget
		# self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
		# self.setLineWidth(1)
		
		layout = QVBoxLayout(self)
		# for text in texts:
		# 	label = QLabel(text)
		# 	label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		# 	# label.setStyleSheet("color: darkblue; font-size: 16px; background-color: white;")
		# 	layout.addWidget(label)

		label = QLabel("TEXT")
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		label.setStyleSheet("color: darkblue; font-size: 16px; background-color: white;")
		layout.addWidget(label)
		
		self.setLayout(layout)



		# https://www.pythonguis.com/tutorials/qpropertyanimation/
		self._backgroundGradientDirection = 0
		self.color_anim = QPropertyAnimation(self, b'bgGradientDirection')
		self.color_anim.setStartValue(360)
		# self.color_anim.setKeyValueAt(0.5, color2)
		self.color_anim.setEndValue(0)
		self.color_anim.setDuration(2000)
		self.color_anim.setLoopCount(-1)
		self.color_anim.start()

	# https://stackoverflow.com/q/6979772
	# https://stackoverflow.com/a/64835600
	def _getBackgroundColorGradientStyle(self, direction):
		# ret = ("background-color: qradialgradient("
		# 														"cx: 0.5, cy: 0.5, radius: 2, fx: 0.5, fy: 1, "
		# 														"stop: 0    rgba(30,255,30,255), "
		# 														"stop: 0.1 rgba(30,255,30,144), "
		# 														"stop: 0.2  rgba(30,255,30,32));")
		ret = ("background-color: qconicalgradient("
																f"cx: 0.5, cy: 0.5, angle: {direction}, "
																"stop: 0.00 rgba(30,255,30,255), "
																"stop: 0.10 rgba(30,255,30,32), "
																"stop: 0.90 rgba(30,255,30,32), "
																"stop: 1.00 rgba(30,255,30,255));")
		return ret

	@pyqtProperty(int)
	def bgGradientDirection(self):
		return self._backgroundGradientDirection
	
	@bgGradientDirection.setter
	def bgGradientDirection(self, dir):
		self._backgroundGradientDirection = dir
		self.setStyleSheet(self._getBackgroundColorGradientStyle(dir))
	
	def _updateBackColor(self):
		palette = self.palette()
		palette.setColor(QPalette.ColorRole.Window, self._backColor)
		self.setPalette(palette)
		self.setAutoFillBackground(True)


class PulsingFrame(QFrame):
		def __init__(self, parent=None):
				super().__init__(parent)
				
				# Set up the layout and add QLabels
				self.layout = QVBoxLayout(self)
				self.labels = ["Label 1", "Label 2", "Label 3"]
				for text in self.labels:
						label = QLabel(text)
						label.setAlignment(Qt.AlignmentFlag.AlignCenter)
						label.setStyleSheet("color: darkblue; font-size: 16px;")
						self.layout.addWidget(label)
				
				# Set the initial style
				self._border_color = QColor(255, 0, 0)
				self.setStyleSheet(f"""
						QFrame {{
								background-color: pink;
								border: 2px solid {self._border_color.name()};
						}}
				""")
				
				# Initialize the animation
				self.animation = QPropertyAnimation(self, b"borderColor")
				self.animation.setDuration(1000)  # 1 second
				self.animation.setLoopCount(-1)  # Infinite loop
				self.animation.setStartValue(QColor(255, 0, 0))
				self.animation.setEndValue(QColor(255, 255, 255))
				self.animation.setEasingCurve(QEasingCurve.Type.InOutBack)
				
				# Start the animation
				self.animation.start()
				
		@pyqtProperty(QColor)
		def borderColor(self):
				return self._border_color

		@borderColor.setter
		def borderColor(self, color):
				self._border_color = color
				self.setStyleSheet(f"""
						QFrame {{
								background-color: pink;
								border: 2px solid {self._border_color.name()};
						}}
				""")