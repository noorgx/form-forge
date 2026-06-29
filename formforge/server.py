"""
Local web server behind the editor and the desktop app.

Serves the UI (formforge/web/index.html), the base image, fonts and rendered
output, and a small JSON API to load/save fields and run renders.

The UI is a read-only package resource; all writable data (fields.json,
templates, bases, output) lives under the workspace folder. fields.json is the
single source of truth: the editor loads it and Save/Render write it back in the
flat shape the renderer reads.
"""
import base64
import hashlib
import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import renderer as form_filler
from . import batch

PKG = os.path.dirname(os.path.abspath(__file__))     # formforge package
WEB = os.path.join(PKG, "web")                        # bundled UI (read-only)
ROOT = os.environ.get("APP_ROOT") or os.path.join(os.path.dirname(PKG), "workspace")
FIELDS = os.path.join(ROOT, "fields.json")            # working template (single source)
TEMPLATES_DIR = os.path.join(ROOT, "templates")
BASES_DIR = os.path.join(ROOT, "bases")
OUTPUT_DIR = os.path.join(ROOT, "output")
PORT = 8000

for _d in (ROOT, TEMPLATES_DIR, BASES_DIR, OUTPUT_DIR, os.path.join(ROOT, "fonts")):
    os.makedirs(_d, exist_ok=True)


def _hash_bytes(b):
    return hashlib.sha1(b).hexdigest()[:16]


def file_hash(path):
    try:
        with open(path, "rb") as f:
            return _hash_bytes(f.read())
    except OSError:
        return None


def _safe_name(s):
    import re
    return re.sub(r"[^0-9A-Za-z._-]+", "_", (s or "untitled")).strip("_") or "untitled"


def load_template():
    """Single source of truth = fields.json. Return {meta, fields} where meta is
    everything except the fields list."""
    if not os.path.exists(FIELDS):
        return {"meta": {}, "fields": []}
    with open(FIELDS, encoding="utf-8") as f:
        flat = json.load(f)
    fields = flat.pop("fields", [])
    return {"meta": flat, "fields": fields}


