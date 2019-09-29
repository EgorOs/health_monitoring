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
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import pandas as pd
from Xlib import display
from pynput.mouse import Button, Controller
from pynput import mouse


def get_mouse_pose_unix():
    data = display.Display().screen().root.query_pointer()._data
    return data["root_x"], data["root_y"]

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
                 "frame_id": frame_count,
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

class ActionsPerMinute:
    def __init__(self, context, file):
        self.context = context
        self.mouse = Controller()
        self.actions = 0
        self.init_time = time()
        self.apmfile = file

    def _write(self, apm):
        df = pd.DataFrame(data=apm, index=[time()], columns=["actions"])
        if not os.path.exists(self.apmfile):
            df.to_csv(self.apmfile, mode='a', header=True)
        else:
            df.to_csv(self.apmfile, mode='a', header=False)

    def reset_by_time(self):
        if time() - self.init_time > 60:
            apm = {"actions": self.actions}
            self._write(apm)
            self.context[self.__class__.__name__] = apm
            self.actions = 0
            self.init_time = time()

    def on_click(self, x, y, button, pressed):
        self.actions += 1
        self.reset_by_time()

    def on_scroll(self, x, y, dx, dy):
        self.actions += 1
        self.reset_by_time()

    def run(self):
        # ...or, in a non-blocking fashion:
        listener = mouse.Listener(
            on_click=self.on_click,
            on_scroll=self.on_scroll)
        listener.start()


class MouseTracker:
    def __init__(self, context):
        self.context = context
        self.prev_pose = None
    
    def run(self):
        while True:
            if not self.prev_pose:
                self.prev_pose = get_mouse_pose_unix()
                continue

            pose = get_mouse_pose_unix()
            timestamp = time()
            diff_x = pose[0] - self.prev_pose[0]
            diff_y = pose[1] - self.prev_pose[1]
            # print(pose, self.prev_pose, diff_x, diff_y)
            self.prev_pose = pose
            self.context[self.__class__.__name__] = {
                "time": timestamp,
                "speed_x": diff_x,
                "speed_y": diff_y
            }
            # self.buffer.append((m_x, m_y))
            # if time() - start_time > 1:
            #     avg_x_speed = 0
            #     avg_y_speed = 0
            #     for 

            #     self.buffer = []
            #     start_time = time()


class Application:
    def __init__(self):

        self.datapath = Path("data")
        os.makedirs(self.datapath, exist_ok=True)
        self.posefile = self.datapath/"pose.csv"
        self.mousefile = self.datapath/"mouse.csv"
        self.apmfile = self.datapath/"actions_per_minute.csv"

        self.context = dict()
        self.screen_tracker = ScreenTracker(self.context)
        self.pose_tracker = PoseEstimation(self.context)
        self.mouse_tracker = MouseTracker(self.context)
        self.apm_tracker = ActionsPerMinute(self.context, self.apmfile)

    def _show_posenet(self):
        if self.context.get("PoseEstimation"):
            img = self.context["PoseEstimation"]["image"]
            cv2.imshow('posenet', img)
            cv2.waitKey(1)

    def _get_state(self):
        if self.context.get("PoseEstimation"):
            return self.context["PoseEstimation"]["state"]
        return []

    def _get_mouse(self):
        if self.context.get("MouseTracker"):
            return self.context["MouseTracker"]
        return []

    def _get_time(self):
        if self.context.get("PoseEstimation"):
            return self.context["PoseEstimation"]["time"]

    def data_server(self):
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'secret!'
        app.debug = False
        socketio = SocketIO(app)

        @app.route('/')
        def index():
            return "Server is up!"

        @socketio.on('request_data')
        def test_message(message):
            emit('data_response', self._get_state())

        socketio.run(app)

    def run(self):
        self.screen_thread = threading.Thread(name='screen_thread',
                target=self.screen_tracker.run)
        self.pose_thread = threading.Thread(name='pose_thread',
                target=self.pose_tracker.run)
        self.mouse_thread = threading.Thread(name='mouse_thread',
                target=self.mouse_tracker.run)
        self.flask_thread = threading.Thread(name='flask_thread',
                target=self.data_server)
        self.apm_thread = threading.Thread(name='apm_thread',
                target=self.apm_tracker.run)
        self.screen_thread.start()
        self.mouse_thread.start()
        self.flask_thread.start()
        self.pose_thread.start()
        self.apm_thread.start()
        prev_timestamp = -1
        while True:
            self._show_posenet()
            state = self._get_state()
            if len(state) > 0:
                timestamp = self._get_time()
                if timestamp != prev_timestamp:
                    state["time"] = timestamp
                    df = pd.DataFrame(data=state, index=[timestamp], columns=["spine", "neck", "left_eye", "right_eye", "shoulder_skew"])
                    if not os.path.exists(self.posefile):
                        df.to_csv(self.posefile, mode='a', header=True)
                    else:
                        df.to_csv(self.posefile, mode='a', header=False)
                    prev_timestamp = timestamp

            mouse_data = self._get_mouse()
            if len(mouse_data) > 0:
                df = pd.DataFrame(data=mouse_data, index=[mouse_data["time"]], columns=["speed_x", "speed_y"])
                if not os.path.exists(self.mousefile):
                    df.to_csv(self.mousefile, mode='a', header=True)
                else:
                    df.to_csv(self.mousefile, mode='a', header=False)


    def __exit__(self):
        self.screen_thread.join()
        self.pose_thread.join()
        self.mouse_thread.join()
        self.flask_thread.join()
        self.apm_thread.join()


if __name__ == "__main__":
    app = Application()
    app.run()
