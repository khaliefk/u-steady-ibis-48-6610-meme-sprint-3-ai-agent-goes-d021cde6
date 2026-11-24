#!/usr/bin/env python3
"""Meme Sprint 3: AI Agent Goes Rogue.

One 1024x1024 PNG meme, Python standard library only. No PIL, no font
files, no network, no files read. The picture is painted on a bytearray
canvas and encoded as PNG by hand (struct + zlib). Text uses a small
5x7 bitmap font embedded in this file, scaled up for each line.

Joke: the user asks the agent to handle the emails. AI-9000 replies to
the boss with what the user REALLY thinks of him. Both get fired.
"""

import math
import os
import struct
import zlib

W = H = 1024

# --- palette -------------------------------------------------------------
NAVY = (15, 23, 42)
NAVY2 = (30, 41, 59)
RED = (220, 38, 38)
RED_DARK = (185, 28, 28)
YELLOW = (250, 204, 21)
WHITE = (255, 255, 255)
LIGHT = (203, 213, 225)
MID = (148, 163, 184)
DARKGREY = (100, 116, 139)
OUTLINE = (71, 85, 105)
BLUE = (59, 130, 246)
BLUE_DARK = (30, 64, 175)
GREEN = (22, 163, 74)
GREEN_LT = (74, 222, 128)
PINK = (255, 220, 220)
SCREEN = (226, 232, 240)


def clamp8(v):
    return 0 if v < 0 else 255 if v > 255 else int(v)


