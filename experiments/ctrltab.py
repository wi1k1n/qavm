from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenu, 
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QEvent, QPoint

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ctrl+Tab Menu Cycling")

        # Setup View menu and actions
        self.viewMenu = QMenu("View", self)
        self.menuBar().addMenu(self.viewMenu)
        self.viewActions = []

        for i in range(5):
            action = QAction(f"View {i+1}", self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, i=i: print(f"Activated View {i+1}"))
            self.viewMenu.addAction(action)
            self.viewActions.append(action)

        # State tracking
        self.currentIndex = -1
        self.ctrlHeld = False

        # Global event filter
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Control:
                self.ctrlHeld = True
                return False  # allow normal processing
            elif event.key() == Qt.Key.Key_Tab and self.ctrlHeld:
                self.cycleMenu()
                return True

        elif event.type() == QEvent.Type.KeyRelease:
            if event.key() == Qt.Key.Key_Control and self.ctrlHeld:
                self.ctrlHeld = False
                self.triggerSelectedAction()
                return True

        return super().eventFilter(obj, event)

    def cycleMenu(self):
        if not self.viewMenu.isVisible():
            bar = self.menuBar()
            menu_action = self.viewMenu.menuAction()
            rect = bar.actionGeometry(menu_action)
            global_pos = bar.mapToGlobal(rect.bottomLeft())
            self.viewMenu.popup(global_pos)

        self.currentIndex = (self.currentIndex + 1) % len(self.viewActions)

        for i, action in enumerate(self.viewActions):
            action.setChecked(i == self.currentIndex)

    def triggerSelectedAction(self):
        if 0 <= self.currentIndex < len(self.viewActions):
            self.viewActions[self.currentIndex].trigger()
        self.cleanup()

    def cleanup(self):
        self.currentIndex = -1
        self.viewMenu.hide()
        for action in self.viewActions:
            action.setChecked(False)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.resize(400, 300)
    window.show()
    app.exec()
