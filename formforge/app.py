"""
Desktop app: runs the local server on a background thread and opens the editor
in a native window. Works as a script (python run.py) and as a PyInstaller exe.

Writable data lives in a "workspace" folder (next to the .exe when packaged, or
in the repo root from source), so the project tree stays clean.
"""
import os
import sys
import threading
from http.server import ThreadingHTTPServer


def data_dir():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
    d = os.path.join(base, "workspace")
    os.makedirs(d, exist_ok=True)
    return d


DATA = data_dir()
for _d in ("templates", "bases", "output", "out", "fonts"):
    os.makedirs(os.path.join(DATA, _d), exist_ok=True)
os.environ["APP_ROOT"] = DATA      # server resolves writable paths here
os.chdir(DATA)                     # renderer uses cwd-relative font/base paths

import webview            # noqa: E402
from . import server      # noqa: E402


def main():
    threading.Thread(
        target=lambda: ThreadingHTTPServer(("127.0.0.1", server.PORT), server.Handler).serve_forever(),
        daemon=True,
    ).start()
    webview.create_window(
        "Form Forge",
        f"http://127.0.0.1:{server.PORT}/",
        width=1240, height=920, min_size=(900, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
