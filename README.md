# Aurora Hand Control

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="PySide6" src="https://img.shields.io/badge/PySide6-Desktop%20GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white">
  <img alt="OpenCV" src="https://img.shields.io/badge/OpenCV-Realtime%20Camera-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white">
  <img alt="MediaPipe" src="https://img.shields.io/badge/MediaPipe-Hand%20Tracking-00A676?style=for-the-badge">
</p>

<p align="center">
  <b>A colorful Windows desktop app for controlling your PC with camera-based hand gestures.</b>
</p>

Aurora Hand Control uses a webcam, OpenCV, MediaPipe, PySide6, and PyAutoGUI to track your hand, draw live landmark lines, recognize gestures, and control basic mouse/media actions from a polished desktop interface.

## Features

- Live camera preview with hand skeleton lines, fingertip points, gesture labels, FPS, and action overlays.
- Smooth cursor movement with open-palm tracking and configurable sensitivity.
- Left click, right click, drag, scroll, play/pause, precision hold, and closed-fist pause gestures.
- Safety-first controls with an app lock, emergency stop button, and `Ctrl+Alt+X` shortcut.
- Simple control profiles: `Balanced`, `Fast`, `Precision`, and `Low Light`.
- Local settings stored in `data/settings.json` so your tuning is remembered.

## Project Structure

```text
  app.py
  requirements.txt
  README.md
  hand_control/
    config.py
    desktop_control.py
    gestures.py
    hand_tracking.py
    main_window.py
  models/
    hand_landmarker.task    
```

## Requirements

- Windows 10 or Windows 11.
- Python 3.12 or newer.
- A working webcam.
- The MediaPipe hand model file named `hand_landmarker.task`.

## Setup

Open PowerShell inside the project folder.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the app dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create the model folder if it does not already exist:

```powershell
New-Item -ItemType Directory -Force -Path models
```

Download `hand_landmarker.task` from Hugging Face:

Model page:

```text
https://huggingface.co/lithiumice/models_hub/blob/8a7b241f38e33d194a06f881a1211b3e7eda4edd/hand_landmarker.task
```

PowerShell download command:

```powershell
Invoke-WebRequest -Uri "https://huggingface.co/lithiumice/models_hub/resolve/8a7b241f38e33d194a06f881a1211b3e7eda4edd/hand_landmarker.task?download=true" -OutFile "models\hand_landmarker.task"
```

Run the app:

```powershell
python app.py
```

## How To Use

1. Start the app with `python app.py`.
2. Select your webcam from the `Camera` dropdown.
3. Choose a profile: `Balanced`, `Fast`, `Precision`, or `Low Light`.
4. Click `Check Setup`.
5. Keep `Enable OS Control` turned off while you test hand tracking.
6. Click `Start Tracking`.
7. Confirm that hand lines and fingertip points appear in the camera preview.
8. Turn on `Enable OS Control` only when the tracking feels stable.
9. Use `Emergency Stop` or `Ctrl+Alt+X` immediately if control becomes unstable.

## Gesture Guide

| Gesture                                                 | Action              |
| ------------------------------------------------------- | ------------------- |
| Open palm                                               | Move cursor         |
| Thumb + index pinch                                     | Left click          |
| Thumb + middle pinch                                    | Right click         |
| Thumb + index pinch while middle finger is raised       | Drag                |
| Two fingers raised and separated, then swipe up or down | Scroll              |
| Tap index and middle fingertips together twice          | Play or pause media |
| Thumb + ring pinch                                      | Precision hold      |
| Closed fist                                             | Pause movement      |

## Safety Notes

- Test with `Enable OS Control` off before allowing the app to move or click.
- Keep your hand fully visible in the camera frame for cleaner tracking.
- Use brighter lighting for fewer false gestures.
- Use `Emergency Stop` before changing camera position, lighting, or profiles.
- PyAutoGUI fail-safe is enabled, so moving the pointer to a screen corner can stop automation.

## Troubleshooting

Check whether the webcam opens:

```powershell
python -c "import cv2; cam=cv2.VideoCapture(0); print(cam.isOpened()); cam.release()"
```

Reinstall dependencies:

```powershell
python -m pip install -r requirements.txt
```

Check whether the model file exists:

```powershell
Get-Item ".\models\hand_landmarker.task"
```

Run a syntax check:

```powershell
python -m py_compile app.py hand_control\config.py hand_control\desktop_control.py hand_control\gestures.py hand_control\hand_tracking.py hand_control\main_window.py
```

## What To Upload To GitHub

Upload these files and folders:

- `.gitignore`
- `README.md`
- `requirements.txt`
- `app.py`
- `hand_control/`
- `models/README.md`

Do not upload these generated or local files:

- `.venv/`
- `__pycache__/`
- `*.pyc`
- `data/settings.json`
- `models/*.zip`
- `models/hand_landmarker.task`

Optional model note:

- You can upload `models/hand_landmarker.task` only if you want the repository to be fully offline-ready and the file size/license are acceptable for your GitHub repo.
- The cleaner GitHub option is to keep the model out of Git and use the download command above.

## GitHub Commands

Initialize Git:

```powershell
git init
```

Check files before committing:

```powershell
git status
```

Stage the project:

```powershell
git add .
```

Commit the first version:

```powershell
git commit -m "Initial Aurora Hand Control app"
```

Connect your GitHub repository:

```powershell
git remote add origin <your-github-repository-url>
```

Push to GitHub:

```powershell
git branch -M main
git push -u origin main
```

## License

Choose a license before publishing. MIT is a common choice for personal open-source desktop tools.
