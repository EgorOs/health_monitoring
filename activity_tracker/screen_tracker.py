import mss
import mss.tools
import cv2
import numpy as np

def to_cv_img(img):
    print(img)
    return np.float32(img)

with mss.mss() as sct:
    monitor = sct.monitors[1]

    left = monitor["left"]
    top = monitor["top"]
    right = monitor["width"]
    lower = monitor["height"]
    bbox = (left, top, right, lower)

    while True:
        im = sct.grab(bbox)  # type: ignore
        cv2.imshow("Screen", np.array(im))
        cv2.waitKey(10)