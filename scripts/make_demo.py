"""
Build assets/demo.gif: a generic sample form, the field boxes, and two filled
results. Uses a synthetic form so no real document is shown.

  python scripts/make_demo.py
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.chdir(REPO)
from formforge import renderer as form_filler  # noqa: E402

W, H = 680, 300
DEMO_BASE = "demo_base.png"
FONT = "workspace/fonts/PlaypenSansArabic.ttf"      # local font (not committed)
LABEL = "C:/Windows/Fonts/arial.ttf"
LABELB = "C:/Windows/Fonts/arialbd.ttf"

# Field geometry (shared by the drawn form and the template) ----------------
SERIAL = [W - 150, 40, W - 22, 66]
NAME = [120, 78, 420, 104]
DOB = {"day": [150, 120, 188, 146], "month": [196, 120, 234, 146], "year": [242, 120, 320, 146]}
IDB = [120, 162, 470, 190]
ID_CELLS = 10
GENDER = {"male": [120, 206, 138, 224], "female": [230, 206, 248, 224]}


def lf(sz, bold=False):
    return ImageFont.truetype(LABELB if bold else LABEL, sz)


def make_base():
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 30), fill=(30, 34, 51))
    d.text((16, 7), "REGISTRATION FORM", font=lf(15, True), fill="white")
    d.text((W - 150, 24), "Serial No.", font=lf(10), fill=(110, 110, 110))
    d.rectangle(SERIAL, outline=(150, 150, 150))
    d.text((20, 82), "Full Name", font=lf(12), fill=(60, 60, 60))
    d.line((120, 104, 420, 104), fill=(170, 170, 170))
    d.text((20, 124), "Date of Birth", font=lf(12), fill=(60, 60, 60))
    for b in DOB.values():
        d.rectangle(b, outline=(150, 150, 150))
    d.text((150, 148), "D D / M M / Y Y Y Y", font=lf(9), fill=(150, 150, 150))
    d.text((20, 167), "ID Number", font=lf(12), fill=(60, 60, 60))
    cw = (IDB[2] - IDB[0]) / ID_CELLS
    for i in range(ID_CELLS + 1):
        x = IDB[0] + cw * i
        d.line((x, IDB[1], x, IDB[3]), fill=(150, 150, 150))
    d.line((IDB[0], IDB[1], IDB[2], IDB[1]), fill=(150, 150, 150))
    d.line((IDB[0], IDB[3], IDB[2], IDB[3]), fill=(150, 150, 150))
    d.text((20, 208), "Gender", font=lf(12), fill=(60, 60, 60))
    d.rectangle(GENDER["male"], outline=(150, 150, 150))
    d.text((144, 207), "Male", font=lf(12), fill=(60, 60, 60))
    d.rectangle(GENDER["female"], outline=(150, 150, 150))
    d.text((254, 207), "Female", font=lf(12), fill=(60, 60, 60))
    d.text((16, H - 22), "FormForge", font=lf(11, True), fill=(180, 180, 190))
    im.save(DEMO_BASE)


def template(values, mark):
    return {
        "base_image": DEMO_BASE, "out_image": "_frame.png",
        "font": FONT, "ink": [25, 30, 90], "default_size": 20,
        "fields": [
            {"name": "serial", "type": "text", "box": SERIAL, "align": "center",
             "value": values.get("serial", ""), "font": "workspace/fonts/MailartRubberstamp.otf",
             "color": "#b3001b", "size": 18},
            {"name": "full_name", "type": "text", "box": NAME, "value": values.get("name", "")},
            {"name": "dob", "type": "date", "box": [150, 120, 320, 146], "align": "center", "size": 18,
             "parts": {k: {"box": DOB[k], "value": values.get(k, "")} for k in DOB}},
            {"name": "id_number", "type": "digits", "box": IDB, "count": ID_CELLS,
             "value": values.get("id", ""), "size": 18},
            {"name": "gender", "type": "choice", "mark": "x", "selected": values.get("gender"),
             "options": [{"key": k, "box": GENDER[k]} for k in GENDER]},
        ],
    }


def render_frame(values, out, debug=False):
    cfg = template(values, "x")
    cfg["out_image"] = out
    cfg["debug_boxes"] = debug
    form_filler.render_dict(cfg)
    return Image.open(out).convert("RGB").copy()


def main():
    make_base()
    blank = Image.open(DEMO_BASE).convert("RGB").copy()
    boxes = render_frame({}, "_f1.png", debug=True)
    a = render_frame({"serial": "100245", "name": "John Carter", "day": "05",
                      "month": "07", "year": "1990", "id": "9007051234", "gender": "male"}, "_f2.png")
    b = render_frame({"serial": "100246", "name": "احمد علي", "day": "21",
                      "month": "11", "year": "1988", "id": "8811210055", "gender": "female"}, "_f3.png")
    frames = [blank, boxes, a, b]
    durations = [900, 1600, 1700, 1700]
    os.makedirs("assets", exist_ok=True)
    frames[0].save("assets/demo.gif", save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, disposal=2)
    for f in ("_f1.png", "_f2.png", "_f3.png", DEMO_BASE):
        if os.path.exists(f):
            os.remove(f)
    print("wrote assets/demo.gif")


if __name__ == "__main__":
    main()
