#  MonitoringPanel

使用opencv-python或ffmpeg方式实时读取10路网络摄像头rtsp视频流，请求后端行为识别模型，返回行为识别结果包括骨架、包围盒进行展示，该项目为前端展示部分

![在这里插入图片描述](https://img-blog.csdnimg.cn/947ee3bc2123432997be31df2aa73989.png?x-oss-process=image/watermark,type_ZHJvaWRzYW5zZmFsbGJhY2s,shadow_50,text_Q1NETiBAQkVOVUxM,size_20,color_FFFFFF,t_70,g_se,x_16#pic_center)


## 依赖

```python
pyqt5
opencv-python
ffmpeg-python
```

## 文件结构

```java
├── App.py       	 主入口
├── Controller.py  后端交互文件
├── UiWindow.py  	 界面文件
├── Util.py        骨架绘制文件
└── VideoCapture.py 视频获取文件
```

## 视频流获取

提供opencv-python和ffmpeg-python两种方式获取视频流，其中ffmpeg-python以tcp方式读取rtsp流更稳定

使用多进程，一个进程负责读取视频流放入队列，一个进程负责从队列取帧进行处理并请求后端服务
```python
    def procVideo(self, camera):
        self.__cameras.append(camera)
        videoCapture = VideoCapture(camera, self.__cameras.index(camera))
        self.waitingQueueDict[camera] = Queue(maxsize=Controller.__WAITING_QUEUE_MAXSIZE)
        p = multiprocessing.Process(target=videoCapture.captureFrameByFfmpeg, args=(self.waitingQueueDict[camera],))
        self.__processes.append(p)
        p.start()
   
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
```

## 请求后端

轮询向各路视频流队列取帧，对图像base64编码，组合成请求列表，使用grequest请求多服务器进行识别
```python
    def recognizeAction(self, params):
        requestList = self.__buildRequestList(params)
        responseList = grequests.map(requestList)
        return self.__processMultiResponse(requestList, responseList)

    def __buildRecognizeParam(self, images, pose: bool = False, box: bool = False):
        if not images: return None
        images = list(map(
            lambda image: {'camera': str(image[0]), 'image': base64.b64encode(cv2.imencode('.jpg', image[2])[1]).decode()},
            images))
        option = dict(pose=pose, box=box)
        return dict(images=images, option=option)

    def __processMultiResponse(self, requestList, responseList):
        mergedData = []
        for request, response in zip(requestList, responseList):
            if response is None:
                imagesNum = len(json.loads(request.kwargs['data'])['images'])
                mergedData.extend([dict() for _ in range(imagesNum)])
                continue
            if response.status_code == 200:
                res = response.json()
                if res.get('status') == 0 or res.get('status') == 3:
                    mergedData.extend(res.get('data'))
                else:
                    raise Exception('Recognize Error: ' + res.get('message'))
            else:
                raise response.raise_for_status()
        return mergedData

    def __buildRequestList(self, params):
        return [grequests.post(url, data=json.dumps(param), timeout=(1, 3)) for url, param in
                zip(Controller.__RECOGNIZE_ACTION_URLS, params) if param]
```

## 显示界面

使用QGridLayout布局每个Grid放置QWidget，对每个QWidget中的QLabel通过设置一个定时器，定时刷新达到视频的效果
```python
    def refresh(self, imageInfos):
        for imageInfo in imageInfos:
            self.__refreshScreen(imageInfo)

    def __refreshScreen(self, info: dict):
        screen = self.myWindow.screenByCamera[info["camera"]]
        screen.setActionLabel(info.get('label'))
        screen.setImage(info['image'])

    def __startRefresh(self):
        self.refreshTimer = QTimer()
        self.refreshTimer.timeout.connect(self.process)
        self.refreshTimer.start(App.__REFRESH_INTERVAL)
```
## 骨架和包围盒绘制

骨架采用OpenPose 18个关节点进行绘制

```python
def renderPose(image, poses, inplace: bool = True, inverseNormalization='auto'):
    """绘制骨架

    参数
        image: 原图

        poses: 一组或多组关节点坐标

        config: 配置项

        inplace: 是否绘制在原图上

        inverseNormalization` 是否[True|False]进行逆归一化, 当值为auto时将根据坐标值自动确定

    返回
        输出图像, inplace为True时返回image, 为False时返回新的图像
    """
    poses = np.array(poses)
    if not inplace:
        image = image.copy()

    if len(poses.shape) == 2:
        poses = poses[None, :, :2]

    if inverseNormalization not in ['auto', True, False]:
        raise ValueError(f'Unknown "inverseNormalization" value {inverseNormalization}')

    _isPointValid = lambda point: point[0] != 0 and point[1] != 0
    _FILL_CIRCLE = -1
    for pose in poses:
        pose = preparePoint(pose, (image.shape[1], image.shape[0]), inverseNormalization)
        validPointIndices = set(filter(lambda i: _isPointValid(pose[i]), range(pose.shape[0])))
        for i, (start, end) in enumerate(RENDER_CONFIG_OPENPOSE['edges']):
            if start in validPointIndices and end in validPointIndices:
                cv2.line(image, tuple(pose[start]), tuple(pose[end]), RENDER_CONFIG_OPENPOSE['edgeColors'][i],
                         RENDER_CONFIG_OPENPOSE['edgeWidth'])

        for i in validPointIndices:
            cv2.circle(image, tuple(pose[i]), RENDER_CONFIG_OPENPOSE['pointRadius'],
                       tuple(RENDER_CONFIG_OPENPOSE['pointColors'][i]), _FILL_CIRCLE)

    return image


def renderBbox(image, box, inplace: bool = True, inverseNormalization='auto'):
    if not inplace:
        image = image.copy()

    if inverseNormalization not in ['auto', True, False]:
        raise ValueError(f'Unknown "inverseNormalization" value {inverseNormalization}')
    if len(box) == 4:
        box = np.array(box).reshape(2, 2)
        box = preparePoint(box, (image.shape[1], image.shape[0]), inverseNormalization)
        cv2.rectangle(image, tuple(box[0]), tuple(box[0]+box[1]), (255, 0, 0), thickness=1)
    return image
```


