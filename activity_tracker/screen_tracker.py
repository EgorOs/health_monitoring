import mss
import mss.tools
import cv2
import numpy as np
import os
from pathlib import Path
import tensorflow as tf
import posenet
import threading
from time import time

class PoseEstimation:
    MODEL = 101
    SCALE_FACTOR = 0.7125
    def __init__(self, context, camera=(1366, 768)):    
        self.context = context
        self.camera = camera

    def run(self):
        with tf.Session() as sess:
            self.model_cfg, self.model_outputs = posenet.load_model(self.MODEL, sess)
            self.output_stride = self.model_cfg['output_stride']
            cap = cv2.VideoCapture(0)
            cap.set(3, self.camera[0])
            cap.set(4, self.camera[1])
            # start = time.time()
            frame_count = 0
            while True:
                input_image, display_image, output_scale = posenet.read_cap(
                    cap, scale_factor=self.SCALE_FACTOR, output_stride=self.output_stride, )

                heatmaps_result, offsets_result, displacement_fwd_result, displacement_bwd_result = sess.run(
                    self.model_outputs,
                    feed_dict={'image:0': input_image}
                )

                pose_scores, keypoint_scores, keypoint_coords = posenet.decode_multi.decode_multiple_poses(
                    heatmaps_result.squeeze(axis=0),
                    offsets_result.squeeze(axis=0),
                    displacement_fwd_result.squeeze(axis=0),
                    displacement_bwd_result.squeeze(axis=0),
                    output_stride=self.output_stride,
                    max_pose_detections=10,
                    min_pose_score=0.15)

                keypoint_coords *= output_scale
                overlay_image = posenet.draw_skel_and_kp_single(
                    display_image, pose_scores, keypoint_scores, keypoint_coords,
                    min_pose_score=0.15, min_part_score=0.1)

                frame_count += 1
                data = {
                "coords": keypoint_coords,
                 "image": overlay_image, 
                 "frame_id": frame_count}
                self.context[self.__class__.__name__] = data


class ScreenTracker:

    def __init__(self, context):
        self.context = context
        self.context[self.__class__.__name__] = []
        self.video_buffer = []
        self.__init_screen()
        file = Path(os.getcwd())/'outpy.avi'

    def __init_screen(self):
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            left = monitor["left"]
            top = monitor["top"]
            right = monitor["width"]
            lower = monitor["height"]
            self.img_size = (monitor["width"], monitor["height"])
            self.bbox = (left, top, right, lower)

    def run(self):
        with mss.mss() as sct:
            while True:
                img = np.array(sct.grab(self.bbox))
                # cv2.imshow("Screen", img)
                # cv2.waitKey(10)
                self.context[self.__class__.__name__].append(2)

class Application:
    def __init__(self):
        self.context = dict()
        self.screen_tracker = ScreenTracker(self.context)
        self.pose_tracker = PoseEstimation(self.context)

    def _show_posenet(self):
        if self.context.get("PoseEstimation"):
            img = self.context["PoseEstimation"]["image"]
            cv2.imshow('posenet', img)
            cv2.waitKey(1)

    def _get_poses(self):
        if self.context.get("PoseEstimation"):
            return self.context["PoseEstimation"]["coords"]
        return []

    def run(self):
        self.screen_thread = threading.Thread(name='screen_thread',
                target=self.screen_tracker.run)
        self.pose_thread = threading.Thread(name='pose_thread',
                target=self.pose_tracker.run)
        self.screen_thread.start()
        self.pose_thread.start()
        while True:
                # print(time() - start_time)

            # self.screen_thread.join()
            # self.pose_thread.join()
            self._show_posenet()
            if len(self._get_poses()) > 0:
                print(self._get_poses()[0])



    def __exit__(self):
        self.screen_thread.join()
        self.pose_thread.join()


if __name__ == "__main__":
    app = Application()
    app.run()
