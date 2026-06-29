"""
Build FormTemplateEditor.exe with PyInstaller.

  python build_exe.py

Produces dist/FormTemplateEditor.exe (single file). Read-only resources
(index.html, base.jpeg, fonts, a starter fields.json) are bundled inside;
working files are created next to the .exe on first run.
"""
import os
import PyInstaller.__main__

os.chdir(os.path.dirname(os.path.abspath(__file__)))
SEP = ";"  # Windows add-data separator

PyInstaller.__main__.run([
    "app.py",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "FormTemplateEditor",
    "--add-data", f"index.html{SEP}.",
    "--add-data", f"base.jpeg{SEP}.",
    "--add-data", f"fields.json{SEP}.",
    "--add-data", f"fonts{SEP}fonts",
    "--collect-all", "webview",
])
