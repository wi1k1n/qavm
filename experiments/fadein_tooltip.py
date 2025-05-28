from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEvent
from PyQt6.QtGui import QFont, QEnterEvent
import sys


class FadeTooltip(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip)
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setStyleSheet("background-color: yellow; border: 1px solid black; padding: 5px;")
        self.setFont(QFont("Arial", 10))
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)

    def showText(self, text, pos):
        self.setText(text)
        self.adjustSize()
        self.move(pos)
        self.setWindowOpacity(0.0)
        self.show()

        self.animation.stop()
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.start()

    def hideWithFade(self):
        self.animation.stop()
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.start()
        self.animation.finished.connect(self.hide)


class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel("Hover and stay 3s", self)
        self.label.move(50, 50)
        self.label.setStyleSheet("border: 1px solid black; padding: 10px;")
        self.label.setMouseTracking(True)
        self.setMouseTracking(True)

        self.tooltip = FadeTooltip(self)
        self.hoverTimer = QTimer(self)
        self.hoverTimer.setSingleShot(True)
        self.hoverTimer.timeout.connect(self._showTooltip)

        self.lastMousePos = None

        self.label.installEventFilter(self)

    def _showTooltip(self):
        if not self.underMouse():
            return
        pos = self.label.mapToGlobal(QPoint(0, self.label.height()))
        self.tooltip.showText("This tooltip appears after 0.5s of stillness", pos)

    def eventFilter(self, source, event):
        HOVER_TOOLTIP_TIMEOUT = 500  # milliseconds
        if source is self.label:
            if event.type() == QEvent.Type.Enter:
                self.lastMousePos = self.cursor().pos()
                self.hoverTimer.start(HOVER_TOOLTIP_TIMEOUT)
            elif event.type() == QEvent.Type.Leave:
                self.hoverTimer.stop()
                self.tooltip.hide()
            elif event.type() == QEvent.Type.MouseMove:
                currentPos = self.cursor().pos()
                if currentPos != self.lastMousePos:
                    self.lastMousePos = currentPos
                    self.hoverTimer.start(HOVER_TOOLTIP_TIMEOUT)  # Restart countdown
        return super().eventFilter(source, event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MyWidget()
    win.resize(400, 200)
    win.show()
    sys.exit(app.exec())
