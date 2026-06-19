import math
import random

from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QPropertyAnimation, pyqtSignal
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
	""" A tooltip-like label that fades in/out. Supports rich text (HTML).

	When interactive=True the tooltip stops being transparent to the mouse: its text becomes selectable,
	embedded links become clickable, and it emits mouseEntered/mouseLeft so an owner can keep it alive
	while the cursor is over it (persistent tooltip behaviour). """
	mouseEntered = pyqtSignal()
	mouseLeft = pyqtSignal()

	FADEIN_DURATION_MS: int = 150
	FADEOUT_DURATION_MS: int = 150

	def __init__(self, parent: QWidget | None = None, interactive: bool = False):
		super().__init__(parent, Qt.WindowType.ToolTip)
		self.setWindowFlags(Qt.WindowType.ToolTip)
		self._interactive: bool = interactive

		from qavm.qavmapi.gui import GetThemeData
		themeData = GetThemeData()
		colorPrimary = QColor(themeData.get('primaryColor', '#ffffff')) if themeData else QColor('#ffffff')
		colorSecondary = QColor(themeData.get('secondaryColor', '#0f0f0f')) if themeData else QColor('#0f0f0f')

		self.setStyleSheet(f"background-color: {colorSecondary.name()}; color: {colorPrimary.name()}; border: 1px solid {colorPrimary.name()}; padding: 6px; border-radius: 4px;")
		self.setFont(QFont("Arial", 10))
		self.setTextFormat(Qt.TextFormat.RichText)
		if interactive:
			# Let the user select/copy the text and click embedded links.
			self.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
			self.setOpenExternalLinks(True)
		else:
			self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

		self.animation = QPropertyAnimation(self, b"windowOpacity")
		self.animation.setDuration(self.FADEIN_DURATION_MS)
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
		self.animation.setDuration(self.FADEOUT_DURATION_MS)
		self.animation.start()

	def enterEvent(self, event):
		if self._interactive:
			self.mouseEntered.emit()
		super().enterEvent(event)

	def leaveEvent(self, event):
		if self._interactive:
			self.mouseLeft.emit()
		super().leaveEvent(event)

	def _onAnimationFinished(self):
		if self._fadingOut:
			self.hide()
			self._fadingOut = False


class DistinguishableColorGenerator:
	""" Generates perceptually distinguishable colors using the OKLab / OKLCh color space.

	Reusable helper: build a fixed palette of pleasant candidate colors once, then ask for the
	candidate that is the most perceptually distinct from a set of already-used colors. """

	_LIGHTNESS_VALUES: tuple[float, ...] = (0.66, 0.72, 0.78, 0.84)
	_CHROMA_VALUES: tuple[float, ...] = (0.10, 0.13, 0.16)
	_HUE_STEP_DEGREES: int = 4

	def __init__(self) -> None:
		self._candidates: list[tuple[int, int, int]] = self._GenerateCandidateColors()
		self._candidateOklab: dict[tuple[int, int, int], tuple[float, float, float]] = {
			rgb: self._RGBToOklab(rgb) for rgb in self._candidates
		}

	def GenerateColor(self, existingColors: list[QColor] | None = None) -> QColor:
		""" Returns the candidate color that is most perceptually distinguishable from all existingColors.
		If no existing colors are given, a random candidate is returned. """
		existingRGB: list[tuple[int, int, int]] = [
			(c.red(), c.green(), c.blue()) for c in (existingColors or []) if c is not None and c.isValid()
		]
		if not existingRGB:
			return QColor(*random.choice(self._candidates))

		existingOklab: list[tuple[float, float, float]] = [self._RGBToOklab(rgb) for rgb in existingRGB]
		bestRGB: tuple[int, int, int] = max(
			self._candidates,
			key=lambda rgb: min(
				self._OklabDistance(self._candidateOklab[rgb], existing)
				for existing in existingOklab
			),
		)
		return QColor(*bestRGB)

	def GenerateColors(self, count: int, existingColors: list[QColor] | None = None) -> list[QColor]:
		""" Returns count colors, each maximally distinguishable from the existing ones and from each other. """
		if count <= 0:
			return []
		accumulated: list[QColor] = list(existingColors or [])
		result: list[QColor] = []
		for _ in range(count):
			color: QColor = self.GenerateColor(accumulated)
			result.append(color)
			accumulated.append(color)
		return result

	# region Color math (sRGB <-> linear <-> OKLab / OKLCh)
	@classmethod
	def _GenerateCandidateColors(cls) -> list[tuple[int, int, int]]:
		candidates: list[tuple[int, int, int]] = []
		for lightness in cls._LIGHTNESS_VALUES:
			for chroma in cls._CHROMA_VALUES:
				for hue in range(0, 360, cls._HUE_STEP_DEGREES):
					rgb = cls._OklchToRGB(lightness, chroma, hue)
					if rgb is not None:
						candidates.append(rgb)
		return candidates

	@staticmethod
	def _SRGBToLinear(c: int) -> float:
		v = c / 255.0
		return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

	@staticmethod
	def _LinearToSRGB(c: float) -> int:
		if c <= 0.0031308:
			c = 12.92 * c
		else:
			c = 1.055 * (c ** (1.0 / 2.4)) - 0.055
		return round(max(0.0, min(1.0, c)) * 255)

	@classmethod
	def _RGBToOklab(cls, rgb: tuple[int, int, int]) -> tuple[float, float, float]:
		r, g, b = (cls._SRGBToLinear(c) for c in rgb)

		l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
		m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
		s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

		l_, m_, s_ = math.cbrt(l), math.cbrt(m), math.cbrt(s)

		return (
			0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
			1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
			0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
		)

	@classmethod
	def _OklchToRGB(cls, lightness: float, chroma: float, hueDegrees: float) -> tuple[int, int, int] | None:
		hue = math.radians(hueDegrees)
		a = chroma * math.cos(hue)
		b = chroma * math.sin(hue)

		l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
		m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
		s_ = lightness - 0.0894841775 * a - 1.2914855480 * b

		l, m, s = l_ ** 3, m_ ** 3, s_ ** 3

		r = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
		g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
		b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

		if not all(0.0 <= channel <= 1.0 for channel in (r, g, b)):
			return None

		return cls._LinearToSRGB(r), cls._LinearToSRGB(g), cls._LinearToSRGB(b)

	@staticmethod
	def _OklabDistance(c1: tuple[float, float, float], c2: tuple[float, float, float]) -> float:
		return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))
	# endregion