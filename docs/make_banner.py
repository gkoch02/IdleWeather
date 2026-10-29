"""Render the README banner at docs/images/banner.png.

Idle Hours' own look: paper, black and the panel's red, Playfair Display, the
logo's rule and square. The frame on the right is `render_png()` for one pinned
rain quote in the `default` theme, scaled down from the panel's 800×480, so the
banner shows the real renderer. Deterministic: a fixed key, time and theme.

Usage:
    python3 docs/make_banner.py
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import idle_hours
from PIL import Image, ImageDraw, ImageFont

from idle_weather.pick import load_database
from idle_weather.render import DATABASE_PATH, find_row, render_png

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = REPO_ROOT / "docs" / "images" / "banner.png"
FONTS = Path(os.path.dirname(idle_hours.__file__)) / "fonts"

WIDTH, HEIGHT = 1600, 400
PAPER = (255, 255, 255)
INK = (0, 0, 0)
RED = (196, 30, 30)
QUOTE_KEY = "139:459:777"  # The Lost World: "a thin, cold rain is falling"
THEME = "default"
TIME = "10:00"


def font(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"PlayfairDisplay-{weight}.ttf"), size)


def frame() -> Image.Image:
    row = find_row(load_database(DATABASE_PATH), QUOTE_KEY)
    png = render_png(row, THEME, TIME, "production")
    image = Image.open(io.BytesIO(png)).convert("RGB")
    return image.resize((560, 336), Image.Resampling.LANCZOS)


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    panel = frame()
    px, py = WIDTH - panel.width - 60, (HEIGHT - panel.height) // 2
    draw.rectangle((px - 8, py - 8, px + panel.width + 8, py + panel.height + 8), fill=INK)
    image.paste(panel, (px, py))

    x = 80
    draw.text((x, 76), "Idle Weather", font=font(112), fill=INK)
    # The logo's rule and red square, under the wordmark.
    draw.rectangle((x + 4, 214, x + 604, 217), fill=INK)
    draw.rectangle((x + 612, 206, x + 630, 224), fill=RED)
    draw.text((x + 4, 240), "the weather outside, as a novelist put it", font=font(36, "Medium"), fill=INK)
    draw.text((x + 4, 298), "Open-Meteo  ·  Idle Hours' themes  ·  an Inky Impression on a Raspberry Pi",
              font=font(24, "Regular"), fill=INK)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT_PATH, optimize=True)
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} ({WIDTH}×{HEIGHT})")


if __name__ == "__main__":
    main()
