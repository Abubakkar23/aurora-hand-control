# This import provides data classes for structured gesture results.
from dataclasses import dataclass
# This import provides math helpers for landmark distance checks.
import math
# This import provides gesture timing for double-tap recognition.
import time


# This data class carries the interpreted hand control state.
@dataclass
class GestureDecision:
    # This field stores the user-facing gesture name.
    name: str
    # This field stores the pointer x position in normalized screen space.
    pointer_x: float
    # This field stores the pointer y position in normalized screen space.
    pointer_y: float
    # This field stores the high-level action keyword for the desktop controller.
    action: str
    # This field stores the amount of scrolling to apply for this frame.
    scroll_delta: float
    # This field stores whether pointer movement should remain active.
    move_enabled: bool
    # This field stores a gesture strength value for UI feedback.
    strength: float


# This helper returns the Euclidean distance between two landmarks.
def landmark_distance(first_point, second_point) -> float:
    # This line calculates the horizontal difference between the points.
    delta_x = first_point[0] - second_point[0]
    # This line calculates the vertical difference between the points.
    delta_y = first_point[1] - second_point[1]
    # This line returns the two-dimensional distance.
    return math.hypot(delta_x, delta_y)


# This helper decides whether a finger is extended.
def is_finger_up(tip_point, pip_point) -> bool:
    # This line returns true when the fingertip is visually above the joint.
    return tip_point[1] < pip_point[1]