def save_template(data):
    """Write {meta, fields} back to fields.json as a flat config (the same shape
    `python form_filler.py` reads). Returns the flat dict."""
    flat = dict(data.get("meta", {}))
    flat["fields"] = data.get("fields", [])
    flat.setdefault("base_image", "base.jpeg")
    flat.setdefault("out_image", "out/filled.png")
    with open(FIELDS, "w", encoding="utf-8") as f:
        json.dump(flat, f, ensure_ascii=False, indent=2)
    return flat


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body, ctype="application/octet-stream", nocache=False):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if nocache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json", nocache=True)

    def _file(self, relpath, ctype, nocache=False):
        path = os.path.join(ROOT, relpath)
        if not os.path.exists(path):
            return self._send(404, b"not found", "text/plain")
        with open(path, "rb") as f:
            self._send(200, f.read(), ctype, nocache)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            p = os.path.join(WEB, "index.html")
            if not os.path.exists(p):
                return self._send(404, b"not found", "text/plain")
            with open(p, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8", nocache=True)
        if path == "/base.jpeg":
            return self._file("base.jpeg", "image/jpeg")
        if path.startswith("/out/") or path.startswith("/bases/") or path.startswith("/output/"):
            rel = path.lstrip("/")
            ct = "image/png" if rel.endswith(".png") else "image/jpeg"
            return self._file(rel, ct, nocache=True)
        if path == "/api/template":
            return self._json(load_template())
        if path == "/api/templates":
            names = sorted(f[:-5] for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json"))
            return self._json({"templates": names})
        if path == "/api/fonts":
            fdir = os.path.join(ROOT, "fonts")
            fonts = []
            if os.path.isdir(fdir):
                for fn in sorted(os.listdir(fdir)):
                    if fn.lower().endswith((".ttf", ".otf")):
                        fonts.append({"label": os.path.splitext(fn)[0], "path": f"fonts/{fn}"})
            return self._json({"fonts": fonts})
        if path == "/api/load-template":
            name = self._query("name")
            p = os.path.join(TEMPLATES_DIR, _safe_name(name) + ".json")
            if not os.path.exists(p):
                return self._json({"ok": False, "error": "not found"}, 404)
            with open(p, encoding="utf-8") as f:
                flat = json.load(f)
            fields = flat.pop("fields", [])
            return self._json({"ok": True, "meta": flat, "fields": fields})
        self._send(404, b"not found", "text/plain")

    def _query(self, key):
        from urllib.parse import urlparse, parse_qs
        return (parse_qs(urlparse(self.path).query).get(key) or [""])[0]

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return self._json({"ok": False, "error": "bad json"}, 400)

        path = self.path.split("?")[0]
        if path == "/api/template":
            save_template(data)
            return self._json({"ok": True})

        if path == "/api/render":
            try:
                flat = save_template(data)          # working file = fields.json
                form_filler.render(FIELDS)
                return self._json({"ok": True, "fields": len(flat["fields"])})
            except Exception as e:
                traceback.print_exc()
                return self._json({"ok": False, "error": str(e)})

        if path == "/api/upload-base":
            try:
                raw = base64.b64decode(data["data_b64"])
                ext = os.path.splitext(data.get("filename", "base.png"))[1].lower() or ".png"
                h = _hash_bytes(raw)
                rel = f"bases/{h}{ext}"
                with open(os.path.join(ROOT, rel), "wb") as f:
                    f.write(raw)
                return self._json({"ok": True, "base_image": rel, "hash": h})
            except Exception as e:
                traceback.print_exc()
                return self._json({"ok": False, "error": str(e)})

        if path == "/api/save-template":
            name = _safe_name(data.get("name"))
            flat = dict(data.get("meta", {}))
            flat["fields"] = data.get("fields", [])
            flat["name"] = name
            flat["base_hash"] = file_hash(os.path.join(ROOT, flat.get("base_image", "base.jpeg")))
            with open(os.path.join(TEMPLATES_DIR, name + ".json"), "w", encoding="utf-8") as f:
                json.dump(flat, f, ensure_ascii=False, indent=2)
            save_template(data)   # also keep it as the working fields.json
            return self._json({"ok": True, "name": name})

        if path == "/api/xlsx-template":
            import openpyxl
            name = _safe_name(data.get("name"))
            wb = openpyxl.Workbook(); ws = wb.active; ws.title = "fill"
            ws.append(batch.fillable_columns(data.get("fields", [])))
            out = os.path.join(ROOT, name + "_fill.xlsx")
            wb.save(out)
            try:                                  # reveal the folder (desktop app)
                if hasattr(os, "startfile"):
                    os.startfile(ROOT)
            except Exception:
                pass
            return self._json({"ok": True, "file": name + "_fill.xlsx",
                               "folder": os.path.abspath(ROOT)})

        if path == "/api/generate":
            try:
                name = _safe_name(data.get("name"))
                meta = dict(data.get("meta", {}))
                fields = data.get("fields", [])
                xlsx = base64.b64decode(data["xlsx_b64"])
                xpath = os.path.join(OUTPUT_DIR, name + "_input.xlsx")
                with open(xpath, "wb") as f:
                    f.write(xlsx)
                out_dir = os.path.join(OUTPUT_DIR, name)
                made = batch.generate(meta, fields, xpath, out_dir)
                return self._json({"ok": True, "count": len(made),
                                   "folder": f"output/{name}",
                                   "files": [os.path.basename(m) for m in made]})
            except Exception as e:
                traceback.print_exc()
                return self._json({"ok": False, "error": str(e)})

        self._json({"ok": False, "error": "unknown endpoint"}, 404)


if __name__ == "__main__":
    os.chdir(ROOT)
    print(f"Form Forge running at  http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
