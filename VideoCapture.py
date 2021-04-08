# coding = utf-8
import cv2
import os
from multiprocessing import Queue
import signal


class VideoCapture:

    def __init__(self, camera):
        self.camera = camera

    def captureFrame(self, queue: Queue):
        print(f'{self.camera}开始处理')
        cap = cv2.VideoCapture(self.camera)
        # cap = cv2.VideoCapture("rtp://127.0.0.1:55555")
        frameNum = 1
        ret, frame = cap.read()
        while (ret):
            frame = cv2.resize(frame, (480, 360))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            queue.put((self.camera, frameNum, frame))
            frameNum += 1
            ret, frame = cap.read()
        cap.release()
        queue.put('DONE')
        print(f'{self.camera}进程{os.getpid()}处理完成')


if __name__ == '__main__':
    import cv2
    cap = cv2.VideoCapture("rtp://127.0.0.1:1234")
    ret, frame = cap.read()
    while ret:
        ret, frame = cap.read()
        cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()




