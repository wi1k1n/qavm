from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtProperty, QPoint, QRect, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen, QFont, QPalette
from PyQt6.QtWidgets import QLabel, QSizePolicy, QMainWindow, QVBoxLayout, QApplication, QLayout, QWidget, QStyle, QScrollArea, QTabWidget, QFrame

class AnimatedWidget(QFrame):
	def __init__(self, parent=None):
		super().__init__(parent)
		self.resize(600, 600)

		# self.setStyleSheet("background-color: rgb(255,0,0); margin:5px; border:1px solid rgb(0, 255, 0); ")
		# # use for a container widget
		# self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
		# self.setLineWidth(1)

		# https://www.pythonguis.com/tutorials/qpropertyanimation/
		color1 = QColor(255, 0, 0)
		color2 = QColor(0, 255, 0)

		self._backColor = color1

		self.color_anim = QPropertyAnimation(self, b'backColor')
		self.color_anim.setStartValue(color1)
		self.color_anim.setKeyValueAt(0.5, color2)
		self.color_anim.setEndValue(color1)
		self.color_anim.setDuration(1000)
		self.color_anim.setLoopCount(-1)
		self.color_anim.start()

	@pyqtProperty(QColor)
	def backColor(self):
		return self._backColor
	
	@backColor.setter
	def backColor(self, color):
		self._backColor = color
		self._updateBackColor()
	
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