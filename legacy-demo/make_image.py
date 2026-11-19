#!/usr/bin/env python3
"""Ảnh minh hoạ cho bài viết về kịch bản 3.

Khác `spike/make_gallery.py`: ảnh đó dựng cho kịch bản 1 (lãi dồn, 4 bản ghi).
Bài viết nói về kịch bản 3 (Perl vs Java, 354 bản ghi) — dùng nhầm ảnh là để
con số trong ảnh cãi nhau với con số trong bài.

Và như mọi ảnh khác trong repo này: **số liệu lấy từ công cụ, không gõ tay.**

Chạy:  python3 make_image.py
"""

import os
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
OUT = "post-03.png"

BG    = (17, 21, 28)
PANEL = (12, 15, 20)
INK   = (233, 237, 243)
DIM   = (126, 137, 153)
RED   = (232, 94, 94)
AMBER = (226, 173, 74)
BLUE  = (99, 164, 232)
LINE  = (44, 52, 64)

MONO  = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONOB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANSB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
WIN = (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\consolab.ttf",
       r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf")
if not os.path.exists(MONO):
    MONO, MONOB, SANS, SANSB = WIN


def f(path, size):
    return ImageFont.truetype(path, size)


def report():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, os.path.join("..", "spike", "verify.py"),
                        "legacy_out.txt", "modern_out.txt", "schema.json",
                        "--lang=en"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env)
    return p.stdout.splitlines()


def main():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    d.text((40, 30), "Perl 2004 vs Java 21, same spec, 1,200 records",
           font=f(SANSB, 27), fill=INK)
    d.text((40, 68), "Two independent implementations. Nobody seeded a single "
                     "difference.", font=f(SANS, 17), fill=DIM)

    d.rectangle([32, 104, W - 32, H - 70], fill=PANEL)

    y = 120
    # 29 dòng là vừa khít khung; nhiều hơn thì chữ chạy đè lên dòng chú thích.
    for line in report()[:29]:
        col = INK
        if line.startswith("="):
            col = LINE
        elif "DO NOT SHIP" in line or "BUSINESS LOGIC" in line or "blocks" in line:
            col = RED
        elif "Rounding" in line or "sign-off" in line:
            col = AMBER
        elif line.startswith("  POL"):
            col = BLUE
        elif line.startswith("-") or line.startswith("  ..."):
            col = DIM
        d.text((52, y), line[:104], font=f(MONO, 15), fill=col)
        y += 17.5

    d.text((40, H - 56),
           "All 354 came from one sentence missing in the spec. "
           "Both programs read it correctly.",
           font=f(SANSB, 18), fill=AMBER)
    d.text((W - 32, H - 28), "trunkle.win", font=f(SANS, 15), fill=DIM,
           anchor="ra")

    im.save(OUT)
    print("ghi", OUT)


if __name__ == "__main__":
    main()
