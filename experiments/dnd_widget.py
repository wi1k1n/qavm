# ChatGPT generated code
import sys
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

class DraggableLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedSize(100, 50)
        self.setStyleSheet("background-color: lightblue; border: 1px solid black;")

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.mapToParent(event.pos() - self.drag_start_position))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.mapToParent(event.pos() - self.drag_start_position))

class DragDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Drag & Drop QLabel with Span Navigation")
        self.setGeometry(100, 100, 600, 400)

        # Store the initial position for panning
        self.pan_start_position = None

        # Adding a few labels to demonstrate
        self.labels = []
        for i in range(5):
            label = DraggableLabel(f"Label {i+1}", self)
            label.move(50 + i * 120, 50)
            self.labels.append(label)
            label.show()

        self.setStyleSheet("background-color: white;")
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pan_start_position = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self.pan_start_position is not None:
            # Calculate the delta
            delta = event.pos() - self.pan_start_position
            self.pan_start_position = event.pos()
            # Move all labels
            for label in self.labels:
                label.move(label.pos() + delta)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pan_start_position = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    demo = DragDropWidget()
    demo.show()
    sys.exit(app.exec())