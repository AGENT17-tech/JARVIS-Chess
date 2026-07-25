"""
One-off generator for the JARVIS Chess app icon/branding assets.
Run with: python scripts/generate_icon.py
Regenerates public/icon.png, public/favicon.ico, public/logo192.png, public/logo512.png.

Not part of the build pipeline - the icon rarely changes, so this is a manual
tool rather than a build step.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(HERE, "..", "public")

# Matches theme.js's dark-mode accentBlue family, since the icon is the app's
# permanent "brand" and shouldn't flip with the user's light/dark preference.
BLUE_DARK = (17, 39, 90)
BLUE_MID = (30, 64, 175)
BLUE_LIGHT = (59, 130, 246)
WHITE = (255, 255, 255)

FONT_PATH = r"C:\Windows\Fonts\seguisym.ttf"
KNIGHT_GLYPH = "\u265E"  # black chess knight - renders as a solid glyph in Segoe UI Symbol


def make_master(size=1024):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Radial-ish gradient background disc (top-left lighter -> bottom-right darker)
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(bg)
    for y in range(size):
        t = y / size
        r = int(BLUE_LIGHT[0] + (BLUE_DARK[0] - BLUE_LIGHT[0]) * t)
        g = int(BLUE_LIGHT[1] + (BLUE_DARK[1] - BLUE_LIGHT[1]) * t)
        b = int(BLUE_LIGHT[2] + (BLUE_DARK[2] - BLUE_LIGHT[2]) * t)
        d.line([(0, y), (size, y)], fill=(r, g, b, 255))

    # Rounded-square mask (modern app-icon shape, not a hard square or circle)
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    radius = int(size * 0.22)
    md.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    img.paste(bg, (0, 0), mask)

    draw = ImageDraw.Draw(img, "RGBA")

    # Subtle circuit-trace accents in the corners - thin lines + node dots,
    # kept low-opacity and away from the center so they read as texture at
    # large sizes and disappear cleanly at 16-32px rather than turning to noise.
    def circuit(x0, y0, dx, dy, segments):
        x, y = x0, y0
        pts = [(x, y)]
        for i in range(segments):
            if i % 2 == 0:
                x += dx
            else:
                y += dy
            pts.append((x, y))
        draw.line(pts, fill=(255, 255, 255, 60), width=max(2, size // 200))
        for px, py in pts[::2]:
            r = size // 90
            draw.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, 90))

    step = size * 0.09
    circuit(size * 0.08, size * 0.14, step, step * 0.7, 5)
    circuit(size * 0.92, size * 0.86, -step, -step * 0.7, 5)

    # Knight glyph, centered, scaled to fill most of the badge
    font_size = int(size * 0.62)
    font = ImageFont.truetype(FONT_PATH, font_size)
    bbox = draw.textbbox((0, 0), KNIGHT_GLYPH, font=font)
    gw, gh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    gx = (size - gw) / 2 - bbox[0]
    gy = (size - gh) / 2 - bbox[1]

    # Soft drop shadow for depth, then the glyph itself in white
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    offset = size * 0.012
    sd.text((gx + offset, gy + offset * 2.2), KNIGHT_GLYPH, font=font, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.01))
    img.alpha_composite(shadow)

    draw.text((gx, gy), KNIGHT_GLYPH, font=font, fill=WHITE)

    return img


def main():
    master = make_master(1024)

    os.makedirs(PUBLIC, exist_ok=True)

    master.resize((256, 256), Image.LANCZOS).save(os.path.join(PUBLIC, "icon.png"))
    master.resize((192, 192), Image.LANCZOS).save(os.path.join(PUBLIC, "logo192.png"))
    master.resize((512, 512), Image.LANCZOS).save(os.path.join(PUBLIC, "logo512.png"))

    ico_sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
    master.save(os.path.join(PUBLIC, "favicon.ico"), sizes=ico_sizes)

    print("Wrote icon.png, logo192.png, logo512.png, favicon.ico to", PUBLIC)


if __name__ == "__main__":
    main()
