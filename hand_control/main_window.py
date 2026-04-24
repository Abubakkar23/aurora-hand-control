# This import provides thread-safe timing inside the worker loop.
import time
# This import provides package presence checks without importing heavy packages.
import importlib.util
# This import provides Qt core classes and signals.
from PySide6.QtCore import QThread, Qt, Signal
# This import provides Qt image, icon, font, and keyboard shortcut classes.
from PySide6.QtGui import QFont, QImage, QKeySequence, QPixmap, QShortcut
# This import provides Qt widgets for the desktop interface.
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QMainWindow, QProgressBar, QPushButton, QSlider, QStyle, QTextEdit, QVBoxLayout, QWidget
# This import loads app configuration helpers.
from hand_control.config import MODELS_DIR, AppSettings, load_settings, save_settings
# This import loads the desktop automation controller.
from hand_control.desktop_control import DesktopController
# This import loads gesture interpretation.
from hand_control.gestures import GestureInterpreter
# This import loads the hand tracking service.
from hand_control.hand_tracking import HandTracker


# This worker thread captures frames, interprets gestures, and updates the GUI.
class TrackingWorker(QThread):
    # This signal sends the latest preview image to the GUI.
    frame_ready = Signal(QImage)
    # This signal sends the latest status payload to the GUI.
    status_ready = Signal(dict)
    # This signal sends recoverable error text to the GUI.
    error_ready = Signal(str)

    # This initializer stores the shared services and settings.
    def __init__(self, settings: AppSettings, controller: DesktopController) -> None:
        # This line initializes the QThread base class.
        super().__init__()
        # This line stores the shared settings object.
        self.settings = settings
        # This line stores the desktop controller.
        self.controller = controller
        # This line creates the gesture interpreter.
        self.interpreter = GestureInterpreter()
        # This line stores the optional hand tracker instance.
        self.tracker = None
        # This line stores the running flag for loop control.
        self.running = False
        # This line stores the last smoothed screen x coordinate.
        self.smoothed_x = None
        # This line stores the last smoothed screen y coordinate.
        self.smoothed_y = None
        # This line caches the primary screen size once to avoid repeated calls.
        self.screen_width, self.screen_height = self.controller_screen_size()

    # This method maps normalized hand coordinates into screen coordinates.
    def map_to_screen(self, pointer_x: float, pointer_y: float):
        # This line applies configurable edge padding to the x coordinate.
        adjusted_x = self.apply_padding(pointer_x, self.settings.edge_padding)
        # This line applies configurable edge padding to the y coordinate.
        adjusted_y = self.apply_padding(pointer_y, self.settings.edge_padding)
        # This line applies a central dead zone to reduce small tremors.
        adjusted_x = self.apply_dead_zone(adjusted_x, self.settings.dead_zone)
        # This line applies a central dead zone to reduce small tremors.
        adjusted_y = self.apply_dead_zone(adjusted_y, self.settings.dead_zone)
        # This line converts the normalized x coordinate into pixels.
        target_x = int(adjusted_x * self.screen_width)
        # This line converts the normalized y coordinate into pixels.
        target_y = int(adjusted_y * self.screen_height)
        # This line calculates the current pointer jump distance for adaptive smoothing.
        distance = 0.0 if self.smoothed_x is None or self.smoothed_y is None else (((target_x - self.smoothed_x) ** 2) + ((target_y - self.smoothed_y) ** 2)) ** 0.5
        # This line converts the jump distance into an extra responsiveness boost.
        dynamic_boost = min(self.settings.motion_boost, distance / max(self.screen_width, self.screen_height))
        # This line combines the base smoothing with the dynamic boost.
        alpha = max(0.08, min(0.92, self.settings.smoothing + dynamic_boost))
        # This line smooths the x coordinate using the adaptive factor.
        self.smoothed_x = target_x if self.smoothed_x is None else int((alpha * target_x) + ((1.0 - alpha) * self.smoothed_x))
        # This line smooths the y coordinate using the adaptive factor.
        self.smoothed_y = target_y if self.smoothed_y is None else int((alpha * target_y) + ((1.0 - alpha) * self.smoothed_y))
        # This line returns the smoothed screen coordinates.
        return self.smoothed_x, self.smoothed_y

    # This helper returns the primary screen size from PyAutoGUI.
    def controller_screen_size(self):
        # This import is local so GUI startup stays lightweight.
        import pyautogui
        # This line returns the current screen resolution.
        return pyautogui.size()

    # This helper applies configurable edge padding to a normalized coordinate.
    def apply_padding(self, value: float, padding: float) -> float:
        # This line clamps the value into a safe range.
        value = max(0.0, min(1.0, value))
        # This line scales the coordinate into the padded region.
        return max(0.0, min(1.0, (value - padding) / max(1.0 - (padding * 2.0), 1e-6)))

    # This helper reduces sensitivity around the center of the screen.
    def apply_dead_zone(self, value: float, dead_zone: float) -> float:
        # This line calculates the distance from the center.
        distance = value - 0.5
        # This line returns exact center when the movement is tiny.
        if abs(distance) < dead_zone:
            # This line locks the coordinate to the center.
            return 0.5
        # This line returns the unchanged coordinate outside the dead zone.
        return value

    # This method runs the tracking loop on the worker thread.
    def run(self) -> None:
        # This line sets the running flag before service startup.
        self.running = True
        # This block protects the worker from crashing the GUI thread.
        try:
            # This line creates the hand tracker for the selected camera.
            self.tracker = HandTracker(self.settings)
            # This line reports a camera error when the device could not open.
            if not self.tracker.is_ready():
                # This line emits a readable camera error.
                self.error_ready.emit("Could not open the selected camera.")
                # This line stops the worker loop immediately.
                self.running = False
                # This line exits the worker.
                return
            # This line starts the emergency-stop hotkey listener.
            self.controller.start_hotkey()
            # This line enters the main capture and processing loop.
            while self.running:
                # This line reads the next processed frame from the camera.
                success, frame, all_landmarks, fps_value = self.tracker.read()
                # This line reports a frame-read issue and retries.
                if not success or frame is None:
                    # This line emits a readable capture warning.
                    self.error_ready.emit("Camera frame could not be read.")
                    # This line waits briefly before trying again.
                    time.sleep(0.05)
                    # This line continues to the next loop iteration.
                    continue
                # This line selects the dominant hand for control output.
                dominant = self.tracker.select_dominant_hand(all_landmarks)
                # This line stores a default gesture label.
                gesture_name = "No Hand"
                # This line stores the current output label.
                output_text = self.controller.last_output
                # This line stores a default gesture strength for the UI.
                gesture_strength = "0.00"
                # This line processes the dominant hand when one exists.
                if dominant is not None:
                    # This line interprets the dominant hand into a gesture decision.
                    decision = self.interpreter.interpret(dominant)
                    # This line updates the visible gesture label.
                    gesture_name = decision.name
                    # This line updates the gesture strength label.
                    gesture_strength = f"{decision.strength:.2f}"
                    # This line applies pointer mapping to the current gesture.
                    screen_point = self.map_to_screen(decision.pointer_x, decision.pointer_y)
                    # This line applies desktop output only when controls are enabled.
                    if self.settings.controls_enabled:
                        # This line sends the gesture to the desktop controller.
                        output_text = self.controller.apply_gesture(decision, self.settings, screen_point)
                    # This line keeps the output readable when controls are disabled.
                    else:
                        # This line stores the disabled output status.
                        output_text = "Tracking Only"
                # This line draws the current overlays onto the preview frame.
                self.tracker.draw_dominant_overlay(frame, dominant, gesture_name, output_text, self.settings.controls_enabled and not self.controller.emergency_stop, fps_value)
                # This line converts the frame into a Qt-friendly RGB array.
                rgb_frame = self.tracker.to_rgb_image(frame)
                # This line creates the Qt image around the RGB buffer.
                image = QImage(rgb_frame.data, rgb_frame.shape[1], rgb_frame.shape[0], rgb_frame.strides[0], QImage.Format.Format_RGB888).copy()
                # This line sends the preview image to the GUI.
                self.frame_ready.emit(image)
                # This line sends the latest status payload to the GUI.
                self.status_ready.emit({"gesture": gesture_name, "output": output_text, "fps": f"{fps_value:.1f}", "emergency_stop": self.controller.emergency_stop, "strength": gesture_strength})
                # This line yields briefly so the UI stays responsive under heavy load.
                self.msleep(1)
        # This block reports any unexpected worker failure to the GUI.
        except Exception as error:
            # This line emits the unexpected error text.
            self.error_ready.emit(str(error))
        # This block always releases resources on exit.
        finally:
            # This line releases any held mouse drag safely.
            self.controller.release_drag()
            # This line stops the global emergency-stop hotkey listener.
            self.controller.stop_hotkey()
            # This line closes the hand tracker when it exists.
            if self.tracker is not None:
                # This line releases the tracker resources.
                self.tracker.close()

    # This method requests a clean worker shutdown.
    def stop(self) -> None:
        # This line clears the running flag for the loop.
        self.running = False


