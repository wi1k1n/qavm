import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenu
from PyQt6.QtGui import QAction


class ClickableSubmenuMenu(QMenu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.click_handlers = {}

    def set_click_handler(self, action: QAction, handler):
        self.click_handlers[action] = handler

    def mouseReleaseEvent(self, event):
        action = self.actionAt(event.position().toPoint())

        if action in self.click_handlers:
            self.click_handlers[action]()
            self.close()
            return

        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        main_menu = ClickableSubmenuMenu("Main", self)
        self.menuBar().addMenu(main_menu)

        submenu_a1 = QMenu("A1", self)

        action_a2 = submenu_a1.addAction("A2")
        action_a3 = submenu_a1.addAction("A3")

        action_a2.triggered.connect(self.on_a2)
        action_a3.triggered.connect(self.on_a3)

        a1_action = main_menu.addMenu(submenu_a1)

        # Click directly on "A1"
        main_menu.set_click_handler(a1_action, self.on_a1)

    def on_a1(self):
        print("A1 clicked")

    def on_a2(self):
        print("A2 clicked")

    def on_a3(self):
        print("A3 clicked")


app = QApplication(sys.argv)
window = MainWindow()
window.resize(400, 300)
window.show()
sys.exit(app.exec())