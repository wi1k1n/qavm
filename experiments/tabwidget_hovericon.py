import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QRect
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPalette
from PyQt6.QtWidgets import (
	QApplication,
	QLabel,
	QMainWindow,
	QStyle,
	QStyleOptionTab,
	QStylePainter,
	QTabBar,
	QTabWidget,
	QVBoxLayout,
	QWidget,
)

from qt_material import apply_stylesheet

def load_icon(path: str, fallback_text: str) -> QIcon:
	image_path = Path(path)

	if image_path.exists():
		return QIcon(str(image_path))

	pixmap = QPixmap(160, 88)
	pixmap.fill(QColor("#303030"))

	painter = QPainter(pixmap)
	painter.setRenderHint(QPainter.RenderHint.Antialiasing)
	painter.setPen(QColor("white"))

	font = QFont()
	font.setPointSize(18)
	font.setBold(True)
	painter.setFont(font)

	painter.drawText(
		pixmap.rect(),
		Qt.AlignmentFlag.AlignCenter,
		fallback_text,
	)

	painter.end()

	return QIcon(pixmap)

class CenteredIconTabBar(QTabBar):
	"""
	Tab bar optimized for icon-only tabs.

	- Always draws centered icons.
	- Does not track hover.
	- Does not swap between image/text.
	- Avoids QTabBar's built-in icon layout, which can be affected by stylesheets.
	"""

	def __init__(self, parent=None):
		super().__init__(parent)

		self._tab_icons: dict[int, QIcon] = {}

		self.setIconSize(QSize(80, 24))

	def set_tab_icon(self, index: int, icon: QIcon, tooltip: str = ""):
		self._tab_icons[index] = icon

		# Keep real tab text/icon empty because painting is custom.
		self.setTabText(index, "")
		self.setTabIcon(index, QIcon())

		if tooltip:
			self.setTabToolTip(index, tooltip)

		self.update()

	def paintEvent(self, event):
		painter = QStylePainter(self)

		for index in range(self.count()):
			option = QStyleOptionTab()
			self.initStyleOption(option, index)

			# Draw only the tab background/shape via the active style.
			shape_option = QStyleOptionTab(option)
			shape_option.text = ""
			shape_option.icon = QIcon()

			painter.drawControl(
				QStyle.ControlElement.CE_TabBarTabShape,
				shape_option,
			)

			content_rect = self.style().subElementRect(
				QStyle.SubElement.SE_TabBarTabText,
				option,
				self,
			)

			if not content_rect.isValid():
				content_rect = option.rect.adjusted(8, 4, -8, -4)

			self._draw_centered_icon(
				painter,
				content_rect,
				self._tab_icons.get(index, QIcon()),
			)

	def _draw_centered_icon(
		self,
		painter: QPainter,
		rect: QRect,
		icon: QIcon,
	):
		if icon.isNull():
			return

		icon_size = self.iconSize()

		max_width = min(icon_size.width(), rect.width())
		max_height = min(icon_size.height(), rect.height())

		pixmap = icon.pixmap(QSize(max_width, max_height))

		x = rect.x() + (rect.width() - pixmap.width()) // 2
		y = rect.y() + (rect.height() - pixmap.height()) // 2

		painter.drawPixmap(x, y, pixmap)

class IconDefaultHoverTextTabBar(QTabBar):
	def __init__(self, parent=None):
		super().__init__(parent)

		self.setMouseTracking(True)

		self._hovered_index = -1
		self._tab_titles: dict[int, str] = {}
		self._tab_icons: dict[int, QIcon] = {}

		self.setIconSize(QSize(80, 44))

	def set_tab_icon(self, index: int, icon: QIcon, title: str):
		self._tab_titles[index] = title
		self._tab_icons[index] = icon

		# Keep the real tab text empty, because we custom-paint everything.
		self.setTabText(index, "")

		self.update()

	def mouseMoveEvent(self, event):
		index = self.tabAt(event.pos())

		if index != self._hovered_index:
			self._hovered_index = index
			self.update()

		super().mouseMoveEvent(event)

	def leaveEvent(self, event):
		self._hovered_index = -1
		self.update()

		super().leaveEvent(event)

	def paintEvent(self, event):
		painter = QStylePainter(self)

		for index in range(self.count()):
			option = QStyleOptionTab()
			self.initStyleOption(option, index)

			# Draw the tab shape using the active Qt/qt_material style.
			shape_option = QStyleOptionTab(option)
			shape_option.text = ""
			shape_option.icon = QIcon()

			painter.drawControl(
				QStyle.ControlElement.CE_TabBarTabShape,
				shape_option,
			)

			content_rect = self.style().subElementRect(
				QStyle.SubElement.SE_TabBarTabText,
				option,
				self,
			)

			if not content_rect.isValid():
				content_rect = option.rect.adjusted(8, 4, -8, -4)

			if index == self._hovered_index:
				self._draw_centered_title(
					painter,
					content_rect,
					option,
					self._tab_titles.get(index, ""),
				)
			else:
				self._draw_centered_icon(
					painter,
					content_rect,
					self._tab_icons.get(index, QIcon()),
				)

	def _draw_centered_title(
		self,
		painter: QPainter,
		rect: QRect,
		option: QStyleOptionTab,
		title: str,
	):
		painter.save()

		painter.setPen(option.palette.color(QPalette.ColorRole.ButtonText))

		font = painter.font()
		font.setBold(True)
		painter.setFont(font)

		painter.drawText(
			rect,
			Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextSingleLine,
			title,
		)

		painter.restore()

	def _draw_centered_icon(
		self,
		painter: QPainter,
		rect: QRect,
		icon: QIcon,
	):
		if icon.isNull():
			return

		icon_size = self.iconSize()

		max_width = min(icon_size.width(), rect.width())
		max_height = min(icon_size.height(), rect.height())

		pixmap = icon.pixmap(QSize(max_width, max_height))

		x = rect.x() + (rect.width() - pixmap.width()) // 2
		y = rect.y() + (rect.height() - pixmap.height()) // 2

		painter.drawPixmap(x, y, pixmap)

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()

		self.setWindowTitle("Image tabs with hover titles")
		self.resize(500, 300)

		tabs = QTabWidget()

		tab_bar = CenteredIconTabBar()
		tabs.setTabBar(tab_bar)

		light_page = self._make_page("Light tab content")
		dark_page = self._make_page("Dark tab content")

		light_index = tabs.addTab(light_page, "")
		dark_index = tabs.addTab(dark_page, "")

		tab_bar.set_tab_icon(
			light_index,
			load_icon("qavm\\res\\yoda-1.png", "Yoda"),
			"Light",
		)

		tab_bar.set_tab_icon(
			dark_index,
			load_icon("qavm\\res\\dv-1.png", "Vader"),
			"Dark",
		)

		self.setCentralWidget(tabs)

	@staticmethod
	def _make_page(text: str) -> QWidget:
		page = QWidget()
		layout = QVBoxLayout(page)

		label = QLabel(text)
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)

		layout.addWidget(label)
		return page


def main():
	app = QApplication(sys.argv)

	apply_stylesheet(
		app,
		theme="dark_teal.xml",
		extra={
			"density_scale": "0",
		},
	)

	app.setStyleSheet(
		app.styleSheet()
		+ """
		QTabBar::tab {
			min-width: 80px;
			min-height: 24px;
			padding: 2px 4px;
		}
		"""
	)

	window = MainWindow()
	window.show()

	sys.exit(app.exec())


if __name__ == "__main__":
	main()