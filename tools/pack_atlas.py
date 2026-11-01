# Simple shelf packer -> Spine 4.x .atlas + png pages (no rotation, no trim; images pre-trimmed).
import sys, os
from PIL import Image
img_dir, out_dir, name = sys.argv[1:4]
MAXW, MAXH, PAD = 2048, 2048, 2
files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".png"))
ims = [(f[:-4], Image.open(os.path.join(img_dir, f)).convert("RGBA")) for f in files]
ims.sort(key=lambda t: (-t[1].size[1], -t[1].size[0]))
pages, cur, x, y, rowh = [], [], 0, 0, 0
for n, im in ims:
    w, h = im.size
    if x + w > MAXW: x, y, rowh = 0, y + rowh + PAD, 0
    if y + h > MAXH:
        pages.append(cur); cur, x, y, rowh = [], 0, 0, 0
    cur.append((n, im, x, y)); x += w + PAD; rowh = max(rowh, h)
pages.append(cur)
lines = []
for pi, pg in enumerate(pages):
    H = max(yy + im.size[1] for _, im, _, yy in pg)
    PH = 1
    while PH < H: PH *= 2
    pname = f"{name}.png" if len(pages) == 1 else f"{name}_{pi + 1}.png"
    sheet = Image.new("RGBA", (MAXW, PH), (0, 0, 0, 0))
    if lines: lines.append("")
    lines += [pname, f"size:{MAXW},{PH}", "filter:Linear,Linear"]
    for n, im, xx, yy in sorted(pg, key=lambda t: t[0]):
        sheet.paste(im, (xx, yy))
        lines += [n, f"bounds:{xx},{yy},{im.size[0]},{im.size[1]}"]
    sheet.save(os.path.join(out_dir, pname), optimize=True)
    print(pname, MAXW, PH, len(pg))
open(os.path.join(out_dir, name + ".atlas"), "w").write("\n".join(lines) + "\n")
