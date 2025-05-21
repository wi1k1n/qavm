import datetime as dt

from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, pyqtProperty
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout, QLabel, QTableWidgetItem
from PyQt6.QtGui import QColor

from qt_material import apply_stylesheet, get_theme, list_themes

class DateTimeTableWidgetItem(QTableWidgetItem):
	def __init__(self, date: dt.datetime, format: str):
		self.date: dt.datetime = date
		self.format: str = format
		super().__init__(self.date.strftime(self.format))

	def __lt__(self, other):
		if isinstance(other, DateTimeTableWidgetItem):
			return self.date < other.date
		return super().__lt__(other)

# Copied from experiments on 26th of June 2024
class StaticBorderWidget(QFrame):
	def __init__(self, color: QColor, parent=None):
		super().__init__(parent)

		self._color = color
		self.setStyleSheet(self._getBackgroundColorStyle())
		self.setLayout(QVBoxLayout(self))

	def _getBackgroundColorStyle(self):
		cssColorString = f"rgba({self._color.red()}, {self._color.green()}, {self._color.blue()}, {self._color.alpha()})"
		return (f"background-color: {cssColorString}")

# Copied from experiments on 19th of May 2025
class RunningBorderWidget(QFrame):
	def __init__(self, accentColor: QColor, tailColor: QColor, parent=None):
		super().__init__(parent)

		self._accentColor = accentColor
		self._tailColor = tailColor
		
		self.setStyleSheet(self._getBackgroundColorGradientStyle(0))

		self._bgGradientDirection = 0
		self.bgGradientAnim = QPropertyAnimation(self, b'bgGradientDirection')
		self.bgGradientAnim.setStartValue(360)
		self.bgGradientAnim.setEndValue(0)
		self.bgGradientAnim.setDuration(2000)
		self.bgGradientAnim.setLoopCount(-1)
		self.bgGradientAnim.start()

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
		return self._bgGradientDirection
	
	@bgGradientDirection.setter
	def bgGradientDirection(self, dir):
		self._bgGradientDirection = dir
		self.setStyleSheet(self._getBackgroundColorGradientStyle(dir))

class ClickableLabel(QLabel):
	# TODO: change this to get modifier keys from the event instead
	clickedLeft = pyqtSignal(bool, bool, bool)  # ctrl, alt, shift
	clickedRight = pyqtSignal(bool, bool, bool)  # ctrl, alt, shift
	clickedMiddle = pyqtSignal(bool, bool, bool)  # ctrl, alt, shift
	
	clickedAny = pyqtSignal(bool, bool, bool)  # ctrl, alt, shift

	def __init__(self, parent=None):
		super().__init__(parent)

	def mousePressEvent(self, evt):
		# get modifier keys
		ctrl = bool(evt.modifiers() & Qt.KeyboardModifier.ControlModifier)
		alt = bool(evt.modifiers() & Qt.KeyboardModifier.AltModifier)
		shift = bool(evt.modifiers() & Qt.KeyboardModifier.ShiftModifier)
		
		self.clickedAny.emit(ctrl, alt, shift)
		if evt.button() == Qt.MouseButton.LeftButton:
			self.clickedLeft.emit(ctrl, alt, shift)
		elif evt.button() == Qt.MouseButton.RightButton:
			self.clickedRight.emit(ctrl, alt, shift)
		elif evt.button() == Qt.MouseButton.MiddleButton:
			self.clickedMiddle.emit(ctrl, alt, shift)
		super().mousePressEvent(evt)


CURRENT_THEME = 'light_purple.xml'
def GetThemeName() -> str:
	return CURRENT_THEME

def SetTheme(theme: str) -> None:
	app: QApplication = QApplication.instance()
	
	apply_stylesheet(app, theme=GetThemeName(), extra={'density_scale': '-1'})
	
	# Append custom style to override scrollbar thickness
	# TODO: use secondColor as a background color for the scrollbar
	app.setStyleSheet(app.styleSheet() + """
		QScrollBar:vertical {
			width: 14px;
			margin: 0px;
		}

		QScrollBar:horizontal {
			height: 14px;
			margin: 0px;
		}

		QScrollBar::handle:vertical {
			min-height: 20px;
			background-color: #888;
			border-radius: 7px;
		}

		QScrollBar::handle:horizontal {
			min-width: 20px;
			background-color: #888;
			border-radius: 7px;
		}

		QScrollBar::add-line,
		QScrollBar::sub-line {
			background: none;
			border: none;
		}

		QScrollBar::add-page,
		QScrollBar::sub-page {
			background: none;
		}
	""")

def GetThemesList() -> list[str]:
	return list_themes()

def GetThemeData() -> dict[str, str | None] | None:
	return get_theme(GetThemeName())