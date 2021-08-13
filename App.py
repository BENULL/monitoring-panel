# coding = utf-8
import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWidgets import *
from Controller import Controller
from UiWindow import MyWindow
import time
import queue
from PIL import Image
import multiprocessing


class App(MyWindow):

    __CACHE_QUEUE_LENGTH = 50
    __CACHE_INTERVAL = 20
    __REFRESH_INTERVAL = 40

    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        self.setupUi()
        self.controller = Controller()
        self.establishConnections()

    def establishConnections(self):
        self.buttonLabel.connect_customized_slot(self.start)

    def refresh(self, imageInfos):
        for imageInfo in imageInfos:
            self.__refreshScreen(imageInfo)

    def __refreshScreen(self, info: dict):
        # import os
        # print(f'{os.getpid()} refresh ')
        # import time
        # print(f'{time.time()}  refresh')

        screen = self.screenByCamera[info["camera"]]
        screen.setActionLabel(info.get('label'))
        screen.setImage(info['image'])
        screen.repaint()

    def __startRefresh(self):
        self.refreshTimer = QTimer()
        self.refreshTimer.timeout.connect(self.process)
        self.refreshTimer.start(App.__REFRESH_INTERVAL)

    def __startCache(self):
        self.cacheTimer = QTimer()
        self.cacheTimer.timeout.connect(self.writeToCacheQueue)
        self.cacheQueue = queue.Queue()
        self.isFirst = True
        self.cacheTimer.start(App.__CACHE_INTERVAL)

    def start(self):
        self.controller.start()
        self.__startCache()
        self.__startRefresh()

    def receiveData(self):
        infodict = self.controller.recv()['data']
        # print("接收到的数据为：",infodict)
        for _infodict in infodict:
            image = self.ndarrayToQPixmap(_infodict["image"])
            _infodict.update({'image': image})

        return infodict

    def process(self):
        if self.cacheQueue.qsize() >= App.__CACHE_QUEUE_LENGTH and self.isFirst:
            self.send()
            self.isFirst = False
        elif not self.isFirst:
            self.send()

    def send(self):
        try:
            data = self.cacheQueue.get(block=False)
        except queue.Empty:
            data = []
        self.refresh(data)

    def writeToCacheQueue(self):
        data = self.receiveData()
        if data:
            self.cacheQueue.put(data)
            print('队列长度：', self.cacheQueue.qsize())

    def ndarrayToQPixmap(self, image):
        return Image.fromarray(image).toqpixmap()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    application = App()
    application.show()
    sys.exit(app.exec_())