# This class converts hand landmarks into stable app gestures.
class GestureInterpreter:
    # This initializer creates gesture state used across frames.
    def __init__(self) -> None:
        # This line stores the running anchor used for scroll swipes.
        self.scroll_anchor_y = None
        # This line stores whether the media tap pose is active in this moment.
        self.media_tap_active = False
        # This line stores the time of the last media tap edge.
        self.last_media_tap_time = 0.0

    # This method interprets a dominant hand into a gesture decision.
    def interpret(self, landmarks) -> GestureDecision:
        # This line reads the current monotonic time for temporal gestures.
        now = time.monotonic()
        # This line stores the wrist landmark for later ratios.
        wrist = landmarks[0]
        # This line stores the thumb tip landmark.
        thumb_tip = landmarks[4]
        # This line stores the index fingertip landmark.
        index_tip = landmarks[8]
        # This line stores the middle fingertip landmark.
        middle_tip = landmarks[12]
        # This line stores the ring fingertip landmark.
        ring_tip = landmarks[16]
        # This line stores the pinky fingertip landmark.
        pinky_tip = landmarks[20]
        # This line stores the index finger joint landmark.
        index_pip = landmarks[6]
        # This line stores the middle finger joint landmark.
        middle_pip = landmarks[10]
        # This line stores the ring finger joint landmark.
        ring_pip = landmarks[14]
        # This line stores the pinky finger joint landmark.
        pinky_pip = landmarks[18]
        # This line measures the base hand scale for normalization.
        hand_scale = max(landmark_distance(wrist, middle_tip), 0.05)
        # This line measures thumb-to-index closeness for left click detection.
        index_pinch = landmark_distance(thumb_tip, index_tip) / hand_scale
        # This line measures thumb-to-middle closeness for right click detection.
        middle_pinch = landmark_distance(thumb_tip, middle_tip) / hand_scale
        # This line measures thumb-to-ring closeness for precision hold detection.
        ring_pinch = landmark_distance(thumb_tip, ring_tip) / hand_scale
        # This line measures the spacing between index and middle fingers.
        two_finger_spacing = landmark_distance(index_tip, middle_tip) / hand_scale
        # This line measures whether the index and middle fingertips are touching each other.
        index_middle_tap = landmark_distance(index_tip, middle_tip) / hand_scale
        # This line checks whether the index finger is raised.
        index_up = is_finger_up(index_tip, index_pip)
        # This line checks whether the middle finger is raised.
        middle_up = is_finger_up(middle_tip, middle_pip)
        # This line checks whether the ring finger is raised.
        ring_up = is_finger_up(ring_tip, ring_pip)
        # This line checks whether the pinky finger is raised.
        pinky_up = is_finger_up(pinky_tip, pinky_pip)
        # This line stores the normalized pointer x from the index-middle midpoint.
        pointer_x = (index_tip[0] + middle_tip[0]) / 2.0
        # This line stores the normalized pointer y from the index-middle midpoint.
        pointer_y = (index_tip[1] + middle_tip[1]) / 2.0
        # This line detects a fully closed fist state.
        fist_closed = not index_up and not middle_up and not ring_up and not pinky_up
        # This line detects a stable open-palm state.
        open_palm = index_up and middle_up and ring_up and pinky_up
        # This line detects an index-thumb pinch without requiring the bent index finger to still look raised.
        index_pinch_pose = index_pinch < 0.34 and middle_pinch > 0.32 and ring_pinch > 0.32
        # This line detects a middle-thumb pinch without requiring the bent middle finger to still look raised.
        middle_pinch_pose = middle_pinch < 0.34 and index_pinch > 0.32 and ring_pinch > 0.32
        # This line detects a ring-thumb pinch before the closed-fist logic can swallow it.
        ring_pinch_pose = ring_pinch < 0.36 and index_pinch > 0.32 and middle_pinch > 0.32
        # This line detects a two-finger navigation pose used for scrolling.
        scroll_pose = index_up and middle_up and two_finger_spacing > 0.24 and index_pinch > 0.40 and middle_pinch > 0.40 and ring_pinch > 0.36
        # This line detects a drag pose as an index pinch while the middle finger is visibly raised.
        drag_pose = index_pinch_pose and middle_up
        # This line detects a media tap pose by touching index and middle fingertips together.
        media_tap_pose = index_up and middle_up and index_middle_tap < 0.18 and index_pinch > 0.38 and middle_pinch > 0.38
        # This line resets the scroll anchor when scroll mode is not active.
        if not scroll_pose:
            # This line clears the stored scroll anchor.
            self.scroll_anchor_y = None
        # This line handles the media double-tap gesture on the pinch edge.
        if media_tap_pose:
            # This line checks whether the gesture just became active.
            if not self.media_tap_active:
                # This line checks whether a second tap arrived inside the allowed window.
                if now - self.last_media_tap_time <= 0.45:
                    # This line clears the last tap time after a complete double tap.
                    self.last_media_tap_time = 0.0
                    # This line marks the media tap as active for edge detection.
                    self.media_tap_active = True
                    # This line builds the media-toggle gesture result.
                    return GestureDecision(name="Double Tap Media", pointer_x=pointer_x, pointer_y=pointer_y, action="media_toggle", scroll_delta=0.0, move_enabled=False, strength=1.0)
                # This line stores the first tap time while waiting for the second one.
                self.last_media_tap_time = now
            # This line marks the media tap pose as active for this frame.
            self.media_tap_active = True
            # This line builds a hold state while the tap gesture is armed.
            return GestureDecision(name="Media Tap Armed", pointer_x=pointer_x, pointer_y=pointer_y, action="pause", scroll_delta=0.0, move_enabled=False, strength=0.8)
        # This line clears the media tap edge state when the pose is released.
        self.media_tap_active = False
        # This line handles precision hold before closed fist detection can hide the ring pinch.
        if ring_pinch_pose:
            # This line builds a precision hold gesture result.
            return GestureDecision(name="Ring Pinch Hold", pointer_x=pointer_x, pointer_y=pointer_y, action="pause", scroll_delta=0.0, move_enabled=False, strength=max(0.0, min(1.0, 1.0 - ring_pinch)))
        # This line returns a no-move pause state for a closed fist.
        if fist_closed:
            # This line clears the media tap state during the pause pose.
            self.media_tap_active = False
            # This line builds the paused gesture result.
            return GestureDecision(name="Closed Fist", pointer_x=pointer_x, pointer_y=pointer_y, action="pause", scroll_delta=0.0, move_enabled=False, strength=1.0)
        # This line returns a drag gesture when the drag pose is active.
        if drag_pose:
            # This line builds the drag gesture result.
            return GestureDecision(name="Drag", pointer_x=pointer_x, pointer_y=pointer_y, action="drag", scroll_delta=0.0, move_enabled=True, strength=max(0.0, min(1.0, 1.0 - index_pinch)))
        # This line returns a left-click gesture when the index pinch is detected.
        if index_pinch_pose:
            # This line builds the left-click gesture result.
            return GestureDecision(name="Index Pinch", pointer_x=pointer_x, pointer_y=pointer_y, action="left_click", scroll_delta=0.0, move_enabled=True, strength=max(0.0, min(1.0, 1.0 - index_pinch)))
        # This line returns a right-click gesture when the middle pinch is detected.
        if middle_pinch_pose:
            # This line builds the right-click gesture result.
            return GestureDecision(name="Middle Pinch", pointer_x=pointer_x, pointer_y=pointer_y, action="right_click", scroll_delta=0.0, move_enabled=True, strength=max(0.0, min(1.0, 1.0 - middle_pinch)))
        # This line returns a scroll gesture when the two-finger pose is active.
        if scroll_pose:
            # This line calculates the shared vertical position of the two main fingers.
            current_scroll_y = (index_tip[1] + middle_tip[1]) / 2.0
            # This line initializes the scroll anchor on the first scroll frame.
            if self.scroll_anchor_y is None:
                # This line stores the current scroll anchor position.
                self.scroll_anchor_y = current_scroll_y
            # This line calculates the signed movement against the last anchor.
            raw_scroll_delta = self.scroll_anchor_y - current_scroll_y
            # This line refreshes the scroll anchor with a stable trailing average.
            self.scroll_anchor_y = (self.scroll_anchor_y * 0.55) + (current_scroll_y * 0.45)
            # This line suppresses tiny unintended jitter during scroll mode.
            filtered_scroll_delta = 0.0 if abs(raw_scroll_delta) < 0.012 else raw_scroll_delta
            # This line chooses the user-facing scroll direction label.
            scroll_name = "Two Finger Swipe Up" if filtered_scroll_delta > 0.0 else "Two Finger Swipe Down"
            # This line keeps the neutral scroll label when no movement is present.
            scroll_name = "Two Finger Scroll" if filtered_scroll_delta == 0.0 else scroll_name
            # This line builds the scroll gesture result.
            return GestureDecision(name=scroll_name, pointer_x=pointer_x, pointer_y=pointer_y, action="scroll", scroll_delta=filtered_scroll_delta, move_enabled=False, strength=max(0.0, min(1.0, abs(filtered_scroll_delta) * 40.0)))
        # This line returns the open-palm move state when all fingers are visible.
        if open_palm:
            # This line builds the movement-only gesture result.
            return GestureDecision(name="Open Palm", pointer_x=pointer_x, pointer_y=pointer_y, action="move", scroll_delta=0.0, move_enabled=True, strength=max(0.0, min(1.0, two_finger_spacing)))
        # This line returns a default move state for partial but usable hand poses.
        return GestureDecision(name="Tracking", pointer_x=pointer_x, pointer_y=pointer_y, action="move", scroll_delta=0.0, move_enabled=True, strength=0.4)
