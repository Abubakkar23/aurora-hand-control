# This import starts the packaged desktop application.
from hand_control.main_window import run_app


# This guard keeps the launcher safe when the file is imported elsewhere.
if __name__ == "__main__":
    # This line starts the GUI application event loop.
    run_app()
