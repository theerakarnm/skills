"""Build labeled contact sheets (run via: uv run --with pillow python _sheet.py DIR EVERY TILE PER_SHEET FONT)."""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

d, every, tile, per, font = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
frames = sorted(glob.glob(os.path.join(d, "f_*.jpg")))
fnt = ImageFont.truetype(font, max(14, tile // 9))
cols = 6
for s in range(0, len(frames), per):
    group = frames[s:s + per]
    ims = [Image.open(f).convert("RGB") for f in group]
    w = tile
    h = round(ims[0].height * tile / ims[0].width)
    rows = -(-len(ims) // cols)
    sheet = Image.new("RGB", (cols * (w + 4) + 4, rows * (h + 4) + 4), "black")
    for k, im in enumerate(ims):
        im = im.resize((w, h))
        t = (s + k) * every
        lab = f"{int(t // 60)}:{t % 60:04.1f}"
        dr = ImageDraw.Draw(im)
        bb = dr.textbbox((6, 6), lab, font=fnt)
        dr.rectangle((bb[0] - 4, bb[1] - 3, bb[2] + 4, bb[3] + 3), fill=(0, 0, 0))
        dr.text((6, 6), lab, font=fnt, fill=(255, 255, 255))
        sheet.paste(im, (4 + (k % cols) * (w + 4), 4 + (k // cols) * (h + 4)))
    sheet.save(os.path.join(d, f"sheet_{s // per + 1}.jpg"), quality=85)
print(f"{-(-len(frames) // per)} sheet(s)")
