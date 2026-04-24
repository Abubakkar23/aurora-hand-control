# This import provides time checks for cooldown and listening windows.
import time
# This import provides mouse and keyboard automation on Windows.
import pyautogui

# This block loads the optional global hotkey listener package.
try:
    # This import provides a global emergency-stop hotkey listener.
    from pynput import keyboard
# This fallback keeps the app running when pynput is not installed.
except ImportError:
    # This assignment marks the hotkey dependency as unavailable.
    keyboard = None

# This line enables PyAutoGUI's corner fail-safe protection.
pyautogui.FAILSAFE = True
# This line avoids built-in motion delays so gesture control feels responsive.
pyautogui.PAUSE = 0.0


# This class applies gestures and voice commands to the desktop safely.
class DesktopController:
    # This initializer creates a new controller state object.
    def __init__(self) -> None:
        # This line stores the last action timestamp for debounce.
        self.last_action_time = 0.0
        # This line stores the current drag state.
        self.drag_active = False
        # This line stores whether all control output is currently locked.
        self.emergency_stop = False
        # This line stores the last human-readable output action.
        self.last_output = "Idle"
        # This line stores the keyboard listener instance.
        self.hotkey_listener = None

    # This method starts the global emergency-stop listener.
    def start_hotkey(self) -> None:
        # This line skips global hotkey setup when pynput is unavailable.
        if keyboard is None:
            # This line updates the visible status for the GUI.
            self.last_output = "Global Hotkey Unavailable"
            # This line exits because the dependency is missing.
            return
        # This line skips starting a second listener when one already exists.
        if self.hotkey_listener is not None:
            # This line exits because the listener is already active.
            return
        # This line builds the global hotkey mapping for Ctrl+Alt+X.
        bindings = {"<ctrl>+<alt>+x": self.toggle_emergency_stop}
        # This line creates the background hotkey listener.
        self.hotkey_listener = keyboard.GlobalHotKeys(bindings)
        # This line starts the listener thread.
        self.hotkey_listener.start()

    # This method stops the global emergency-stop listener.
    def stop_hotkey(self) -> None:
        # This line skips shutdown when there is no listener yet.
        if self.hotkey_listener is None:
            # This line exits because nothing is running.
            return
        # This line stops the listener thread safely.
        self.hotkey_listener.stop()
        # This line clears the stored listener reference.
        self.hotkey_listener = None

    # This method toggles the emergency-stop lock state.
    def toggle_emergency_stop(self) -> None:
        # This line flips the emergency-stop flag.
        self.emergency_stop = not self.emergency_stop
        # This line updates the last output label for the GUI.
        self.last_output = "Emergency Stop Enabled" if self.emergency_stop else "Emergency Stop Cleared"
        # This line ends any held drag when emergency stop is enabled.
        if self.emergency_stop and self.drag_active:
            # This line releases the held mouse button.
            pyautogui.mouseUp()
            # This line clears the drag state.
            self.drag_active = False

    # This method releases any held drag state during shutdown.
    def release_drag(self) -> None:
        # This line checks whether a drag is currently active.
        if self.drag_active:
            # This line releases the left mouse button.
            pyautogui.mouseUp()
            # This line clears the drag state flag.
            self.drag_active = False

    # This helper determines whether a click-like action may fire now.
    def can_fire(self, cooldown_seconds: float) -> bool:
        # This line reads the current monotonic time.
        current_time = time.monotonic()
        # This line checks whether the cooldown has expired.
        if current_time - self.last_action_time >= cooldown_seconds:
            # This line stores the new action timestamp.
            self.last_action_time = current_time
            # This line allows the action to continue.
            return True
        # This line denies the action while cooldown is still active.
        return False

    # This method applies the interpreted gesture to the desktop.
    def apply_gesture(self, decision, settings, screen_point) -> str:
        # This line stops all output immediately when emergency stop is active.
        if self.emergency_stop:
            # This line stores the stopped status label.
            self.last_output = "Emergency Stop Active"
            # This line returns the visible stopped state.
            return self.last_output
        # This line moves the cursor when gesture movement is enabled.
        if decision.move_enabled:
            # This line moves the mouse pointer to the smoothed screen point.
            pyautogui.moveTo(screen_point[0], screen_point[1], _pause=False)
        # This line handles gesture-specific click and drag actions.
        if decision.action == "left_click" and self.can_fire(settings.click_cooldown):
            # This line performs a left mouse click.
            pyautogui.click(button="left")
            # This line stores the last output action.
            self.last_output = "Left Click"
        # This line handles right-click output with the same cooldown safety.
        elif decision.action == "right_click" and self.can_fire(settings.click_cooldown):
            # This line performs a right mouse click.
            pyautogui.click(button="right")
            # This line stores the last output action.
            self.last_output = "Right Click"
        # This line handles drag output while the pinch is held.
        elif decision.action == "drag":
            # This line presses the left button on the first drag frame.
            if not self.drag_active:
                # This line holds the left mouse button down.
                pyautogui.mouseDown()
                # This line records the active drag state.
                self.drag_active = True
            # This line stores the last output action.
            self.last_output = "Dragging"
        # This line handles scroll output during the two-finger gesture.
        elif decision.action == "scroll":
            # This line converts the normalized scroll intent into wheel steps.
            amount = int(decision.scroll_delta * settings.scroll_sensitivity)
            # This line scrolls only when the computed amount is meaningful.
            if amount != 0:
                # This line performs the scroll wheel action.
                pyautogui.scroll(amount)
            # This line stores the last output action.
            self.last_output = f"Scrolling {amount}"
        # This line handles media play and pause on a double tap gesture.
        elif decision.action == "media_toggle":
            # This line checks whether the media action cooldown has expired.
            if self.can_fire(settings.media_tap_window):
                # This line presses the media play-pause key.
                pyautogui.press("playpause")
                # This line stores the last output action.
                self.last_output = "Play Or Pause"
            # This line preserves a readable status while the cooldown is active.
            else:
                # This line stores the cooldown-blocked media status.
                self.last_output = "Media Gesture Cooling Down"
        # This line handles the pause state for a closed fist.
        elif decision.action == "pause":
            # This line stores the last output action.
            self.last_output = "Movement Paused"
        # This line handles the move-only state.
        else:
            # This line stores the last output action.
            self.last_output = "Moving"
        # This line releases drag automatically when the current gesture is no longer drag.
        if decision.action != "drag" and self.drag_active:
            # This line releases the held left button.
            pyautogui.mouseUp()
            # This line clears the drag state.
            self.drag_active = False
        # This line returns the last output action for the GUI.
        return self.last_output
