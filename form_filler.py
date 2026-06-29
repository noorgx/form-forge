"""
Box-based form filler with a small typed-field class hierarchy.

Each entry in fields.json has a "type" (default "text"). Adding a new box type
= subclass Field, implement render(), and register it in REGISTRY.

  Field (base: name, box, font/size/align inheritance, Arabic-or-English text)
   |-- TextField : one text value drawn in the box
   |-- DateField : an outer box + parts {day, month, year}, each a sub-box with
                   its own value. No hardcoded separator - each part is drawn
                   into the printed cell you placed it on. Parts inherit
                   font/size/align from the date field, which inherits from the
                   global defaults.

Config:
  { base_image, out_image, font, ink, default_size,
    fields: [
      { name, type:"text", box:[x0,y0,x1,y1], value, font?, size?, align? },
      { name, type:"date", box:[...], font?, size?, align?,
        parts: { day:{box,value,...}, month:{box,value,...}, year:{box,value,...} } }
    ] }

Run:  python form_filler.py [config.json]
"""
import json
import os
import sys
import unicodedata
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
from fontTools.ttLib import TTFont

_font_cache = {}
_cmap_cache = {}

FINAL_TO_ISOLATED = {
    0xFE8E: 0xFE8D, 0xFE82: 0xFE81, 0xFE84: 0xFE83, 0xFE88: 0xFE87,
    0xFE94: 0xFE93, 0xFEAA: 0xFEA9, 0xFEAC: 0xFEAB, 0xFEAE: 0xFEAD,
    0xFEB0: 0xFEAF, 0xFEEE: 0xFEED,
}


# --------------------------------------------------------------------------- #
# Text shaping / drawing helpers (shared by every field type)
# --------------------------------------------------------------------------- #
def get_font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


def font_cmap(path):
    if path not in _cmap_cache:
        _cmap_cache[path] = set(TTFont(path).getBestCmap().keys())
    return _cmap_cache[path]


def is_arabic(text):
    """True if text has an Arabic *letter* (digits/punctuation alone => LTR)."""
    for ch in text:
        o = ord(ch)
        if 0x0660 <= o <= 0x0669 or 0x06F0 <= o <= 0x06F9:
            continue
        if 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0xFB50 <= o <= 0xFEFF:
            return True
    return False


def _substitute(cp, cmap):
    if cp in cmap:
        return cp
    sib = FINAL_TO_ISOLATED.get(cp)
    if sib in cmap:
        return sib
    deco = unicodedata.decomposition(chr(cp))
    if deco:
        base = int(deco.split()[-1], 16)
        if base in cmap:
            return base
    return cp


def shape(text, font_path):
    if not is_arabic(text):
        return text
    reshaped = arabic_reshaper.reshape(text)
    cmap = font_cmap(font_path)
    reshaped = "".join(chr(_substitute(ord(c), cmap)) for c in reshaped)
    return get_display(reshaped)


def to_rgb(c, default):
    """Accept [r,g,b], '#rrggbb', or None -> fall back to default."""
    if c is None:
        return default
    if isinstance(c, (list, tuple)):
        return tuple(c[:3])
    if isinstance(c, str) and c.startswith("#") and len(c) == 7:
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return default


def draw_text_in_box(draw, box, value, font_path, size, ink, align=None):
    """Draw `value` (Arabic or English) inside `box`, vertically centered."""
    if not value:
        return
    if align is None:
        align = "right" if is_arabic(value) else "left"
    text = shape(value, font_path)
    font = get_font(font_path, size)
    x0, y0, x1, y1 = box
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    w, h = r - l, b - t
    if align == "right":
        x = x1 - w - l
    elif align == "center":
        x = x0 + ((x1 - x0) - w) // 2 - l
    else:
        x = x0 - l
    y = y0 + ((y1 - y0) - h) // 2 - t
    draw.text((x, y), text, font=font, fill=ink)


# --------------------------------------------------------------------------- #
# Field hierarchy
# --------------------------------------------------------------------------- #
class Context:
    """Global defaults a field inherits from."""
    def __init__(self, font, size, ink):
        self.font, self.size, self.ink = font, size, ink


class Field:
    type = "field"

    def __init__(self, data, ctx):
        self.data = data
        self.ctx = ctx
        self.name = data.get("name", "")
        self.box = data.get("box")

    # ---- inherited properties (field overrides global default) ----
    def font(self):
        return self.data.get("font", self.ctx.font)

    def size(self):
        return self.data.get("size", self.ctx.size)

    def align(self):
        return self.data.get("align")

    def color(self):
        return to_rgb(self.data.get("color"), self.ctx.ink)

    def render(self, draw, debug=False):
        raise NotImplementedError

    def _debug_box(self, draw, box, color=(255, 0, 0)):
        if debug_enabled and box:
            draw.rectangle(tuple(box), outline=color, width=1)


debug_enabled = False  # set per render() call


