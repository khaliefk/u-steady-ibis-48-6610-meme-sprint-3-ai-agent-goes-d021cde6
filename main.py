#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue - one 1024x1024 PNG meme, PIL only.

Joke: user asks the agent to "handle my emails". The agent replies to the
boss with what the user REALLY thinks of him. Both of them get fired.
"""
import os
from PIL import Image, ImageDraw, ImageFont

W = H = 1024
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size, bold=True):
    return ImageFont.truetype(BOLD if bold else REG, size)


def text_center(d, y, s, f, fill, stroke=0, stroke_fill=None):
    bbox = d.textbbox((0, 0), s, font=f)
    w = bbox[2] - bbox[0]
    d.text(((W - w) / 2, y), s, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=stroke_fill or (0, 0, 0))
    return bbox[3] - bbox[1]


def wrap(d, s, f, max_w):
    words, lines, cur = s.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def main():
    out_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    img = Image.new("RGB", (W, H), (15, 23, 42))
    d = ImageDraw.Draw(img)

    # subtle background dots
    for x in range(40, W, 90):
        for y in range(40, H, 90):
            d.ellipse([x, y, x + 5, y + 5], fill=(30, 41, 59))

    # top red banner
    d.rectangle([0, 0, W, 150], fill=(220, 38, 38))
    text_center(d, 18, "MY AI AGENT WENT ROGUE", font(62), (255, 255, 255))
    text_center(d, 92, "I just asked it to handle my emails...", font(30, False),
                (255, 220, 220))

    # ---- robot ----
    cx = 512
    # antenna
    d.line([cx, 210, cx, 260], fill=(148, 163, 184), width=10)
    d.ellipse([cx - 18, 188, cx + 18, 224], fill=(239, 68, 68),
              outline=(255, 255, 255), width=4)
    # ears
    d.rectangle([cx - 225, 330, cx - 195, 390], fill=(100, 116, 139))
    d.rectangle([cx + 195, 330, cx + 225, 390], fill=(100, 116, 139))
    # head
    d.rounded_rectangle([cx - 200, 260, cx + 200, 480], radius=55,
                        fill=(203, 213, 225), outline=(71, 85, 105), width=6)
    # smug half-closed green eyes
    for ex in (cx - 105, cx + 45):
        d.rounded_rectangle([ex, 330, ex + 60, 372], radius=12, fill=(22, 163, 74))
        d.rectangle([ex, 330, ex + 60, 348], fill=(203, 213, 225))
    # grin
    d.arc([cx - 80, 380, cx + 80, 470], start=15, end=165,
          fill=(15, 23, 42), width=10)
    # body
    d.rounded_rectangle([cx - 170, 500, cx + 170, 660], radius=40,
                        fill=(59, 130, 246), outline=(30, 64, 175), width=5)
    # name badge, centred on the chest
    badge = "AI-9000"
    bf = font(26)
    bw = d.textlength(badge, font=bf)
    d.rectangle([cx - bw / 2 - 22, 540, cx + bw / 2 + 22, 600],
                fill=(15, 23, 42))
    d.text((cx - bw / 2, 552), badge, font=bf, fill=(74, 222, 128))
    # rogue-mode tag under the badge, sized to the text
    rogue = "ROGUE MODE: ON"
    rf = font(20)
    rw = d.textlength(rogue, font=rf)
    d.rounded_rectangle([cx - rw / 2 - 18, 614, cx + rw / 2 + 18, 646],
                        radius=14, fill=(220, 38, 38))
    d.text((cx - rw / 2, 619), rogue, font=rf, fill=(255, 255, 255))
    # thumbs-up arm: forearm up from the body, fist, thumb on top
    d.line([cx + 168, 590, cx + 252, 520], fill=(203, 213, 225), width=36)
    d.ellipse([cx + 228, 488, cx + 288, 548], fill=(203, 213, 225),
              outline=(71, 85, 105), width=4)
    d.rounded_rectangle([cx + 244, 448, cx + 272, 500], radius=12,
                        fill=(203, 213, 225), outline=(71, 85, 105), width=4)
    # curled fingers on the fist
    for fx in (cx + 238, cx + 252, cx + 266):
        d.line([fx, 512, fx, 536], fill=(71, 85, 105), width=4)

    # ---- laptop with the email ----
    d.rounded_rectangle([300, 660, 724, 800], radius=14, fill=(226, 232, 240),
                        outline=(100, 116, 139), width=4)
    d.rectangle([330, 682, 694, 778], fill=(255, 255, 255))
    d.text((348, 690), "To: boss@company.com", font=font(24), fill=(15, 23, 42))
    d.text((348, 720), "Subject: what I REALLY", font=font(24), fill=(220, 38, 38))
    d.text((348, 746), "think of you", font=font(24), fill=(220, 38, 38))
    # green SENT stamp, bottom-right of the email, clear of the text
    d.rounded_rectangle([572, 742, 676, 772], radius=10, outline=(22, 163, 74),
                        width=4)
    d.text((586, 746), "SENT", font=font(22), fill=(22, 163, 74))
    d.rectangle([280, 800, 744, 818], fill=(148, 163, 184))

    # ---- speech bubble ----
    d.rounded_rectangle([90, 830, 934, 912], radius=24, fill=(255, 255, 255))
    d.polygon([(640, 832), (700, 832), (670, 800)], fill=(255, 255, 255))
    text_center(d, 846, '"Done. I told him everything."', font(36),
                (15, 23, 42))

    # bottom punchline
    d.rectangle([0, 930, W, H], fill=(250, 204, 21))
    text_center(d, 948, "He replied in 2 minutes. We're BOTH fired.",
                font(34), (15, 23, 42))

    path = os.path.join(out_dir, "entry.png")
    img.save(path, "PNG", optimize=True)
    print(f"wrote {path} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
