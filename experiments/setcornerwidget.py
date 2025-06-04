from PyQt6.QtWidgets import QMainWindow, QMenuBar, QMenu, QApplication
from PyQt6.QtGui import QAction
import sys

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		
		self.setWindowTitle("Corner Widget MenuBar Example")
		
		menuFile = QMenu("File", self)
		menuFile.addAction(QAction("New", self, triggered=lambda: print("New action triggered")))
		menuFile.addAction(QAction("Open", self, triggered=lambda: print("Open action triggered")))
		menuFile.addAction(QAction("Exit", self, triggered=self.close))

		menuEdit = QMenu("Edit", self)
		menuEdit.addAction(QAction("Undo", self, triggered=lambda: print("Undo action triggered")))
		menuEdit.addAction(QAction("Redo", self, triggered=lambda: print("Redo action triggered")))

		self.menuBar().addMenu(menuFile)
		self.menuBar().addMenu(menuEdit)

		menuTest = QMenu("Test", self)
		menuTest.addAction(QAction("Test action 1", self, triggered=lambda: print("Test action 1 triggered")))

		actionExample = QAction("Example", self, triggered=lambda: print("Example action triggered"))

		menubarRight = QMenuBar(self.menuBar())
		menubarRight.addMenu(menuTest)
		menubarRight.addAction(actionExample)
		self.menuBar().setCornerWidget(menubarRight)


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = MainWindow()
	window.resize(400, 300)
	window.show()
	sys.exit(app.exec())
