import datetime as dt

from PyQt6.QtCore import Qt, pyqtSignal
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


class ClickableLabel(QLabel):
	clicked = pyqtSignal()

	def __init__(self, parent=None):
		super().__init__(parent)

	def mousePressEvent(self, evt):
		if evt.button() == Qt.MouseButton.LeftButton:
			self.clicked.emit()
		super().mousePressEvent(evt)

CURRENT_THEME = 'light_purple.xml'
def GetThemeName() -> str:
	return CURRENT_THEME

def SetTheme(theme: str) -> None:
	apply_stylesheet(QApplication.instance(), theme=GetThemeName(), extra={'density_scale': '-1'})

def GetThemesList() -> list[str]:
	return list_themes()

def GetThemeData() -> dict[str, str | None] | None:
	return get_theme(GetThemeName())