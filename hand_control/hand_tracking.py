# This import provides frame timing for FPS calculations.
import time
# This import provides OpenCV camera and drawing support.
import cv2
# This import provides the MediaPipe image wrapper for Tasks inference.
from mediapipe import Image, ImageFormat
# This import provides MediaPipe base options for model loading.
from mediapipe.tasks.python.core.base_options import BaseOptions
# This import provides the modern MediaPipe hand landmarker classes.
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, HandLandmarksConnections, RunningMode
# This import provides NumPy arrays for frame conversion.
import numpy as np
# This import provides the shared models folder path.
from hand_control.config import MODELS_DIR

# This constant points to the required MediaPipe hand landmarker model file.
HAND_LANDMARKER_MODEL_PATH = MODELS_DIR / "hand_landmarker.task"


# This class manages webcam capture and hand landmark extraction.
class HandTracker:
    # This initializer creates the capture and MediaPipe state.
    def __init__(self, settings) -> None:
        # This line stores the camera index for later restarts.
        self.camera_index = settings.camera_index
        # This line stores the requested camera width.
        self.camera_width = settings.camera_width
        # This line stores the requested camera height.
        self.camera_height = settings.camera_height
        # This line stores the configured inference downscale factor.
        self.inference_scale = settings.inference_scale
        # This line opens the selected webcam device.
        self.capture = cv2.VideoCapture(self.camera_index)
        # This line asks OpenCV to keep the capture buffer small when supported.
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # This line requests a readable capture width.
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
        # This line requests a readable capture height.
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        # This line stores the MediaPipe Tasks hand connection list for manual drawing.
        self.hand_connections = HandLandmarksConnections.HAND_CONNECTIONS
        # This line stops startup with a clear message when the hand model file is missing.
        if not HAND_LANDMARKER_MODEL_PATH.exists():
            # This line raises a readable setup error for the GUI.
            raise RuntimeError(f"Missing MediaPipe hand model: {HAND_LANDMARKER_MODEL_PATH}")
        # This line builds the MediaPipe Tasks options with live-video settings.
        options = HandLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(HAND_LANDMARKER_MODEL_PATH)), running_mode=RunningMode.VIDEO, num_hands=2, min_hand_detection_confidence=0.6, min_hand_presence_confidence=0.5, min_tracking_confidence=0.55)
        # This line creates the modern MediaPipe hand landmarker.
        self.hands = HandLandmarker.create_from_options(options)
        # This line stores the previous frame time for FPS updates.
        self.last_frame_time = time.monotonic()
        # This line stores the current FPS estimate.
        self.current_fps = 0.0

    # This method reports whether the selected camera opened successfully.
    def is_ready(self) -> bool:
        # This line returns the camera open state.
        return self.capture.isOpened()

    # This method reads one frame and extracts any hand landmarks.
    def read(self):
        # This line reads the next frame from the webcam.
        success, frame = self.capture.read()
        # This line returns a failure marker when the camera read fails.
        if not success:
            # This line returns empty results for the failed frame.
            return False, None, [], 0.0
        # This line flips the frame horizontally for mirror control.
        frame = cv2.flip(frame, 1)
        # This line converts the frame into RGB for MediaPipe.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # This line downscales the RGB frame to reduce inference latency.
        inference_frame = cv2.resize(rgb_frame, None, fx=self.inference_scale, fy=self.inference_scale, interpolation=cv2.INTER_LINEAR)
        # This line wraps the downscaled frame in the MediaPipe image container.
        mp_image = Image(image_format=ImageFormat.SRGB, data=inference_frame)
        # This line creates a millisecond timestamp for the video task API.
        timestamp_ms = int(time.monotonic() * 1000)
        # This line processes the frame for hand landmarks with the Tasks API.
        results = self.hands.detect_for_video(mp_image, timestamp_ms)
        # This line creates a list for normalized hand landmark sets.
        all_landmarks = []
        # This line handles frames where one or more hands were detected.
        if results.hand_landmarks:
            # This line loops over each detected hand.
            for hand_landmarks in results.hand_landmarks:
                # This line creates a normalized landmark list for this hand.
                points = [(landmark.x, landmark.y) for landmark in hand_landmarks]
                # This line stores the normalized landmark list.
                all_landmarks.append(points)
                # This line draws the hand skeleton lines and points manually.
                self.draw_hand_landmarks(frame, points)
        # This line updates the live FPS estimate.
        self.current_fps = self.calculate_fps()
        # This line returns the processed frame, landmarks, and FPS.
        return True, frame, all_landmarks, self.current_fps

    # This helper estimates the current FPS.
    def calculate_fps(self) -> float:
        # This line reads the current monotonic time.
        now = time.monotonic()
        # This line calculates the elapsed time since the last frame.
        elapsed = max(now - self.last_frame_time, 1e-6)
        # This line stores the new reference time.
        self.last_frame_time = now
        # This line returns the reciprocal FPS estimate.
        return 1.0 / elapsed

    # This method chooses the dominant hand by largest bounding area.
    def select_dominant_hand(self, all_landmarks):
        # This line returns no dominant hand when nothing was detected.
        if not all_landmarks:
            # This line signals that no hand is available.
            return None
        # This line returns the hand with the largest normalized bounding box area.
        return max(all_landmarks, key=self.hand_area)

    # This method draws landmark connections and landmark points on the frame.
    def draw_hand_landmarks(self, frame, landmarks) -> None:
        # This line loops over each connection defined by MediaPipe.
        for connection in self.hand_connections:
            # This line converts the starting landmark x coordinate into pixels.
            start_x = int(landmarks[connection.start][0] * frame.shape[1])
            # This line converts the starting landmark y coordinate into pixels.
            start_y = int(landmarks[connection.start][1] * frame.shape[0])
            # This line converts the ending landmark x coordinate into pixels.
            end_x = int(landmarks[connection.end][0] * frame.shape[1])
            # This line converts the ending landmark y coordinate into pixels.
            end_y = int(landmarks[connection.end][1] * frame.shape[0])
            # This line draws one connection segment between the landmarks.
            cv2.line(frame, (start_x, start_y), (end_x, end_y), (0, 255, 120), 2)
        # This line loops over each landmark point for visible joints.
        for landmark in landmarks:
            # This line converts the landmark x coordinate into pixels.
            center_x = int(landmark[0] * frame.shape[1])
            # This line converts the landmark y coordinate into pixels.
            center_y = int(landmark[1] * frame.shape[0])
            # This line draws the landmark joint marker.
            cv2.circle(frame, (center_x, center_y), 4, (255, 140, 0), -1)

    # This helper calculates the approximate normalized area of a hand.
    def hand_area(self, landmarks) -> float:
        # This line creates a list of x coordinates from the hand.
        xs = [point[0] for point in landmarks]
        # This line creates a list of y coordinates from the hand.
        ys = [point[1] for point in landmarks]
        # This line returns the bounding-box area.
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    # This method draws extra overlays for the dominant hand.
    def draw_dominant_overlay(self, frame, dominant_landmarks, gesture_name, output_text, controls_enabled, fps_value) -> None:
        # This line draws a fallback message when no hand is present.
        if dominant_landmarks is None:
            # This line writes the no-hand message on the frame.
            cv2.putText(frame, "Show your hand to begin tracking", (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 180, 255), 2)
        # This line handles frames where a dominant hand exists.
        if dominant_landmarks is not None:
            # This line converts normalized x values into pixel coordinates.
            xs = [int(point[0] * frame.shape[1]) for point in dominant_landmarks]
            # This line converts normalized y values into pixel coordinates.
            ys = [int(point[1] * frame.shape[0]) for point in dominant_landmarks]
            # This line draws a visible bounding box around the dominant hand.
            cv2.rectangle(frame, (min(xs), min(ys)), (max(xs), max(ys)), (0, 200, 255), 2)
            # This line draws a visible marker on each fingertip.
            for fingertip_index in [4, 8, 12, 16, 20]:
                # This line converts the fingertip x coordinate into pixels.
                center_x = int(dominant_landmarks[fingertip_index][0] * frame.shape[1])
                # This line converts the fingertip y coordinate into pixels.
                center_y = int(dominant_landmarks[fingertip_index][1] * frame.shape[0])
                # This line draws the fingertip marker.
                cv2.circle(frame, (center_x, center_y), 7, (255, 255, 0), -1)
        # This line builds the control-state label.
        control_label = "Enabled" if controls_enabled else "Disabled"
        # This line draws the current gesture label.
        cv2.putText(frame, f"Gesture: {gesture_name}", (20, frame.shape[0] - 90), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        # This line draws the last desktop-output label.
        cv2.putText(frame, f"Action: {output_text}", (20, frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        # This line draws the current mode label.
        cv2.putText(frame, "Mode: Hand Control", (20, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        # This line draws the live FPS label.
        cv2.putText(frame, f"FPS: {fps_value:.1f}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)
        # This line draws the control-enabled label.
        cv2.putText(frame, f"Controls: {control_label}", (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0) if controls_enabled else (0, 0, 255), 2)
        # This line draws a compact gesture help strip at the bottom.
        cv2.putText(frame, "Open Palm Move | Two Finger Swipe Scroll | Touch Index+Middle Twice For Media | Ring Pinch Hold", (20, frame.shape[0] - 120), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (180, 220, 255), 1)

    # This method converts an OpenCV frame into a Qt-friendly RGB array.
    def to_rgb_image(self, frame):
        # This line converts the BGR frame into RGB order.
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # This line returns a contiguous RGB array for Qt.
        return np.ascontiguousarray(rgb_frame)

    # This method releases capture and tracker resources.
    def close(self) -> None:
        # This line releases the webcam when it exists.
        if self.capture is not None:
            # This line closes the webcam device.
            self.capture.release()
        # This line closes the MediaPipe hand tracker.
        self.hands.close()
