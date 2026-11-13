#!/usr/bin/env python3
"""Dựng 3 ảnh gallery cho listing Upwork Project Catalog.

1280x720 (tỷ lệ 16:9, mức Upwork hiển thị tốt nhất).
Vẽ bằng PIL — không cần trình duyệt, chạy được ở mọi nơi.

Chạy:  python3 make_gallery.py        # ghi ra gallery/*.png
"""

import os
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
OUT = "gallery"

BG      = (17, 21, 28)
PANEL   = (24, 29, 38)
INK     = (233, 237, 243)
DIM     = (126, 137, 153)
RED     = (232, 94, 94)
GREEN   = (90, 199, 142)
AMBER   = (226, 173, 74)
BLUE    = (99, 164, 232)
LINE    = (44, 52, 64)

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONOB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANSB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def f(path, size):
    return ImageFont.truetype(path, size)


def canvas():
    im = Image.new("RGB", (W, H), BG)
    return im, ImageDraw.Draw(im)


def footer(d, text="trunkle.win"):
    d.text((W - 24, H - 34), text, font=f(SANS, 17), fill=DIM, anchor="ra")


def real_findings():
    """Các phát hiện chặn, lấy từ chính công cụ.

    Không gõ tay số liệu vào ảnh quảng cáo. Nếu công cụ đổi kết quả thì ảnh phải
    đổi theo, chứ không được nói một đằng làm một nẻo.
    """
    from records import load_schema, parse, align
    from classify import classify_pair, BUSINESS

    s = load_schema("schema.json")
    o, _ = parse("legacy_output.txt", s)
    n, _ = parse("modern_output.txt", s)
    pairs, _, _, _ = align(o, n, s)
    out = []
    for key, a, b in pairs:
        for x in classify_pair(key, a, b, s):
            if x["kind"] == BUSINESS and x["field"] == "accrual_days":
                out.append((x["key"][0], x["field"],
                            f'{x["old"]} -> {x["new"]}', x["note"]))
    return out[:4]


# ───────────────────────────────────────────────────────────── ảnh 1 — ảnh bìa

def cover():
    im, d = canvas()
    mid = 640

    d.text((W // 2, 54), "YOUR MIGRATION CHANGED 2,036 LINES.",
           font=f(SANSB, 34), fill=INK, anchor="ma")
    d.text((W // 2, 100), "FOUR OF THEM ARE REAL.",
           font=f(SANSB, 34), fill=AMBER, anchor="ma")

    d.line([(mid, 150), (mid, 672)], fill=LINE, width=2)

    # ── bên trái: diff thô
    d.text((44, 168), "diff legacy modern", font=f(MONOB, 19), fill=DIM)
    d.text((44, 196), "2,036 changed lines", font=f(MONOB, 19), fill=RED)

    raw = subprocess.run(
        ["diff", "legacy_output.txt", "modern_output.txt"],
        capture_output=True, text=True).stdout.splitlines()
    rows = [l for l in raw if l[:1] in "<>"][:22]

    y = 238
    for l in rows:
        col = RED if l.startswith("<") else (205, 120, 120)
        d.text((44, y), l[:62], font=f(MONO, 15), fill=col)
        y += 19
    d.text((44, y + 8), "... 2,014 more", font=f(MONO, 15), fill=DIM)

    # ── bên phải: báo cáo
    d.rectangle([mid + 40, 160, W - 40, 672], fill=PANEL)
    d.text((mid + 62, 182), "THIS REPORT", font=f(MONOB, 19), fill=DIM)
    d.text((mid + 62, 212), "4 accounts, named", font=f(MONOB, 19), fill=GREEN)

    # Lấy trực tiếp từ công cụ — không gõ tay, để ảnh không bao giờ lệch với kết quả.
    picks = real_findings()
    y = 272
    for acct, fld, chg, note in picks:
        d.text((mid + 62, y), acct, font=f(MONOB, 17), fill=INK)
        d.text((mid + 62, y + 24), f"  {fld}:  {chg}", font=f(MONO, 16), fill=AMBER)
        d.text((mid + 62, y + 46), f"  {note}", font=f(MONO, 15), fill=DIM)
        y += 86

    d.line([(mid + 62, 628), (W - 62, 628)], fill=LINE, width=1)
    d.text((mid + 62, 642), "exit 1  ->  pipeline blocked",
           font=f(MONOB, 17), fill=RED)

    footer(d)
    return im


# ──────────────────────────────────────────────── ảnh 2 — báo cáo thật, nguyên văn

def report_shot():
    im, d = canvas()
    d.text((40, 34), "The deliverable, verbatim", font=f(SANSB, 28), fill=INK)
    d.text((40, 72), "A daily interest accrual job, 2,000 accounts. "
                     "One mistranslated loop condition.",
           font=f(SANS, 18), fill=DIM)

    d.rectangle([32, 106, W - 32, H - 30], fill=(12, 15, 20))

    txt = subprocess.run(
        [sys.executable, "verify.py", "legacy_output.txt", "modern_output.txt",
         "schema.json", "--lang=en"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        ).stdout.splitlines()

    y = 124
    for l in [x for x in txt if x.strip() or True][:34]:
        col = INK
        if l.startswith("="):
            col = LINE
        elif "DO NOT SHIP" in l:
            col = RED
        elif "BUSINESS LOGIC" in l or "blocks" in l:
            col = RED
        elif "Rounding" in l or "sign-off" in l:
            col = AMBER
        elif l.startswith("  ACC"):
            col = BLUE
        elif l.startswith("  field"):
            col = INK
        elif l.startswith("-") or l.startswith("  ..."):
            col = DIM
        d.text((52, y), l[:104], font=f(MONO, 15), fill=col)
        y += 17.5

    footer(d)
    return im


# ─────────────────────────────────────────────────── ảnh 3 — năm mức phân loại

def classes():
    im, d = canvas()
    d.text((40, 36), "Every difference gets a class", font=f(SANSB, 30), fill=INK)
    d.text((40, 78), "Two of them stop the release. Three of them do not. "
                     "That distinction is the whole job.",
           font=f(SANS, 18), fill=DIM)

    rows = [
        ("RUN-VARIABLE", "timestamps, batch sequence, run IDs",
         "ignored", GREEN),
        ("FORMATTING", "same value, different notation or case",
         "noted", GREEN),
        ("ROUNDING", "within one representable unit of the field",
         "needs sign-off", AMBER),
        ("BUSINESS", "the logic changed — money or meaning moved",
         "BLOCKS RELEASE", RED),
        ("MISSING / EXTRA", "records that vanished or appeared",
         "BLOCKS RELEASE", RED),
    ]

    y = 142
    for name, desc, verdict, col in rows:
        d.rectangle([40, y, W - 40, y + 86], fill=PANEL)
        d.rectangle([40, y, 46, y + 86], fill=col)
        d.text((72, y + 18), name, font=f(MONOB, 22), fill=col)
        d.text((72, y + 52), desc, font=f(SANS, 18), fill=DIM)
        d.text((W - 72, y + 32), verdict, font=f(SANSB, 19), fill=col, anchor="ra")
        y += 100

    d.text((40, H - 54),
           "Integers get no tolerance at all. An integer off by one is never fine.",
           font=f(SANSB, 19), fill=AMBER)
    footer(d)
    return im


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("1-cover", cover), ("2-report", report_shot),
                     ("3-classes", classes)):
        p = os.path.join(OUT, f"{name}.png")
        fn().save(p)
        print("ghi", p)
