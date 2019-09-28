import mss
import mss.tools
import cv2
import numpy as np
import os
from pathlib import Path

class PoseEstimation:
    

class ScreenTracker:

    def __init__(self):
        self.video_buffer = []
        self.__init_screen()
        file = Path(os.getcwd())/'outpy.avi'
        # self.video = cv2.VideoWriter(file, cv2.VideoWriter_fourcc(*'XVID'), 25, 
        #    self.img_size[0],self.img_size[1])
        self.video = cv2.VideoWriter(file,1, 10, self.img_size)

    def __init_screen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            left = monitor["left"]
            top = monitor["top"]
            right = monitor["width"]
            lower = monitor["height"]
            self.img_size = (monitor["width"], monitor["height"])
            self.bbox = (left, top, right, lower)

    def run(self, record=False):
        with mss.mss() as sct:
            while True:
                img = np.array(sct.grab(self.bbox))
                # cv2.imshow("Screen", img)
                # cv2.waitKey(10)
                if record:
                    self.video_buffer.append(img)
                    self.video.write(cv2.resize(img, self.img_size))
                    print(self.img_size)
                if len(self.video_buffer) > 200:
                    self.video.release()
                    break


    # def __exit__
    # def save_video(self):
    #     out = cv2.VideoWriter('project.avi',cv2.VideoWriter_fourcc(*'DIVX') , 
    #         15, self.img_size)
 
    #     for i in range(len(self.video_buffer)):
    #         out.write(self.video_buffer[i])
    #     out.release()


if __name__ == "__main__":
    screen_tracker = ScreenTracker()
    try:
        screen_tracker.run(record=True)
    except KeyboardInterrupt:
        screen_tracker.video.release()
        exit()
