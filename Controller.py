# coding = utf-8

import requests
from typing import *
import base64
import json
from VideoCapture import VideoCapture
import multiprocessing
from multiprocessing import Queue
import queue
import cv2
import traceback
import threading
import time


class Controller:

    __RECOGNIZE_ACTION_URL = 'http://10.176.54.14:55000/recognizeAction'
    __ACTION_LABEL = ['站', '坐', '走', '吃', '红绳操', '毛巾操', '未知动作']

    __QUEUE_GET_TIMEOUT = 2
    __RECOGNIZE_PER_FRAME = 5


    def __init__(self):
        self.waitingQueueDict = dict()
        self.responseQueue = Queue()
        self.__cameras = []
        self.frameCnt = 0

        # self.times = 0
        # self.duration = 0

    def start(self):
        self.startProcRecognize()
        for i in range(1):
            self.procVideo(f'/Users/benull/Downloads/{i}.MOV')


    def startProcRecognize(self):
        t = threading.Thread(target=self.procRecognizeQueue, name='procRecognizeThread',
                             args=(self.waitingQueueDict, self.responseQueue,))
        t.start()

    def __requestRecognizeAction(self, imagesData):
        param = self.__buildRecognizeParam(imagesData, False, False)
        try:
            # start = time.time()

            responseData = self.recognizeAction(param)

            # self.duration += (time.time() - start)
            # self.times += 1
            # print(f'{self.times}次请求平均消耗时间{self.duration/self.times*1000}ms')
            return list(map(self.__procResponseData, imagesData, responseData))
        except Exception as e:
            # traceback.print_exc()
            return []

    def procRecognizeQueue(self, waitingQueueDict, responseQueue):
        while True:
            imagesData, needRecognize = self.__gainFramePerVideo(waitingQueueDict)
            if not imagesData:
                continue
            if needRecognize:
                # pass
                responseQueue.put(self.__requestRecognizeAction(imagesData))
            else:
                responseQueue.put(list(map(self.__procResponseData, imagesData)))

    def __gainFramePerVideo(self, waitingQueueDict):
        imagesData = []
        needRecognize = self.frameCnt % Controller.__RECOGNIZE_PER_FRAME == 0
        for camera in list(waitingQueueDict.keys()):
            try:
                element = waitingQueueDict[camera].get(timeout=Controller.__QUEUE_GET_TIMEOUT)
                if element == 'DONE':
                    del waitingQueueDict[camera]
                else:
                    imagesData.append(element)
            except queue.Empty:
                pass
        self.frameCnt += 1
        return imagesData, needRecognize


    def __procResponseData(self, origin, response=dict()):
        camera, frameNum, image = origin
        label = Controller.__ACTION_LABEL[response['personInfo'][0]['action']] if response.get('personInfo') else None
        return dict(camera=str(self.__cameras.index(camera)), frameNum=frameNum, image=image, label=label)

    def __buildRecognizeParam(self, images, pose: bool = False, box: bool = False):
        images = list(map(
            lambda image: {'camera': image[0], 'image': base64.b64encode(cv2.imencode('.jpg', image[2])[1]).decode()},
            images))
        option = dict(pose=pose, box=box)
        return dict(images=images, option=option)

    def procVideo(self, camera: str):
        videoCapture = VideoCapture(camera)
        self.__cameras.append(camera)
        self.waitingQueueDict[camera] = Queue(maxsize=15)
        p = multiprocessing.Process(target=videoCapture.captureFrame, args=(self.waitingQueueDict[camera],))
        p.start()

    def recognizeAction(self, param: dict):
        response = requests.post(Controller.__RECOGNIZE_ACTION_URL, data=json.dumps(param))
        if response.status_code == 200:
            res = response.json()
            if res.get('status') == 0:
                return res.get('data')
            else:
                raise Exception('Recognize Error: ' + res.get('message'))
        else:
            raise response.raise_for_status()

    def recv(self):
        res = []
        try:
            res = self.responseQueue.get(timeout=Controller.__QUEUE_GET_TIMEOUT)
        except queue.Empty:
            pass
        finally:
            return dict(data=res)

if __name__ == '__main__':
    controller = Controller()

    controller.startProcRecognize()
    controller.procVideo('/Users/benull/Downloads/1.MOV')

    import time


    def runTask(func, second):
        while True:
            func()
            time.sleep(second)


    def doRecv():
        print(controller.recv())


    runTask(doRecv, 0.5)
