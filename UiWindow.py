from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5 import QtCore, QtGui, QtWidgets


class MyQLabel(QtWidgets.QLabel):
    button_clicked_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(MyQLabel, self).__init__(parent)

    def mouseReleaseEvent(self, QMouseEvent):
        self.button_clicked_signal.emit()

    def connect_customized_slot(self, func):
        self.button_clicked_signal.connect(func)


class MyWidget(QWidget):
    def __init__(self, parent=None):
        super(MyWidget, self).__init__(parent)

        self.actionLabel = QTextEdit(self)
        self.actionLabel.setObjectName("cameraOneAction")
        self.actionLabel.setStyleSheet("background:transparent")
        self.actionLabel.setFrameStyle(QFrame.NoFrame)
        self.actionLabel.setReadOnly(True)
        self.actionLabel.resize(200, 80)

        self.imageLabel = QLabel(self)
        # self.imageLabel.setMaximumSize(475, 267)
        self.imageLabel.setMinimumSize(475, 267)
        # self.imageLabel.setMaximumSize(475, 267)
        # self.imageLabel.setScaledContents(True)
        self.actionLabel.raise_()
        self.lastLabel = '未接收到动作'

    def imageStyleSheet(self, style):
        self.imageLabel.setStyleSheet(style)
        return self

    def setActionLabel(self, label: str):
        self.lastLabel = label or self.lastLabel
        self.actionLabel.setPlainText(self.lastLabel)
        self.actionLabel.setFontPointSize(25)
        self.actionLabel.setTextColor(QColor(240, 65, 85))

    def setImage(self, image: QPixmap):
        self.imageLabel.setPixmap(image)
        self.imageLabel.repaint()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        self.imageLabel.resize(self.size())


class MyWindow(QWidget):

    def __init__(self, parent=None):
        super(MyWindow, self).__init__(parent)
        self.setupUi()

    def setupUi(self):
        gridLayout = QGridLayout()
        self.buttonLabel = MyQLabel(self)
        # self.buttonLabel.setStyleSheet("background:#3c4046")
        self.buttonLabel.setStyleSheet("background-color:black")
        self.buttonLabel.setText("点击这里开始展示")
        self.buttonLabel.setStyleSheet("color:white")
        self.buttonLabel.setAlignment(Qt.AlignCenter)

        self.labelNoSignal = QLabel()
        self.labelNoSignal.setText("No Signal")
        self.labelNoSignal.setAlignment(Qt.AlignCenter)
        self.labelNoSignal.setStyleSheet("background:black")
        self.labelNoSignal.setStyleSheet("color:white")

        cameraID = ['0', '1', '2', '3',
                    '4', '5', '6', '7',
                    '8', '9', '空', '空']

        self.screenByCamera = {}

        positions = [(i, j) for i in range(0, 3) for j in range(0, 4)]
        for position, cameraID in zip(positions, cameraID):
            if cameraID == '空':
                continue
            else:
                self.widget = MyWidget(self).imageStyleSheet("background:#3c4046")
                self.screenByCamera[cameraID] = self.widget
                gridLayout.addWidget(self.widget, *position)

        gridLayout.addWidget(self.buttonLabel, 2, 2)
        gridLayout.addWidget(self.labelNoSignal, 2, 3)

        gridLayout.setSpacing(2)
        gridLayout.setContentsMargins(2, 2, 2, 2)  # 设置外边距--控件到窗口边框的距离 左上右下
        self.setLayout(gridLayout)


class MyMainWindow(QMainWindow):

    def __init__(self,):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(0, 0, 1920, 820)
        self.setStyleSheet("background:black")
        self.myWindow = MyWindow()
        self.setCentralWidget(self.myWindow)
        self.setWindowTitle("10路视频演示")
        menubar = self.menuBar()
        viewMenu = menubar.addMenu('显示')
        self.showPoseAct = QAction('显示骨架', self,)
        self.showBboxAct = QAction('显示包围盒', self,)
        self.showBboxAct.setCheckable(True)
        self.showPoseAct.setCheckable(True)
        self.showPoseAct.setChecked(True)
        viewMenu.addAction(self.showPoseAct)
        viewMenu.addAction(self.showBboxAct)




