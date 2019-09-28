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
import math


class PoseEstimation:
    MODEL = 101
    SCALE_FACTOR = 0.7125
    def __init__(self, context, camera=(1366, 768)):    
        self.context = context
        self.camera = camera
        self.user_init_iterations_left = 5
        self.initialized = False
        self.__neck_offset_lst = []
        self.__spine_offset_lst = []
        self.normal_spine_offset = None
        self.normal_neck_offset = None

    def user_initialization(self, body_data):
        if len(body_data["center"]) > 0:
            self.__neck_offset_lst.append(self._get_neck_offset(body_data))
            self.__spine_offset_lst.append(body_data["center"][1])
            self.user_init_iterations_left -= 1
            print("Initialization %s iterations left" % self.user_init_iterations_left)

        if self.user_init_iterations_left == 0:
            print("Initialization is complete")
            self.normal_spine_offset = sum(self.__spine_offset_lst)/len(self.__spine_offset_lst)
            self.normal_neck_offset = sum(self.__neck_offset_lst)/len(self.__neck_offset_lst)
            self.initialized = True

    def _get_neck_offset(self, body_data):
        nose_pose = body_data["body_pts"]["Nose"]
        chest_center = body_data["center"]
        neck_offset = chest_center[1] - nose_pose[1]
        return neck_offset

    @staticmethod
    def _calculate_shoulder_skew(body_data):
        chest_pts = body_data["body_parts"]["chest"]
        chest_pts = sorted(chest_pts, key=lambda pt: pt[0], reverse=True)
        max_x, sign_y_right = chest_pts[0]
        min_x, sign_y_left = chest_pts[1]
        chest_pts = sorted(chest_pts, key=lambda pt: pt[1], reverse=True)
        max_y = chest_pts[0][1]
        min_y = chest_pts[1][1]
        skew = (sign_y_left - sign_y_right)/abs(sign_y_left - sign_y_right)*math.atan2((max_y - min_y),(max_x - min_x))*180/math.pi
        return skew

    def analyze_pose(self, body_data):
        EYE_OPEN = 1
        EYE_CLOSED = 0
        SPINE_UNDEFINED = 0
        SPINE_GOOD = 1
        SPINE_BAD = -1
        NECK_UNDEFINED = 0
        NECK_GOOD = 1
        NECK_BAD = -1
        state = {
            "spine": SPINE_UNDEFINED,
            "neck": NECK_UNDEFINED,
            "left_eye": EYE_OPEN,
            "right_eye": EYE_OPEN,
            "shoulder_skew": 0,
        }

        if not self.initialized:
            return state
        
        if len(body_data["center"]) > 0:
            neck_offset = self._get_neck_offset(body_data)
            if neck_offset < self.normal_neck_offset*0.8:
                state["neck"] = NECK_BAD
            else:
                state["neck"] = NECK_GOOD
            spine_offset = body_data["center"][1]
            if spine_offset > self.normal_spine_offset*1.1:
                state["spine"] = SPINE_BAD
            else:
                state["spine"] = SPINE_GOOD
            if len(body_data["body_parts"]) > 0:
                if body_data["body_parts"].get("chest").any():
                    state["shoulder_skew"] = self._calculate_shoulder_skew(body_data)
        print(state)
        return state

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
                overlay_image, body_data = posenet.analyze_pose(
                    display_image, pose_scores, keypoint_scores, keypoint_coords,
                    min_pose_score=0.15, min_part_score=0.1)

                if not self.initialized:
                    self.user_initialization(body_data)

                state = self.analyze_pose(body_data)
                frame_count += 1
                data = {
                "state": state,
                 "image": overlay_image, 
                 "frame_id": frame_count
                 "time": time()
                 }
                self.context[self.__class__.__name__] = data


class ScreenTracker:

    def __init__(self, context):
        self.context = context
        self.context[self.__class__.__name__] = []
        self.video_buffer = []
        self.__init_screen()

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

    def _get_state(self):
        if self.context.get("PoseEstimation"):
            return self.context["PoseEstimation"]["state"]
        return []

    def run(self):
        self.screen_thread = threading.Thread(name='screen_thread',
                target=self.screen_tracker.run)
        self.pose_thread = threading.Thread(name='pose_thread',
                target=self.pose_tracker.run)
        self.screen_thread.start()
        self.pose_thread.start()
        while True:
            self._show_posenet()
            state = self._get_state()
            if len(state) > 0:
                print(state)
                pass

    def __exit__(self):
        self.screen_thread.join()
        self.pose_thread.join()


if __name__ == "__main__":
    app = Application()
    app.run()