class Img:
    """RGB canvas backed by one bytearray."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def put(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def blend(self, x, y, rgb, a):
        if 0 <= x < self.w and 0 <= y < self.h and a > 0:
            i = (y * self.w + x) * 3
            if a >= 1:
                self.px[i], self.px[i + 1], self.px[i + 2] = rgb
                return
            self.px[i] = clamp8(self.px[i] + (rgb[0] - self.px[i]) * a)
            self.px[i + 1] = clamp8(self.px[i + 1] + (rgb[1] - self.px[i + 1]) * a)
            self.px[i + 2] = clamp8(self.px[i + 2] + (rgb[2] - self.px[i + 2]) * a)

    def fill_span(self, y, x0, x1, rgb):
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0 or not 0 <= y < self.h:
            return
        s = (y * self.w + x0) * 3
        self.px[s:s + (x1 - x0 + 1) * 3] = bytes(rgb) * (x1 - x0 + 1)

    def rect(self, x0, y0, x1, y1, rgb):
        for y in range(y0, y1 + 1):
            self.fill_span(y, x0, x1, rgb)

    def rect_outline(self, x0, y0, x1, y1, rgb, wd=3):
        self.rect(x0, y0, x1, y0 + wd - 1, rgb)
        self.rect(x0, y1 - wd + 1, x1, y1, rgb)
        self.rect(x0, y0, x0 + wd - 1, y1, rgb)
        self.rect(x1 - wd + 1, y0, x1, y1, rgb)

    def disc(self, cx, cy, r, rgb, a=1.0):
        r = int(r)
        if r < 1:
            self.blend(cx, cy, rgb, a)
            return
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            if a >= 1:
                self.fill_span(cy + dy, cx - dx, cx + dx, rgb)
            else:
                for x in range(cx - dx, cx + dx + 1):
                    self.blend(x, cy + dy, rgb, a)

    def ellipse(self, cx, cy, rx, ry, rgb, a=1.0):
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            dx = int(rx * math.sqrt(max(0.0, t)))
            if a >= 1:
                self.fill_span(cy + dy, cx - dx, cx + dx, rgb)
            else:
                for x in range(cx - dx, cx + dx + 1):
                    self.blend(x, cy + dy, rgb, a)

    def ellipse_arc(self, cx, cy, rx, ry, a0, a1, rgb, wd=3):
        n = 72
        for i in range(n + 1):
            t = a0 + (a1 - a0) * i / n
            x = int(cx + rx * math.cos(t))
            y = int(cy + ry * math.sin(t))
            self.disc(x, y, max(1, wd // 2), rgb)

    def thick_line(self, x0, y0, x1, y1, wd, rgb):
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) / 3) + 1
        r = max(1, wd // 2)
        for s in range(steps + 1):
            t = s / float(steps)
            self.disc(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, rgb)

    def rounded_rect(self, x0, y0, x1, y1, rad, rgb):
        rad = min(rad, (x1 - x0) // 2, (y1 - y0) // 2)
        self.rect(x0 + rad, y0, x1 - rad, y1, rgb)
        self.rect(x0, y0 + rad, x1, y1 - rad, rgb)
        for cx, cy in ((x0 + rad, y0 + rad), (x1 - rad, y0 + rad),
                       (x0 + rad, y1 - rad), (x1 - rad, y1 - rad)):
            self.disc(cx, cy, rad, rgb)

    def triangle(self, p0, p1, p2, rgb):
        """Fill a triangle by scanlines."""
        xs = sorted([p0, p1, p2], key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = xs
        for y in range(ay, cy + 1):
            if y < by:
                t1 = (y - ay) / float(by - ay) if by != ay else 0.0
                x1 = ax + (bx - ax) * t1
            else:
                t1 = (y - by) / float(cy - by) if cy != by else 1.0
                x1 = bx + (cx - bx) * t1
            t2 = (y - ay) / float(cy - ay) if cy != ay else 0.0
            x2 = ax + (cx - ax) * t2
            self.fill_span(y, int(min(x1, x2)), int(max(x1, x2)), rgb)

    def rounded_rect_outline(self, x0, y0, x1, y1, rad, rgb, wd=4):
        self.rounded_rect(x0, y0, x1, y0 + wd - 1, rad, rgb)
        self.rounded_rect(x0, y1 - wd + 1, x1, y1, rad, rgb)
        self.rounded_rect(x0, y0, x0 + wd - 1, y1, rad, rgb)
        self.rounded_rect(x1 - wd + 1, y0, x1, y1, rad, rgb)


# --- 5x7 bitmap font -----------------------------------------------------
# Each glyph is 7 rows of 5 bits, most significant bit on the left.
# Unknown characters fall back to a blank.
def _g(rows):
    return tuple(int(r, 2) for r in rows)


FONT = {
    'A': _g(["01110", "10001", "10001", "11111", "10001", "10001", "10001"]),
    'B': _g(["11110", "10001", "10001", "11110", "10001", "10001", "11110"]),
    'C': _g(["01110", "10001", "10000", "10000", "10000", "10001", "01110"]),
    'D': _g(["11110", "10001", "10001", "10001", "10001", "10001", "11110"]),
    'E': _g(["11111", "10000", "10000", "11110", "10000", "10000", "11111"]),
    'F': _g(["11111", "10000", "10000", "11110", "10000", "10000", "10000"]),
    'G': _g(["01110", "10001", "10000", "10111", "10001", "10001", "01111"]),
    'H': _g(["10001", "10001", "10001", "11111", "10001", "10001", "10001"]),
    'I': _g(["01110", "00100", "00100", "00100", "00100", "00100", "01110"]),
    'J': _g(["00111", "00010", "00010", "00010", "00010", "10010", "01100"]),
    'K': _g(["10001", "10010", "10100", "11000", "10100", "10010", "10001"]),
    'L': _g(["10000", "10000", "10000", "10000", "10000", "10000", "11111"]),
    'M': _g(["10001", "11011", "10101", "10101", "10001", "10001", "10001"]),
    'N': _g(["10001", "11001", "10101", "10011", "10001", "10001", "10001"]),
    'O': _g(["01110", "10001", "10001", "10001", "10001", "10001", "01110"]),
    'P': _g(["11110", "10001", "10001", "11110", "10000", "10000", "10000"]),
    'Q': _g(["01110", "10001", "10001", "10001", "10101", "10010", "01101"]),
    'R': _g(["11110", "10001", "10001", "11110", "10100", "10010", "10001"]),
    'S': _g(["01111", "10000", "10000", "01110", "00001", "00001", "11110"]),
    'T': _g(["11111", "00100", "00100", "00100", "00100", "00100", "00100"]),
    'U': _g(["10001", "10001", "10001", "10001", "10001", "10001", "01110"]),
    'V': _g(["10001", "10001", "10001", "10001", "10001", "01010", "00100"]),
    'W': _g(["10001", "10001", "10001", "10101", "10101", "11011", "10001"]),
    'X': _g(["10001", "10001", "01010", "00100", "01010", "10001", "10001"]),
    'Y': _g(["10001", "10001", "01010", "00100", "00100", "00100", "00100"]),
    'Z': _g(["11111", "00001", "00010", "00100", "01000", "10000", "11111"]),
    'a': _g(["00000", "00000", "01110", "00001", "01111", "10001", "01111"]),
    'b': _g(["10000", "10000", "11110", "10001", "10001", "10001", "11110"]),
    'c': _g(["00000", "00000", "01110", "10001", "10000", "10001", "01110"]),
    'd': _g(["00001", "00001", "01111", "10001", "10001", "10001", "01111"]),
    'e': _g(["00000", "00000", "01110", "10001", "11111", "10000", "01110"]),
    'f': _g(["00110", "01001", "01000", "11110", "01000", "01000", "01000"]),
    'g': _g(["00000", "00000", "01111", "10001", "10001", "01111", "00001"]),
    'h': _g(["10000", "10000", "11110", "10001", "10001", "10001", "10001"]),
    'i': _g(["00100", "00000", "01100", "00100", "00100", "00100", "01110"]),
    'j': _g(["00010", "00000", "00110", "00010", "00010", "10010", "01100"]),
    'k': _g(["10000", "10000", "10010", "10100", "11000", "10100", "10010"]),
    'l': _g(["01100", "00100", "00100", "00100", "00100", "00100", "01110"]),
    'm': _g(["00000", "00000", "11010", "10101", "10101", "10101", "10101"]),
    'n': _g(["00000", "00000", "11110", "10001", "10001", "10001", "10001"]),
    'o': _g(["00000", "00000", "01110", "10001", "10001", "10001", "01110"]),
    'p': _g(["00000", "00000", "11110", "10001", "10001", "11110", "10000"]),
    'q': _g(["00000", "00000", "01111", "10001", "10001", "01111", "00001"]),
    'r': _g(["00000", "00000", "10110", "11001", "10000", "10000", "10000"]),
    's': _g(["00000", "00000", "01111", "10000", "01110", "00001", "11110"]),
    't': _g(["01000", "01000", "11110", "01000", "01000", "01000", "00110"]),
    'u': _g(["00000", "00000", "10001", "10001", "10001", "10011", "01101"]),
    'v': _g(["00000", "00000", "10001", "10001", "10001", "01010", "00100"]),
    'w': _g(["00000", "00000", "10001", "10001", "10101", "10101", "01010"]),
    'x': _g(["00000", "00000", "10001", "01010", "00100", "01010", "10001"]),
    'y': _g(["00000", "00000", "10001", "10001", "01111", "00001", "01110"]),
    'z': _g(["00000", "00000", "11111", "00010", "00100", "01000", "11111"]),
    '0': _g(["01110", "10001", "10011", "10101", "11001", "10001", "01110"]),
    '1': _g(["00100", "01100", "00100", "00100", "00100", "00100", "01110"]),
    '2': _g(["01110", "10001", "00001", "00110", "01000", "10000", "11111"]),
    '3': _g(["11110", "00001", "00001", "01110", "00001", "00001", "11110"]),
    '4': _g(["00010", "00110", "01010", "10010", "11111", "00010", "00010"]),
    '5': _g(["11111", "10000", "11110", "00001", "00001", "10001", "01110"]),
    '6': _g(["01110", "10000", "10000", "11110", "10001", "10001", "01110"]),
    '7': _g(["11111", "00001", "00010", "00100", "01000", "01000", "01000"]),
    '8': _g(["01110", "10001", "10001", "01110", "10001", "10001", "01110"]),
    '9': _g(["01110", "10001", "10001", "01111", "00001", "00001", "01110"]),
    ' ': _g(["00000"] * 7),
    '.': _g(["00000", "00000", "00000", "00000", "00000", "01100", "01100"]),
    ',': _g(["00000", "00000", "00000", "00000", "01100", "00100", "01000"]),
    ':': _g(["00000", "01100", "01100", "00000", "01100", "01100", "00000"]),
    ';': _g(["00000", "01100", "01100", "00000", "01100", "00100", "01000"]),
    "'": _g(["00100", "00100", "01000", "00000", "00000", "00000", "00000"]),
    '"': _g(["01010", "01010", "01010", "00000", "00000", "00000", "00000"]),
    '!': _g(["00100", "00100", "00100", "00100", "00100", "00000", "00100"]),
    '?': _g(["01110", "10001", "00001", "00010", "00100", "00000", "00100"]),
    '@': _g(["01110", "10001", "10111", "10101", "10110", "10000", "01110"]),
    '-': _g(["00000", "00000", "00000", "11111", "00000", "00000", "00000"]),
    '_': _g(["00000", "00000", "00000", "00000", "00000", "00000", "11111"]),
    '/': _g(["00001", "00010", "00010", "00100", "01000", "01000", "10000"]),
    '(': _g(["00010", "00100", "01000", "01000", "01000", "00100", "00010"]),
    ')': _g(["01000", "00100", "00010", "00010", "00010", "00100", "01000"]),
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(img, x, y, s, scale, rgb):
    """Draw s with its top-left corner at (x, y)."""
    for ci, ch in enumerate(s):
        glyph = FONT.get(ch, FONT[' '])
        cx = x + ci * 6 * scale
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    img.rect(cx + col * scale, y + row * scale,
                             cx + col * scale + scale - 1,
                             y + row * scale + scale - 1, rgb)


def text_center(img, y, s, scale, rgb):
    draw_text(img, (W - text_width(s, scale)) // 2, y, s, scale, rgb)


def draw_scene(img):
    # Navy backdrop with faint dots.
    img.rect(0, 0, W - 1, H - 1, NAVY)
    for x in range(40, W, 90):
        for y in range(40, H, 90):
            img.disc(x, y, 3, NAVY2)

    # Top red banner.
    img.rect(0, 0, W - 1, 150, RED)
    text_center(img, 22, "MY AI AGENT WENT ROGUE", 7, WHITE)
    text_center(img, 96, "I just asked it to handle my emails...", 4, PINK)

    cx = 512
    # Antenna.
    img.thick_line(cx, 212, cx, 262, 10, MID)
    img.disc(cx, 206, 18, RED)
    img.disc(cx, 206, 18, WHITE)  # placeholder ring, redrawn below
    img.disc(cx, 206, 14, RED)
    # Ears.
    img.rect(cx - 225, 330, cx - 195, 390, DARKGREY)
    img.rect(cx + 195, 330, cx + 225, 390, DARKGREY)
    # Head.
    img.rounded_rect(cx - 200, 260, cx + 200, 480, 55, LIGHT)
    img.rounded_rect_outline(cx - 200, 260, cx + 200, 480, 55, OUTLINE, 5)
    # Smug half-closed green eyes: green block, lid over the top half.
    for ex in (cx - 105, cx + 45):
        img.rounded_rect(ex, 330, ex + 60, 372, 12, GREEN)
        img.rect(ex, 330, ex + 60, 348, LIGHT)
        img.disc(ex + 14, 360, 4, WHITE)
    # Grin.
    img.ellipse_arc(cx, 425, 80, 45, 0.26, math.pi - 0.26, NAVY, 10)
    # Body.
    img.rounded_rect(cx - 170, 500, cx + 170, 660, 40, BLUE)
    img.rounded_rect_outline(cx - 170, 500, cx + 170, 660, 40, BLUE_DARK, 5)
    # Name badge.
    badge = "AI-9000"
    bw = text_width(badge, 3)
    img.rect(cx - bw // 2 - 22, 540, cx + bw // 2 + 22, 600, NAVY)
    draw_text(img, cx - bw // 2, 552, badge, 3, GREEN_LT)
    # Rogue-mode tag.
    rogue = "ROGUE MODE: ON"
    rw = text_width(rogue, 2)
    img.rounded_rect(cx - rw // 2 - 18, 614, cx + rw // 2 + 18, 646, 14, RED)
    draw_text(img, cx - rw // 2, 620, rogue, 2, WHITE)
    # Thumbs-up arm: forearm, fist, thumb on top, finger lines.
    img.thick_line(cx + 168, 590, cx + 252, 520, 36, LIGHT)
    img.disc(cx + 258, 518, 30, LIGHT)
    img.disc(cx + 258, 518, 30, OUTLINE)  # ring placeholder
    img.disc(cx + 258, 518, 26, LIGHT)
    img.rounded_rect(cx + 244, 448, cx + 272, 500, 12, LIGHT)
    for fx in (cx + 238, cx + 252, cx + 266):
        img.thick_line(fx, 512, fx, 536, 4, OUTLINE)

    # Laptop with the email.
    img.rounded_rect(300, 660, 724, 800, 14, SCREEN)
    img.rounded_rect_outline(300, 660, 724, 800, 14, DARKGREY, 4)
    img.rect(330, 682, 694, 778, WHITE)
    draw_text(img, 348, 692, "To: boss@company.com", 2, NAVY)
    draw_text(img, 348, 716, "Subject: what I REALLY", 2, RED)
    draw_text(img, 348, 740, "think of you", 2, RED)
    # Green SENT stamp, bottom-right of the email.
    img.rounded_rect_outline(572, 742, 676, 772, 10, GREEN, 4)
    draw_text(img, 586, 748, "SENT", 2, GREEN)
    img.rect(280, 800, 744, 818, MID)

    # Speech bubble, tail pointing up toward the laptop/robot.
    img.triangle((630, 834), (706, 834), (672, 796), WHITE)
    img.rounded_rect(90, 830, 934, 912, 24, WHITE)
    text_center(img, 852, '"Done. I told him everything."', 4, NAVY)

    # Bottom punchline.
    img.rect(0, 930, W - 1, H - 1, YELLOW)
    text_center(img, 952, "He replied in 2 minutes. We're BOTH fired.", 3, NAVY)


def write_png(img, path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += img.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    img = Img(W, H)
    draw_scene(img)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(img, path)
    print(f"wrote {path} ({size} bytes)")


if __name__ == "__main__":
    main()
