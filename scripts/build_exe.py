"""
Build FormForge.exe with PyInstaller.

  python scripts/build_exe.py

Produces dist/FormForge.exe (single file). The UI is bundled inside; a
"workspace" folder for your data (fields.json, templates, fonts, output) is
created next to the .exe on first run, so keep the .exe in its own folder.
"""
import os
import PyInstaller.__main__

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
SEP = ";"  # Windows add-data separator

PyInstaller.__main__.run([
    "run.py",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "FormForge",
    "--paths", ".",
    "--add-data", f"formforge/web/index.html{SEP}formforge/web",
    "--collect-all", "webview",
])
