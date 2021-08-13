# coding = utf-8

from typing import *
import base64
import json
from VideoCapture import VideoCapture
import multiprocessing
from multiprocessing import Queue
import queue
import cv2
import time
import grequests
import threading
import itertools
import traceback
import requests


class Controller:

    __RECOGNIZE_ACTION_URLS = ['http://10.176.54.24:55000/recognizeAction']

    # __RECOGNIZE_ACTION_URLS = ['http://10.176.54.24:55000/recognizeAction',
    #                            'http://10.176.54.23:35500/recognizeAction',
    #                            'http://10.176.54.22:21602/recognizeAction']

    __ACTION_LABEL = ['站', '坐', '走', '吃饭', '红绳操', '毛巾操', '未知动作']

    # __ACTION_LABEL = ['站', '坐', '走', '吃饭', '红绳操', '毛巾操', '跌倒', '未知动作']

    # __ACTION_LABEL = ['吃', '玩手机', '坐', '睡觉', '站', '红绳操', '毛巾操', '走', '跌倒', '未知动作']

    __QUEUE_GET_TIMEOUT = 0.1
    __RECOGNIZE_PER_FRAME = 5
    __WAITING_QUEUE_MAXSIZE = 100

    def __init__(self):
        self.waitingQueueDict = dict()
        self.responseQueue = Queue()
        self.cameras = []
        self.frameCnt = 0

        # self.times = 0
        # self.duration = 0

    def start(self):

        for i in range(1):
            self.procVideo(f'/Users/benull/Downloads/action_video/{i}.MOV')

        self.startProcRecognize()

    def startProcRecognize(self):
        t = threading.Thread(target=self.procRecognizeQueue, args=(self.waitingQueueDict, self.responseQueue,))
        t.start()
        # p = multiprocessing.Process(target=self.procRecognizeQueue, args=(self.waitingQueueDict, self.responseQueue,))
        # p.start()

    def procRecognizeQueue(self, waitingQueueDict, responseQueue):

        while True:
            imagesData, needRecognize = self.__gainFramePerVideo(waitingQueueDict)
            if not imagesData:
                continue

            if needRecognize:
                # pass
                responseQueue.put(self.__requestRecognizeAction(imagesData))
            else:
                responseQueue.put(list(map(self.__procResponseData, filter(None, imagesData))))

    def __requestRecognizeAction(self, imagesData):

        imageListPerCamera = self.__buildImageListPerCamera(imagesData)

        params = [self.__buildRecognizeParam(imageList, False, False) for imageList in imageListPerCamera]
        try:
            # start = time.time()
            responseData = self.recognizeAction(params)
            # self.duration += (time.time() - start)
            # self.times += 1
            # print(f'{self.times}次请求平均消耗时间{self.duration / self.times * 1000}ms')
            return list(map(self.__procResponseData, itertools.chain.from_iterable(imageListPerCamera), responseData))
        except Exception as e:
            # traceback.print_exc()
            return []

    def __buildImageListPerCamera(self, imagesData):
        serverNum = len(Controller.__RECOGNIZE_ACTION_URLS)
        return [list(filter(None, imagesData[i::serverNum])) for i in range(serverNum)]

    def __gainFramePerVideo(self, waitingQueueDict):
        imagesData = []
        needRecognize = self.frameCnt % Controller.__RECOGNIZE_PER_FRAME == 0
        for camera in self.cameras:
            if camera not in waitingQueueDict:
                imagesData.append(None)
                continue
            try:
                element = waitingQueueDict[camera].get(timeout=Controller.__QUEUE_GET_TIMEOUT)
                if element == 'DONE':
                    del waitingQueueDict[camera]
                    imagesData.append(None)
                else:
                    imagesData.append(element)
            except queue.Empty:
                imagesData.append(None)

        self.frameCnt += 1
        return imagesData, needRecognize

    def __procResponseData(self, origin, response=dict()):
        camera, frameNum, image = origin
        label = Controller.__ACTION_LABEL[response['personInfo'][0]['action']] if response.get('personInfo') else None
        return dict(camera=str(self.cameras.index(camera)), frameNum=frameNum, image=image, label=label)

    def __buildRecognizeParam(self, images, pose: bool = False, box: bool = False):
        if not images: return None
        images = list(map(
            lambda image: {'camera': image[0], 'image': base64.b64encode(cv2.imencode('.jpg', image[2])[1]).decode()},
            images))
        option = dict(pose=pose, box=box)
        return dict(images=images, option=option)

    def procVideo(self, camera):
        videoCapture = VideoCapture(camera)
        self.cameras.append(camera)
        self.waitingQueueDict[camera] = Queue(maxsize=Controller.__WAITING_QUEUE_MAXSIZE)
        p = multiprocessing.Process(target=videoCapture.captureFrame, args=(self.waitingQueueDict[camera],))
        p.start()

    def recognizeAction(self, params):
        # import os
        # print(f'{os.getpid()} recog ')
        # import time
        # print(f'{time.time()}  startRe')

        requestList = self.__buildRequestList(params)

        # responseList = []
        # for r in grequests.imap(requestList, size=100):
        #     responseList.append(r)
        # start = time.time()
        # print(f'request start at {start}')

        responseList = grequests.map(requestList)

        # end = time.time()
        # print(f'request end at {end}')
        # print(f'request cost {end-start}')

        # print(f'{time.time()}  endRe')

        return self.__processMultiResponse(responseList)

    def __processMultiResponse(self, responseList):
        mergedData = []

        for response in filter(None, responseList):
            if response.status_code == 200:
                res = response.json()
                if res.get('status') == 0:
                    mergedData.extend(res.get('data'))
                else:
                    raise Exception('Recognize Error: ' + res.get('message'))
            else:
                raise response.raise_for_status()
        return mergedData

    def __buildRequestList(self, params):
        return [grequests.post(url, data=json.dumps(param)) for url, param in
                zip(Controller.__RECOGNIZE_ACTION_URLS, params) if param]

    def recv(self):
        res = []
        try:
            res = self.responseQueue.get(timeout=Controller.__QUEUE_GET_TIMEOUT)  # block=False
        except queue.Empty:
            pass
        finally:
            return dict(data=res)


if __name__ == '__main__':
    controller = Controller()

    controller.procVideo('/Users/benull/Downloads/1.MOV')
    controller.procVideo('/Users/benull/Downloads/2.MOV')
    controller.procVideo('/Users/benull/Downloads/3.MOV')
    controller.procVideo('/Users/benull/Downloads/4.MOV')

    controller.startProcRecognize()

    import time


    def runTask(func, second):
        while True:
            func()
            time.sleep(second)


    def doRecv():
        print(controller.recv())


    runTask(doRecv, 0.5)
