import sys
from PyQt6.QtWidgets import (
    QApplication, QTableWidget, QTableWidgetItem, QStyledItemDelegate
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, pyqtProperty, QEasingCurve, QPointF
)
from PyQt6.QtGui import (
    QPainter, QLinearGradient, QGradient, QColor
)

from qt_material import apply_stylesheet, get_theme, list_themes

class GradientDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, row=1):
        super().__init__(parent)
        self._pos = 0.0
        self.row = row

        # Animate `pos` 0→1→0 over 4s, looping forever
        self.animation = QPropertyAnimation(self, b"pos", self)
        self.animation.setDuration(4000)
        self.animation.setKeyValueAt(0.0, 0.0)
        self.animation.setKeyValueAt(0.5, 1.0)
        self.animation.setKeyValueAt(1.0, 0.0)
        self.animation.setLoopCount(-1)
        self.animation.setEasingCurve(QEasingCurve.Type.Linear)
        self.animation.start()

    def paint(self, painter, option, index):
        if index.row() != self.row:
            super().paint(painter, option, index)
            return

        painter.save()
        rect = option.rect

        grad = QLinearGradient()
        # use object‐bounding coordinates
        grad.setCoordinateMode(QGradient.CoordinateMode.ObjectBoundingMode)
        # slide the gradient window from x = pos to pos+0.2
        grad.setStart(QPointF(self._pos, 0))
        grad.setFinalStop(QPointF(self._pos + 1.0, 0))
        grad.setSpread(QGradient.Spread.ReflectSpread)
        grad.setColorAt(0.0, QColor(0, 127, 0))
        # grad.setColorAt(0.5, QColor(0, 255, 0))
        grad.setColorAt(1.0, QColor(255, 255, 255))

        painter.fillRect(rect, grad)
        painter.setPen(option.palette.color(option.palette.ColorRole.Text))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, index.data())
        painter.restore()

    def getPos(self):
        return self._pos

    def setPos(self, value):
        self._pos = value
        # trigger repaint
        self.parent().viewport().update()

    pos = pyqtProperty(float, getPos, setPos)

def main():
    app = QApplication(sys.argv)
    apply_stylesheet(QApplication.instance(), theme='dark_purple.xml', extra={'density_scale': '-1'})

    table = QTableWidget(3, 3)
    table.setWindowTitle("PyQt6: Animated Gradient on Row 2")

    # fill with R#C# text
    for i in range(3):
        for j in range(3):
            item = QTableWidgetItem(f"R{i+1}C{j+1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, j, item)

    # apply our gradient delegate to the 2nd row (index 1)
    delegate = GradientDelegate(table, row=1)
    table.setItemDelegateForRow(1, delegate)

    table.resize(400, 200)
    table.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
