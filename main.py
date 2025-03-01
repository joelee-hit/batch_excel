from PyQt5.QtWidgets import QApplication
from qt import MainApp
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainApp()
    mainWin.show()
    sys.exit(app.exec_())