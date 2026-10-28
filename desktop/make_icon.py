"""Draw the app icon (shield + check) -> desktop/assets/app.ico and app.png.
Generated at build time so no binary file needs to live in git."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "assets"


def draw(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256
    # rounded square background, indigo -> violet
    for y in range(size):
        t = y / size
        color = (int(99 + (139 - 99) * t), int(102 + (92 - 102) * t), int(241 + (246 - 241) * t), 255)
        d.line([(0, y), (size, y)], fill=color)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(56 * s), fill=255)
    img.putalpha(mask)
    # shield
    shield = [(128, 34), (206, 64), (200, 150), (128, 222), (56, 150), (50, 64)]
    d.polygon([(x * s, y * s) for x, y in shield], fill=(255, 255, 255, 240))
    # check mark
    d.line([(88 * s, 128 * s), (118 * s, 158 * s), (172 * s, 98 * s)], fill=(16, 185, 129, 255),
           width=max(int(20 * s), 2), joint="curve")
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    img = draw(256)
    img.save(OUT / "app.png")
    img.save(OUT / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Icon written to {OUT}")


if __name__ == "__main__":
    main()
