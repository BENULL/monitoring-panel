# coding = utf-8
import cv2
import os
from multiprocessing import Queue
cv2.setNumThreads(0)


class VideoCapture:

    def __init__(self, camera, channel):
        self.camera = camera
        self.channel = channel

    def captureFrame(self, queue: Queue):
        print(f'{self.camera}开始处理')
        cap = cv2.VideoCapture(self.camera)
        retry = 0
        frameNum = 1
        ret, frame = cap.read()
        while ret or retry <= 3:
            if ret:
                frame = cv2.resize(frame, (480, 360))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                queue.put((self.channel, frameNum, frame))
                frameNum += 1
                ret, frame = cap.read()
            else:
                cap = cv2.VideoCapture(self.camera)
                print(f'{self.camera}流重新建立')
                ret, frame = cap.read()
                retry = retry+1 if not ret else 0
        cap.release()
        queue.put('DONE')
        print(f'{self.camera}进程{os.getpid()}处理完成')


if __name__ == '__main__':

    # cap = cv2.VideoCapture("rtsp://admin:HGLBND@192.168.10.199/Streaming/Channels/101")
    cap = cv2.VideoCapture(f'/Users/benull/Downloads/action_video/0.MOV')
    ret, frame = cap.read()
    while ret:
        ret, frame = cap.read()
        frame = cv2.resize(frame, (480, 360))
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()
