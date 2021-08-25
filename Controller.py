# coding = utf-8

import base64
import json
from VideoCapture import VideoCapture
import multiprocessing
from multiprocessing import Queue
import queue
import cv2
import grequests
import threading
import itertools
from collections import defaultdict
from Util import renderPose, renderBbox

class Controller:

    __RECOGNIZE_ACTION_URLS = [
                               'http://10.176.54.24:55000/recognizeAction',
                               # 'http://10.176.54.14:55000/recognizeAction',
                               'http://10.176.54.41:55000/recognizeAction',
                               'http://10.176.54.42:55000/recognizeAction',
                               ]

    __ACTION_LABEL = ['站', '坐', '走', '吃饭', '红绳操', '毛巾操', '未知动作']

    # __ACTION_LABEL = ['站', '坐', '走', '吃饭', '红绳操', '毛巾操', '跌倒', '未知动作']

    # __ACTION_LABEL = ['吃', '玩手机', '坐', '睡觉', '站', '红绳操', '毛巾操', '走', '跌倒', '未知动作']

    __QUEUE_GET_TIMEOUT = 0.1
    __RECOGNIZE_PER_FRAME = 5
    __WAITING_QUEUE_MAXSIZE = 100

    def __init__(self):
        self.waitingQueueDict = dict()
        self.responseQueue = Queue()
        self.__cameras = []
        self.__processes = []
        self.__frameCnt = 0
        self.showPose = True
        self.showBox = False
        # self.poseAndBoxByCamera = defaultdict(lambda: dict(pose=None, box=None, interval=0))

        self.sources = [
            f'/Users/benull/Downloads/action_video/{i}.MOV' for i in range(10)
        ]

            # 'rtsp://admin:izhaohu666@192.168.10.253/h264/ch1/main/av_stream',
            # 'rtsp://admin:izhaohu666@192.168.10.254/h264/ch1/main/av_stream',
            # 'rtsp://admin:UPXEBY@192.168.10.95/Streaming/Channels/101',


    def start(self):
        for source in self.sources:
            self.procVideo(source)

        self.startProcRecognize()

    def startProcRecognize(self):
        t = threading.Thread(target=self.procRecognizeQueue, args=(self.waitingQueueDict, self.responseQueue,))
        t.start()

    def procRecognizeQueue(self, waitingQueueDict, responseQueue):

        while True:
            imagesData, needRecognize = self.__gainFramePerVideo(waitingQueueDict)
            if not imagesData:
                continue
            if needRecognize:
                responseQueue.put(self.__requestRecognizeAction(imagesData))
            else:
                responseQueue.put(list(map(self.__procResponseData, filter(None, imagesData))))

    def __requestRecognizeAction(self, imagesData):

        imageListPerCamera = self.__buildImageListPerCamera(imagesData)
        params = [self.__buildRecognizeParam(imageList, self.showPose, self.showBox) for imageList in imageListPerCamera]
        try:
            responseData = self.recognizeAction(params)
            return list(map(self.__procResponseData, itertools.chain.from_iterable(imageListPerCamera), responseData))
        except Exception as e:
            return []

    def __buildImageListPerCamera(self, imagesData):
        serverNum = len(Controller.__RECOGNIZE_ACTION_URLS)
        return [list(filter(None, imagesData[i::serverNum])) for i in range(serverNum)]

    def __gainFramePerVideo(self, waitingQueueDict):
        imagesData = []
        needRecognize = self.__frameCnt % Controller.__RECOGNIZE_PER_FRAME == 0
        for camera in self.__cameras:
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

        self.__frameCnt += 1
        return imagesData, needRecognize

    def __procResponseData(self, origin, response=dict()):
        camera, frameNum, image = origin
        image = self.__showPoseAndBox(image, response)
        label = Controller.__ACTION_LABEL[response['personInfo'][0]['action']] if response.get('personInfo') else None
        return dict(camera=str(camera), frameNum=frameNum, image=image, label=label)

    # fix inconsistencies in pose refresh
    # def __showPoseAndBox(self, camera, image, response):
    #     if response.get('personInfo'):
    #         self.poseAndBoxByCamera[camera]['pose'] = response['personInfo'][0]['pose']
    #         self.poseAndBoxByCamera[camera]['box'] = response['personInfo'][0]['box']
    #         self.poseAndBoxByCamera[camera]['interval'] = 0
    #     else:
    #         self.poseAndBoxByCamera[camera]['interval'] += 1
    #
    #     if self.poseAndBoxByCamera[camera]['interval'] > Controller.__RECOGNIZE_PER_FRAME:
    #         self.poseAndBoxByCamera[camera]['pose'] = None
    #         self.poseAndBoxByCamera[camera]['box'] = None
    #
    #     if self.showPose and self.poseAndBoxByCamera[camera]['pose']:
    #         image = renderPose(image, self.poseAndBoxByCamera[camera]['pose'])
    #     if self.showBox and self.poseAndBoxByCamera[camera]['box']:
    #         image = renderBbox(image, self.poseAndBoxByCamera[camera]['box'])
    #     return image

    def __showPoseAndBox(self, image, response):
        if not response.get('personInfo'):
            return image
        pose = response['personInfo'][0]['pose']
        box = response['personInfo'][0]['box']
        if self.showPose and pose:
            image = renderPose(image, pose)
        if self.showBox and box:
            image = renderBbox(image, box)
        return image

    def __buildRecognizeParam(self, images, pose: bool = False, box: bool = False):
        if not images: return None
        images = list(map(
            lambda image: {'camera': str(image[0]), 'image': base64.b64encode(cv2.imencode('.jpg', image[2])[1]).decode()},
            images))
        option = dict(pose=pose, box=box)
        return dict(images=images, option=option)

    def procVideo(self, camera):
        self.__cameras.append(camera)
        videoCapture = VideoCapture(camera, self.__cameras.index(camera))

        self.waitingQueueDict[camera] = Queue(maxsize=Controller.__WAITING_QUEUE_MAXSIZE)
        p = multiprocessing.Process(target=videoCapture.captureFrame, args=(self.waitingQueueDict[camera],))
        self.__processes.append(p)
        p.start()

    def recognizeAction(self, params):
        requestList = self.__buildRequestList(params)
        responseList = grequests.map(requestList)
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
        return [grequests.post(url, data=json.dumps(param), timeout=(1, 3)) for url, param in
                zip(Controller.__RECOGNIZE_ACTION_URLS, params) if param]

    def recv(self):
        res = []
        try:
            res = self.responseQueue.get(timeout=Controller.__QUEUE_GET_TIMEOUT)
        except queue.Empty:
            pass
        finally:
            return dict(data=res)

    def terminalProcesses(self,):
        for process in self.__processes:
            process.terminate()


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
