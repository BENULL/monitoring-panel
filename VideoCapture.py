# coding = utf-8
import cv2
import os
from multiprocessing import Queue
import ffmpeg
import numpy as np
cv2.setNumThreads(0)


class VideoCapture:

    def __init__(self, camera, channel):
        self.camera = camera
        self.channel = channel
        self.frameNum = 1
        self.scaled_width, self.scaled_height = 432, 267

    def captureFrame(self, queue: Queue):
        print(f'{self.camera} begin')
        cap = cv2.VideoCapture(self.camera)
        retry = 0
        ret, frame = cap.read()
        while ret or retry <= 3:
            if ret:
                frame = cv2.resize(frame, (self.scaled_width, self.scaled_height))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                queue.put((self.channel, self.frameNum, frame))
                self.frameNum += 1
                ret, frame = cap.read()
            else:
                cap = cv2.VideoCapture(self.camera)
                print(f'{self.camera}  reconnect')
                ret, frame = cap.read()
                retry = retry+1 if not ret else 0
        cap.release()
        queue.put('DONE')
        print(f'{self.camera} end')

    def capture(self):
        out = (
            ffmpeg
                .input(self.camera, rtsp_transport='tcp')
                .filter('scale', self.scaled_width, self.scaled_height)
                .output('pipe:', format='rawvideo', pix_fmt='rgb24', loglevel="quiet", )
                .run_async(pipe_stdout=True)
        )
        return out

    def captureFrameByFfmpeg(self, queue):
        print(f'{self.camera} begin by ffmpeg')
        # probe = ffmpeg.probe(self.camera)
        # video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        # self.width = int(video_stream['width'])
        # self.height = int(video_stream['height'])
        out = self.capture()
        retry = 0
        byte_len = self.scaled_height * self.scaled_width * 3
        in_bytes = out.stdout.read(byte_len)
        while True:
            # in_bytes or retry <= 10:
            if retry > 100:
                print(f'{self.camera} reconnect by ffmpeg')
                out = self.capture()
                in_bytes = out.stdout.read(byte_len)
            if not in_bytes:
                retry += 1
                in_bytes = out.stdout.read(byte_len)
                continue
            retry = 0
            frame = np.frombuffer(in_bytes, dtype=np.uint8).reshape(self.scaled_height, self.scaled_width, 3)
            queue.put((self.channel, self.frameNum, frame))
            self.frameNum += 1
            in_bytes = out.stdout.read(byte_len)

        queue.put('DONE')
        print(f'{self.camera} end')


if __name__ == '__main__':
    cap = cv2.VideoCapture('rtsp://admin:SMWILY@192.168.10.174/Streaming/Channels/101')
    ret, frame = cap.read()
    while ret:
        ret, frame = cap.read()
        frame = cv2.resize(frame, (480, 360))
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()
