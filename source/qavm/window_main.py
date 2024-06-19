from PyQt6.QtWidgets import QMainWindow, QWidget

class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super(MainWindow, self).__init__(parent)

        self.setWindowTitle("QAVM")
        self.resize(800, 600)

        self.setCentralWidget(QWidget())

        # self.createMenuBar()
        # self.createToolBar()
        # self.createStatusBar()

        self.update()