# This import lets the module work with JSON settings files.
import json
# This import helps the module create lightweight data containers.
from dataclasses import asdict, dataclass
# This import gives path-safe file handling for the project folders.
from pathlib import Path

# This constant points to the project root folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# This constant points to the models folder for offline speech assets.
MODELS_DIR = PROJECT_ROOT / "models"
# This constant points to the data folder for runtime files.
DATA_DIR = PROJECT_ROOT / "data"
# This constant points to the persisted settings file.
SETTINGS_PATH = DATA_DIR / "settings.json"


# This data class stores the user-configurable application settings.
@dataclass
class AppSettings:
    # This field stores the selected camera index.
    camera_index: int = 0
    # This field stores the selected operation profile name.
    control_profile: str = "Balanced"
    # This field stores the requested camera width.
    camera_width: int = 800
    # This field stores the requested camera height.
    camera_height: int = 450
    # This field stores the downscale factor used before hand inference.
    inference_scale: float = 0.70
    # This field stores the cursor smoothing amount.
    smoothing: float = 0.50
    # This field stores extra responsiveness for large pointer jumps.
    motion_boost: float = 0.22
    # This field stores the click cooldown in seconds.
    click_cooldown: float = 0.32
    # This field stores the media gesture double-tap window in seconds.
    media_tap_window: float = 0.45
    # This field stores the scroll sensitivity multiplier.
    scroll_sensitivity: float = 1250.0
    # This field stores the screen-edge padding ratio.
    edge_padding: float = 0.08
    # This field stores the central dead-zone ratio.
    dead_zone: float = 0.04
    # This field stores whether mouse and key control is enabled.
    controls_enabled: bool = True


# This function ensures the project data folder exists.
def ensure_directories() -> None:
    # This line creates the models directory when it is missing.
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    # This line creates the data directory when it is missing.
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# This function builds a dictionary of default settings values.
def default_settings_payload() -> dict:
    # This line converts the default settings object into a dictionary.
    return asdict(AppSettings())


# This function loads settings from disk or returns defaults.
def load_settings() -> AppSettings:
    # This line makes sure the runtime folders exist before file access.
    ensure_directories()
    # This line returns defaults when no settings file exists yet.
    if not SETTINGS_PATH.exists():
        # This line creates a fresh default settings object.
        defaults = AppSettings()
        # This line writes the defaults to disk for user visibility.
        save_settings(defaults)
        # This line returns the default settings object.
        return defaults
    # This line opens the existing JSON settings file for reading.
    with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
        # This line parses the saved JSON into a dictionary.
        payload = json.load(handle)
    # This line builds the default settings dictionary for forward compatibility.
    merged_payload = default_settings_payload()
    # This line copies only known keys from disk into the merged payload.
    for key, value in payload.items():
        # This line checks whether the saved key still exists in the schema.
        if key in merged_payload:
            # This line updates the merged payload with the saved value.
            merged_payload[key] = value
    # This line returns the merged settings object.
    return AppSettings(**merged_payload)


# This function saves the settings object to disk.
def save_settings(settings: AppSettings) -> None:
    # This line makes sure the runtime folders exist before writing.
    ensure_directories()
    # This line opens the settings file for writing.
    with SETTINGS_PATH.open("w", encoding="utf-8") as handle:
        # This line writes the settings as readable JSON.
        json.dump(asdict(settings), handle, indent=2)
