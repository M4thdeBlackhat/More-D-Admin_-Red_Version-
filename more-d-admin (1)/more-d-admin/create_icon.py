"""
Run this script once to generate the assets/icon.ico file.
Requires: pip install pillow
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    os.makedirs("assets", exist_ok=True)
    sizes = [16, 32, 48, 64, 128, 256]
    imgs  = []

    for sz in sizes:
        img  = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle
        pad = max(1, sz // 16)
        draw.ellipse([pad, pad, sz - pad, sz - pad], fill=(10, 10, 10, 255))

        # Red ring
        ring = max(1, sz // 16)
        draw.ellipse([pad, pad, sz - pad, sz - pad],
                     outline=(204, 0, 0, 255), width=ring)

        # "M" letter
        font_sz = max(8, int(sz * 0.48))
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", font_sz)
        except Exception:
            font = ImageFont.load_default()

        text = "M"
        bbox  = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (sz - tw) // 2 - bbox[0]
        y = (sz - th) // 2 - bbox[1]
        draw.text((x, y), text, fill=(204, 0, 0, 255), font=font)

        imgs.append(img)

    imgs[0].save("assets/icon.ico", format="ICO", sizes=[(s, s) for s in sizes],
                 append_images=imgs[1:])
    print(f"✓ Created assets/icon.ico ({len(sizes)} sizes)")

if __name__ == "__main__":
    create_icon()
