from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QLabel

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