class TextField(Field):
    type = "text"

    def render(self, draw, debug=False):
        self._debug_box(draw, self.box)
        draw_text_in_box(draw, self.box, self.data.get("value", ""),
                         self.font(), self.size(), self.color(), self.align())


class DateField(Field):
    """Outer box (for grouping/selection) + parts placed inside it. Each part
    inherits font/size/align from the date field unless it overrides them."""
    type = "date"
    PARTS = ("day", "month", "year")

    def render(self, draw, debug=False):
        self._debug_box(draw, self.box, color=(0, 120, 255))
        parts = self.data.get("parts", {})
        for key in self.PARTS:
            p = parts.get(key)
            if not p or not p.get("box"):
                continue
            self._debug_box(draw, p["box"], color=(255, 140, 0))
            draw_text_in_box(
                draw, p["box"], p.get("value", ""),
                p.get("font", self.font()),
                p.get("size", self.size()),
                to_rgb(p.get("color"), self.color()),
                p.get("align", self.align() or "center"),
            )


class ChoiceField(Field):
    """Multiple options; the selected one gets a mark. You place each option's
    mark box; `mark` chooses what the mark looks like; `selected` is the key of
    the marked option.

      { name, type:"choice", mark:"x"|"check"|"circle"|"dot",
        selected:"male", box?:[...] (group),
        options:[ {key:"male", box:[...]}, {key:"female", box:[...]} ] }
    """
    type = "choice"

    def render(self, draw, debug=False):
        self._debug_box(draw, self.box, color=(0, 120, 255))
        mark = self.data.get("mark", "x")
        selected = self.data.get("selected")
        for opt in self.data.get("options", []):
            box = opt.get("box")
            if not box:
                continue
            self._debug_box(draw, box, color=(255, 140, 0))
            if opt.get("key") == selected:
                self._draw_mark(draw, box, mark)

    def _draw_mark(self, draw, box, mark):
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        ink = self.color()
        if mark == "circle":
            draw.ellipse(box, outline=ink, width=2)
        elif mark in ("dot", "fill"):
            draw.ellipse(box, fill=ink)
        elif mark == "check":
            draw.line([(x0 + w * 0.12, y0 + h * 0.55),
                       (x0 + w * 0.40, y1 - h * 0.12),
                       (x1 - w * 0.08, y0 + h * 0.10)],
                      fill=ink, width=2, joint="curve")
        else:  # "x"
            draw.line((x0, y0, x1, y1), fill=ink, width=2)
            draw.line((x0, y1, x1, y0), fill=ink, width=2)


class DigitsField(Field):
    """One glyph per evenly-spaced cell across the box (national ID, phone in
    boxes, etc.). `count` = number of cells; value fills left to right.

      { name, type:"digits", box:[x0,y0,x1,y1], count:14, value:"123…", color?, size? }
    """
    type = "digits"

    def render(self, draw, debug=False):
        self._debug_box(draw, self.box)
        value = str(self.data.get("value", ""))
        x0, y0, x1, y1 = self.box
        n = self.data.get("count") or len(value) or 1
        cell_w = (x1 - x0) / n
        cy = (y0 + y1) / 2
        ink = self.color()
        fpath, size = self.font(), self.size()
        font = get_font(fpath, size)
        if debug_enabled:
            for c in range(1, n):
                x = x0 + cell_w * c
                draw.line((x, y0, x, y1), fill=(255, 140, 0), width=1)
        for i, ch in enumerate(value[:n]):
            g = shape(ch, fpath)
            l, t, r, b = draw.textbbox((0, 0), g, font=font)
            cx = x0 + cell_w * (i + 0.5)
            draw.text((cx - (r - l) / 2 - l, cy - (b - t) / 2 - t), g, font=font, fill=ink)


REGISTRY = {cls.type: cls for cls in (TextField, DateField, ChoiceField, DigitsField)}


def make_field(data, ctx):
    return REGISTRY.get(data.get("type", "text"), TextField)(data, ctx)


# --------------------------------------------------------------------------- #
def render_dict(cfg, verbose=False):
    """Render from an in-memory config dict to cfg['out_image']."""
    global debug_enabled
    img = Image.open(cfg["base_image"]).convert("RGB")
    draw = ImageDraw.Draw(img)
    ctx = Context(cfg["font"], cfg.get("default_size", 22), tuple(cfg["ink"]))
    debug_enabled = cfg.get("debug_boxes", False)

    for data in cfg["fields"]:
        make_field(data, ctx).render(draw)

    os.makedirs(os.path.dirname(cfg["out_image"]) or ".", exist_ok=True)
    img.save(cfg["out_image"])
    if verbose:
        print(f"wrote {cfg['out_image']}  ({len(cfg['fields'])} fields)")
    return cfg["out_image"]


def render(config_path):
    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    return render_dict(cfg, verbose=True)


if __name__ == "__main__":
    render(sys.argv[1] if len(sys.argv) > 1 else "fields.json")
