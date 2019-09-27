import mss
import mss.tools
import cv2
import numpy as np

prev_img = None

with mss.mss() as sct:
    monitor = sct.monitors[1]

    left = monitor["left"]
    top = monitor["top"]
    right = monitor["width"]
    lower = monitor["height"]
    bbox = (left, top, right, lower)

    while True:
        img = np.array(sct.grab(bbox))
        cv2.imshow("Screen", img)
        cv2.waitKey(10)