# This main window hosts the preview, controls, and status panels.
class MainWindow(QMainWindow):
    # This initializer builds the GUI and loads saved settings.
    def __init__(self) -> None:
        # This line initializes the QMainWindow base class.
        super().__init__()
        # This line loads the saved settings from disk.
        self.settings = load_settings()
        # This line creates the desktop automation controller.
        self.controller = DesktopController()
        # This line stores the worker thread reference.
        self.worker = None
        # This line sets the main window title.
        self.setWindowTitle("Aurora Hand Control")
        # This line sets a comfortable starting window size.
        self.resize(1440, 900)
        # This line applies the rich window styling and typography.
        self.apply_window_theme()
        # This line builds the full user interface layout.
        self.build_ui()
        # This line applies the saved settings to the widgets.
        self.populate_from_settings()
        # This line creates the in-window emergency shortcut.
        self.local_emergency_shortcut = QShortcut(QKeySequence("Ctrl+Alt+X"), self)
        # This line connects the shortcut to the emergency-stop toggle.
        self.local_emergency_shortcut.activated.connect(self.handle_emergency_stop)

    # This method applies the visual theme to the whole window.
    def apply_window_theme(self) -> None:
        # This line sets the main display font for the application window.
        self.setFont(QFont("Segoe UI Variable", 10))
        # This line applies a colorful rich stylesheet to the full window.
        self.setStyleSheet(
            "QMainWindow { background-color: #101418; }"
            "QWidget { color: #f4f7fb; }"
            "QLabel#TitleLabel { font-size: 30px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px; }"
            "QLabel#SubtitleLabel { font-size: 12px; color: #b8c7d9; }"
            "QLabel#StatusPill { background-color: #0f2530; border: 1px solid #24576a; border-radius: 8px; padding: 8px 10px; color: #dff7ff; font-weight: 700; }"
            "QLabel#SafetyPill { background-color: #17291f; border: 1px solid #2f7d46; border-radius: 8px; padding: 8px 10px; color: #dcfce7; font-weight: 800; }"
            "QFrame#Card { background-color: #151c24; border: 1px solid #334155; border-radius: 12px; }"
            "QPushButton { background-color: #0f8b8d; color: white; border: 0px; border-radius: 10px; padding: 11px 14px; font-weight: 700; }"
            "QPushButton:hover { background-color: #13a7aa; }"
            "QPushButton:pressed { background-color: #096164; }"
            "QPushButton:disabled { background-color: #334155; color: #93a4b8; }"
            "QPushButton#DangerButton { background-color: #cf3f12; }"
            "QPushButton#DangerButton:hover { background-color: #f36a21; }"
            "QComboBox, QTextEdit { background-color: #0f1720; border: 1px solid #334155; border-radius: 8px; padding: 8px; }"
            "QCheckBox { spacing: 10px; font-weight: 600; }"
            "QSlider::groove:horizontal { background: #263445; height: 8px; border-radius: 4px; }"
            "QSlider::handle:horizontal { background: #fbbf24; width: 18px; margin: -5px 0; border-radius: 9px; }"
            "QProgressBar { background-color: #0f1720; border: 1px solid #334155; border-radius: 8px; height: 12px; text-align: center; }"
            "QProgressBar::chunk { background-color: #22c55e; border-radius: 8px; }"
        )

    # This helper creates a reusable card frame.
    def create_card(self) -> QFrame:
        # This line creates the card frame widget.
        card = QFrame()
        # This line gives the card a dedicated style identifier.
        card.setObjectName("Card")
        # This line returns the fully prepared card.
        return card

    # This method builds the full desktop interface.
    def build_ui(self) -> None:
        # This line creates the root content widget.
        root = QWidget()
        # This line creates the main horizontal layout.
        main_layout = QHBoxLayout()
        # This line sets generous spacing between the main panels.
        main_layout.setSpacing(18)
        # This line sets outer margins around the window content.
        main_layout.setContentsMargins(18, 18, 18, 18)
        # This line creates the left visual column.
        left_column = QVBoxLayout()
        # This line creates the header card above the preview.
        header_card = self.create_card()
        # This line creates the header layout.
        header_layout = QVBoxLayout()
        # This line creates the title label.
        self.title_label = QLabel("Aurora Hand Control")
        # This line marks the title for custom styling.
        self.title_label.setObjectName("TitleLabel")
        # This line creates the subtitle label.
        self.subtitle_label = QLabel("Camera-based mouse control with gesture overlays, safety lock, and tuning profiles.")
        # This line marks the subtitle for custom styling.
        self.subtitle_label.setObjectName("SubtitleLabel")
        # This line adds the title to the header layout.
        header_layout.addWidget(self.title_label)
        # This line adds the subtitle to the header layout.
        header_layout.addWidget(self.subtitle_label)
        # This line applies the header layout to the card.
        header_card.setLayout(header_layout)
        # This line creates the preview card.
        preview_card = self.create_card()
        # This line creates the preview layout.
        preview_layout = QVBoxLayout()
        # This line creates the preview label for the live camera feed.
        self.preview_label = QLabel("Camera preview will appear here.")
        # This line centers the preview placeholder text.
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # This line gives the preview panel a focused dark background.
        self.preview_label.setStyleSheet("background-color: #050a0f; color: #f0f0f0; border: 1px solid #334155; border-radius: 8px;")
        # This line ensures the preview expands nicely with the window.
        self.preview_label.setMinimumSize(900, 640)
        # This line adds the preview label to the preview card.
        preview_layout.addWidget(self.preview_label)
        # This line applies the preview layout to the preview card.
        preview_card.setLayout(preview_layout)
        # This line adds the header card to the left column.
        left_column.addWidget(header_card)
        # This line adds the preview card to the left column.
        left_column.addWidget(preview_card, 1)
        # This line creates the right-side column.
        right_column = QVBoxLayout()
        # This line creates the controls card.
        controls_card = self.create_card()
        # This line creates the controls layout.
        controls_layout = QVBoxLayout()
        # This line creates the start button.
        self.start_button = QPushButton("Start Tracking")
        # This line gives the start button a standard play icon.
        self.start_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        # This line explains the start button when the user hovers it.
        self.start_button.setToolTip("Start the webcam hand-tracking worker.")
        # This line creates the stop button.
        self.stop_button = QPushButton("Stop Tracking")
        # This line gives the stop button a standard stop icon.
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        # This line explains the stop button when the user hovers it.
        self.stop_button.setToolTip("Stop the camera worker and release any active drag.")
        # This line disables stop until the worker is running.
        self.stop_button.setEnabled(False)
        # This line creates the emergency stop button.
        self.emergency_button = QPushButton("Emergency Stop")
        # This line marks the emergency button for danger styling.
        self.emergency_button.setObjectName("DangerButton")
        # This line gives the emergency button a warning icon.
        self.emergency_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical))
        # This line explains the emergency button when the user hovers it.
        self.emergency_button.setToolTip("Immediately lock output control. Shortcut: Ctrl+Alt+X.")
        # This line creates the control lock button.
        self.lock_button = QPushButton("Lock Controls")
        # This line gives the lock button a standard cancel icon.
        self.lock_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        # This line explains the lock button when the user hovers it.
        self.lock_button.setToolTip("Toggle whether gestures can control the operating system.")
        # This line creates the setup check button.
        self.setup_button = QPushButton("Check Setup")
        # This line gives the setup button a standard information icon.
        self.setup_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        # This line explains the setup button when the user hovers it.
        self.setup_button.setToolTip("Check required packages and the hand landmarker model file.")
        # This line creates the control-enabled checkbox.
        self.controls_checkbox = QCheckBox("Enable OS Control")
        # This line creates the camera selection combo.
        self.camera_combo = QComboBox()
        # This line creates the operation profile selector.
        self.profile_combo = QComboBox()
        # This line creates the smoothing slider.
        self.smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        # This line creates the click cooldown slider.
        self.cooldown_slider = QSlider(Qt.Orientation.Horizontal)
        # This line creates the scroll sensitivity slider.
        self.scroll_slider = QSlider(Qt.Orientation.Horizontal)
        # This line creates the gesture status label.
        self.gesture_label = QLabel("Gesture: Idle")
        # This line marks the gesture label as a polished status pill.
        self.gesture_label.setObjectName("StatusPill")
        # This line creates the output status label.
        self.output_label = QLabel("Action: Idle")
        # This line marks the output label as a polished status pill.
        self.output_label.setObjectName("StatusPill")
        # This line creates the FPS status label.
        self.fps_label = QLabel("FPS: 0.0")
        # This line marks the FPS label as a polished status pill.
        self.fps_label.setObjectName("StatusPill")
        # This line creates the gesture strength status label.
        self.strength_label = QLabel("Strength: 0.00")
        # This line marks the strength label as a polished status pill.
        self.strength_label.setObjectName("StatusPill")
        # This line creates a visual strength meter for faster feedback.
        self.strength_bar = QProgressBar()
        # This line sets the strength meter range to percentages.
        self.strength_bar.setRange(0, 100)
        # This line hides the numeric text because the label already shows it.
        self.strength_bar.setTextVisible(False)
        # This line starts the strength meter empty.
        self.strength_bar.setValue(0)
        # This line creates the safety status label.
        self.safety_label = QLabel("Safety: Ready")
        # This line marks the safety label as the main control-state pill.
        self.safety_label.setObjectName("SafetyPill")
        # This line creates the setup status label.
        self.setup_label = QLabel("Setup: Not checked")
        # This line marks the setup label as a polished status pill.
        self.setup_label.setObjectName("StatusPill")
        # This line creates the control profile label.
        self.profile_label = QLabel("Profile: Balanced")
        # This line marks the profile label as a polished status pill.
        self.profile_label.setObjectName("StatusPill")
        # This line creates the gesture help panel.
        self.help_box = QTextEdit()
        # This line configures the smoothing slider range.
        self.smoothing_slider.setRange(5, 95)
        # This line configures the click cooldown slider range.
        self.cooldown_slider.setRange(10, 100)
        # This line configures the scroll sensitivity slider range.
        self.scroll_slider.setRange(100, 1600)
        # This line makes the help panel read-only.
        self.help_box.setReadOnly(True)
        # This line limits the help panel height so controls stay reachable.
        self.help_box.setMaximumHeight(190)
        # This line fills the help panel with the gesture guide.
        self.help_box.setPlainText("Gesture Guide\n\nOpen Palm: move cursor\nThumb + Index: left click\nThumb + Index while Middle is raised: drag\nThumb + Middle: right click\nTwo fingers raised and separated: swipe scroll\nTap Index + Middle fingertips together twice: play or pause\nThumb + Ring: precision hold\nClosed Fist: pause movement")
        # This line adds the available operation profiles.
        self.profile_combo.addItems(["Balanced", "Fast", "Precision", "Low Light"])
        # This line adds a friendly default camera list.
        for index in range(5):
            # This line adds a camera choice to the combo.
            self.camera_combo.addItem(f"Camera {index}", index)
        # This line creates the form layout for controls and settings.
        form_layout = QFormLayout()
        # This line adds the camera selector row.
        form_layout.addRow("Camera", self.camera_combo)
        # This line adds the operation profile row.
        form_layout.addRow("Profile", self.profile_combo)
        # This line adds the smoothing row.
        form_layout.addRow("Smoothing", self.smoothing_slider)
        # This line adds the click cooldown row.
        form_layout.addRow("Click Cooldown", self.cooldown_slider)
        # This line adds the scroll sensitivity row.
        form_layout.addRow("Scroll Sensitivity", self.scroll_slider)
        # This line adds the start button to the controls layout.
        controls_layout.addWidget(self.start_button)
        # This line adds the stop button to the controls layout.
        controls_layout.addWidget(self.stop_button)
        # This line adds the emergency button to the controls layout.
        controls_layout.addWidget(self.emergency_button)
        # This line adds the lock button to the controls layout.
        controls_layout.addWidget(self.lock_button)
        # This line adds the setup check button to the controls layout.
        controls_layout.addWidget(self.setup_button)
        # This line adds the controls checkbox to the controls layout.
        controls_layout.addWidget(self.controls_checkbox)
        # This line adds the form layout to the controls card.
        controls_layout.addLayout(form_layout)
        # This line adds the gesture label to the controls card.
        controls_layout.addWidget(self.gesture_label)
        # This line adds the action label to the controls card.
        controls_layout.addWidget(self.output_label)
        # This line adds the FPS label to the controls card.
        controls_layout.addWidget(self.fps_label)
        # This line adds the strength label to the controls card.
        controls_layout.addWidget(self.strength_label)
        # This line adds the strength meter to the controls card.
        controls_layout.addWidget(self.strength_bar)
        # This line adds the safety label to the controls card.
        controls_layout.addWidget(self.safety_label)
        # This line adds the setup label to the controls card.
        controls_layout.addWidget(self.setup_label)
        # This line adds the profile label to the controls card.
        controls_layout.addWidget(self.profile_label)
        # This line adds the gesture help box to the controls card.
        controls_layout.addWidget(self.help_box)
        # This line applies the controls layout to the card.
        controls_card.setLayout(controls_layout)
        # This line adds the controls card to the right column.
        right_column.addWidget(controls_card)
        # This line adds stretch so the right panel sits neatly.
        right_column.addStretch(1)
        # This line adds the left column to the main layout.
        main_layout.addLayout(left_column, 3)
        # This line adds the right column to the main layout.
        main_layout.addLayout(right_column, 1)
        # This line applies the main layout to the root widget.
        root.setLayout(main_layout)
        # This line makes the root widget the main window content.
        self.setCentralWidget(root)
        # This line connects the start button to system startup.
        self.start_button.clicked.connect(self.start_system)
        # This line connects the stop button to system shutdown.
        self.stop_button.clicked.connect(self.stop_system)
        # This line connects the emergency button to the toggle handler.
        self.emergency_button.clicked.connect(self.handle_emergency_stop)
        # This line connects the lock button to the control lock handler.
        self.lock_button.clicked.connect(self.toggle_control_lock)
        # This line connects the setup check button to the setup checker.
        self.setup_button.clicked.connect(self.check_setup)
        # This line connects the controls checkbox to settings persistence.
        self.controls_checkbox.toggled.connect(self.update_settings_from_ui)
        # This line connects the camera combo to settings persistence.
        self.camera_combo.currentIndexChanged.connect(self.update_settings_from_ui)
        # This line connects the profile combo to profile application.
        self.profile_combo.currentTextChanged.connect(self.apply_profile)
        # This line connects the smoothing slider to settings persistence.
        self.smoothing_slider.valueChanged.connect(self.update_settings_from_ui)
        # This line connects the cooldown slider to settings persistence.
        self.cooldown_slider.valueChanged.connect(self.update_settings_from_ui)
        # This line connects the scroll slider to settings persistence.
        self.scroll_slider.valueChanged.connect(self.update_settings_from_ui)
        # This line performs an initial setup check after the widgets exist.
        self.check_setup()

    # This method fills the widgets with the saved settings values.
    def populate_from_settings(self) -> None:
        # This line sets the control toggle from saved settings.
        self.controls_checkbox.setChecked(self.settings.controls_enabled)
        # This line selects the saved operation profile when available.
        self.profile_combo.setCurrentText(self.settings.control_profile)
        # This line selects the saved camera when it is in range.
        self.camera_combo.setCurrentIndex(max(0, min(self.settings.camera_index, self.camera_combo.count() - 1)))
        # This line converts the saved smoothing value into slider units.
        self.smoothing_slider.setValue(int(self.settings.smoothing * 100))
        # This line converts the saved cooldown into slider units.
        self.cooldown_slider.setValue(int(self.settings.click_cooldown * 100))
        # This line converts the saved scroll sensitivity into slider units.
        self.scroll_slider.setValue(int(self.settings.scroll_sensitivity))
        # This line refreshes the visible profile label.
        self.profile_label.setText(f"Profile: {self.settings.control_profile}")

    # This method reads widget state back into the shared settings object.
    def update_settings_from_ui(self) -> None:
        # This line stores the selected camera index.
        self.settings.camera_index = int(self.camera_combo.currentData())
        # This line stores the selected control profile.
        self.settings.control_profile = self.profile_combo.currentText()
        # This line stores the control toggle state.
        self.settings.controls_enabled = self.controls_checkbox.isChecked()
        # This line stores the smoothing value as a ratio.
        self.settings.smoothing = self.smoothing_slider.value() / 100.0
        # This line stores the click cooldown as seconds.
        self.settings.click_cooldown = self.cooldown_slider.value() / 100.0
        # This line stores the scroll sensitivity as a raw multiplier.
        self.settings.scroll_sensitivity = float(self.scroll_slider.value())
        # This line persists the updated settings to disk.
        save_settings(self.settings)
        # This line refreshes the visible profile label after saving.
        self.profile_label.setText(f"Profile: {self.settings.control_profile}")

    # This method applies a one-click operation profile to the tuning controls.
    def apply_profile(self, profile_name: str) -> None:
        # This line stores the selected profile name immediately.
        self.settings.control_profile = profile_name
        # This line applies the fast profile for lower lag and stronger movement.
        if profile_name == "Fast":
            # This line sets faster smoothing for the fast profile.
            self.smoothing_slider.setValue(68)
            # This line sets a shorter click cooldown for the fast profile.
            self.cooldown_slider.setValue(24)
            # This line sets stronger scrolling for the fast profile.
            self.scroll_slider.setValue(1500)
            # This line sets a smaller inference frame for the fast profile.
            self.settings.inference_scale = 0.58
        # This line applies the precision profile for steadier pointer use.
        elif profile_name == "Precision":
            # This line sets steadier smoothing for the precision profile.
            self.smoothing_slider.setValue(38)
            # This line sets a safer click cooldown for the precision profile.
            self.cooldown_slider.setValue(42)
            # This line sets gentler scrolling for the precision profile.
            self.scroll_slider.setValue(850)
            # This line keeps more inference detail for precision tracking.
            self.settings.inference_scale = 0.82
        # This line applies the low-light profile with more inference detail.
        elif profile_name == "Low Light":
            # This line sets moderate smoothing for low-light tracking.
            self.smoothing_slider.setValue(46)
            # This line sets a moderate click cooldown for low-light tracking.
            self.cooldown_slider.setValue(48)
            # This line sets moderate scroll sensitivity for low-light tracking.
            self.scroll_slider.setValue(1000)
            # This line uses a larger inference frame for weak camera detail.
            self.settings.inference_scale = 0.90
        # This line applies the balanced default profile.
        else:
            # This line sets balanced smoothing for everyday use.
            self.smoothing_slider.setValue(50)
            # This line sets balanced click cooldown for everyday use.
            self.cooldown_slider.setValue(32)
            # This line sets balanced scroll sensitivity for everyday use.
            self.scroll_slider.setValue(1250)
            # This line sets balanced inference size for everyday use.
            self.settings.inference_scale = 0.70
        # This line saves the new profile and slider settings.
        self.update_settings_from_ui()
        # This line updates the profile label.
        self.profile_label.setText(f"Profile: {profile_name}")

    # This method toggles the OS control checkbox from a large button.
    def toggle_control_lock(self) -> None:
        # This line flips the current OS control checkbox state.
        self.controls_checkbox.setChecked(not self.controls_checkbox.isChecked())
        # This line chooses the visible lock button text.
        button_text = "Lock Controls" if self.controls_checkbox.isChecked() else "Unlock Controls"
        # This line updates the lock button text.
        self.lock_button.setText(button_text)
        # This line updates the safety label for the new state.
        self.safety_label.setText("Safety: Controls Enabled" if self.controls_checkbox.isChecked() else "Safety: Controls Locked")

    # This method checks whether required runtime pieces are available.
    def check_setup(self) -> None:
        # This line checks whether the MediaPipe hand model is present.
        hand_model_ready = (MODELS_DIR / "hand_landmarker.task").exists()
        # This line checks whether OpenCV is importable.
        opencv_ready = importlib.util.find_spec("cv2") is not None
        # This line checks whether PyAutoGUI is importable.
        pyautogui_ready = importlib.util.find_spec("pyautogui") is not None
        # This line chooses the main setup status text.
        setup_text = "Ready" if hand_model_ready and opencv_ready and pyautogui_ready else "Needs model or package"
        # This line writes the setup status into the UI.
        self.setup_label.setText(f"Setup: {setup_text}")

    # This method starts the tracking worker thread.
    def start_system(self) -> None:
        # This line saves any latest UI changes before startup.
        self.update_settings_from_ui()
        # This line avoids starting a second worker when one is already running.
        if self.worker is not None and self.worker.isRunning():
            # This line exits because the worker is already active.
            return
        # This line creates a fresh worker thread for the current settings.
        self.worker = TrackingWorker(self.settings, self.controller)
        # This line connects preview updates from the worker.
        self.worker.frame_ready.connect(self.update_preview)
        # This line connects status updates from the worker.
        self.worker.status_ready.connect(self.update_status)
        # This line connects error messages from the worker.
        self.worker.error_ready.connect(self.show_error)
        # This line starts the worker thread.
        self.worker.start()
        # This line disables the start button while running.
        self.start_button.setEnabled(False)
        # This line enables the stop button while running.
        self.stop_button.setEnabled(True)
        # This line updates the safety label for startup.
        self.safety_label.setText("Safety: Running")

    # This method stops the tracking worker thread.
    def stop_system(self) -> None:
        # This line stops the worker when one exists.
        if self.worker is not None:
            # This line asks the worker loop to exit.
            self.worker.stop()
            # This line waits for the worker to finish cleanly.
            self.worker.wait(3000)
            # This line clears the worker reference.
            self.worker = None
        # This line re-enables the start button.
        self.start_button.setEnabled(True)
        # This line disables the stop button.
        self.stop_button.setEnabled(False)
        # This line updates the safety label for shutdown.
        self.safety_label.setText("Safety: Stopped")

    # This method toggles the emergency-stop controller state.
    def handle_emergency_stop(self) -> None:
        # This line flips the controller safety lock.
        self.controller.toggle_emergency_stop()
        # This line updates the visible safety label.
        self.safety_label.setText(f"Safety: {self.controller.last_output}")

    # This slot updates the preview image in the GUI.
    def update_preview(self, image: QImage) -> None:
        # This line converts the image into a pixmap for the label.
        pixmap = QPixmap.fromImage(image)
        # This line scales the pixmap to the current preview label size.
        scaled = pixmap.scaled(self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        # This line displays the scaled preview frame.
        self.preview_label.setPixmap(scaled)

    # This slot updates the textual status labels in the GUI.
    def update_status(self, payload: dict) -> None:
        # This line updates the gesture label.
        self.gesture_label.setText(f"Gesture: {payload['gesture']}")
        # This line updates the action label.
        self.output_label.setText(f"Action: {payload['output']}")
        # This line updates the FPS label.
        self.fps_label.setText(f"FPS: {payload['fps']}")
        # This line updates the gesture strength label.
        self.strength_label.setText(f"Strength: {payload['strength']}")
        # This line converts the strength text into a percentage value.
        strength_percent = int(float(payload["strength"]) * 100.0)
        # This line clamps the strength percentage into the meter range.
        strength_percent = max(0, min(100, strength_percent))
        # This line updates the visual gesture strength meter.
        self.strength_bar.setValue(strength_percent)
        # This line updates the safety label from the emergency-stop state.
        self.safety_label.setText("Safety: Emergency Stop Active" if payload["emergency_stop"] else "Safety: Running")

    # This slot shows a recoverable error message to the user.
    def show_error(self, message: str) -> None:
        # This line updates the safety label with the error state.
        self.safety_label.setText(f"Safety: {message}")
        # This line mirrors the error into the action label for visibility.
        self.output_label.setText(f"Action: {message}")

    # This method stops the worker before the window closes.
    def closeEvent(self, event) -> None:
        # This line stops the running worker before closing.
        self.stop_system()
        # This line accepts the close event.
        event.accept()


# This function starts the PySide6 application.
def run_app() -> None:
    # This line creates the Qt application object.
    app = QApplication([])
    # This line creates the main application window.
    window = MainWindow()
    # This line shows the main window on screen.
    window.show()
    # This line enters the GUI event loop.
    app.exec()
