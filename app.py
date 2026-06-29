"""
Desktop app for the Form Template Editor.

Runs the local server on a background thread and opens the editor in a native
desktop window. Works both as a plain script and as a PyInstaller .exe.

  python app.py            (development)
  FormTemplateEditor.exe   (packaged)

When packaged, read-only resources (index.html, base.jpeg, fonts) ship inside
the bundle, while the working files (fields.json, templates/, bases/, output/,
out/) live next to the .exe so they persist and stay editable.
"""
import os
import shutil
import sys
import threading
from http.server import ThreadingHTTPServer


def res_dir():
    """Bundled, read-only resources."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def data_dir():
    """Writable working folder: next to the .exe when frozen, else the script dir."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


RES = res_dir()
DATA = data_dir()


def _copy(name, overwrite):
    """Copy a bundled file into the working folder. overwrite=True for shipped
    resources (refresh every launch); False for user data (seed once)."""
    src, dst = os.path.join(RES, name), os.path.join(DATA, name)
    if os.path.abspath(src) == os.path.abspath(dst) or not os.path.exists(src):
        return
    if overwrite or not os.path.exists(dst):
        shutil.copy2(src, dst)


# Shipped UI resources: always refresh so a rebuilt app updates them.
_copy("index.html", overwrite=True)
_copy("base.jpeg", overwrite=True)

# Bundled fonts: merge in (keep any fonts the user added themselves).
os.makedirs(os.path.join(DATA, "fonts"), exist_ok=True)
_fsrc = os.path.join(RES, "fonts")
if os.path.isdir(_fsrc) and os.path.abspath(_fsrc) != os.path.abspath(os.path.join(DATA, "fonts")):
    for _fn in os.listdir(_fsrc):
        _s = os.path.join(_fsrc, _fn)
        if os.path.isfile(_s):
            shutil.copy2(_s, os.path.join(DATA, "fonts", _fn))

# User data: seed once, never overwrite.
_copy("fields.json", overwrite=False)
for _d in ("templates", "bases", "output", "out"):
    os.makedirs(os.path.join(DATA, _d), exist_ok=True)

os.environ["APP_ROOT"] = DATA      # template_tool resolves all paths under here
os.chdir(DATA)                     # form_filler uses cwd-relative font/base paths

import webview            # noqa: E402
import template_tool      # noqa: E402


def serve():
    ThreadingHTTPServer(("127.0.0.1", template_tool.PORT), template_tool.Handler).serve_forever()


def main():
    threading.Thread(target=serve, daemon=True).start()
    webview.create_window(
        "Form Template Editor",
        f"http://127.0.0.1:{template_tool.PORT}/",
        width=1240, height=920, min_size=(900, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
