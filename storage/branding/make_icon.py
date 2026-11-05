"""Render TT Content Publisher app icon (1024x1024 PNG, no transparency)."""
import sys
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1]
SS = 4                      # supersampling factor
S = 1024 * SS

TOP = (67, 56, 202)         # indigo
BOTTOM = (124, 58, 237)     # violet
ACCENT = (251, 146, 60)     # amber-orange
WHITE = (255, 255, 255)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


# Diagonal gradient background
grad = Image.new("RGB", (2, 2))
grad.putpixel((0, 0), TOP)
grad.putpixel((1, 0), lerp(TOP, BOTTOM, 0.5))
grad.putpixel((0, 1), lerp(TOP, BOTTOM, 0.5))
grad.putpixel((1, 1), BOTTOM)
img = grad.resize((S, S), Image.BILINEAR)

# Soft shadow under the video card
DX, DY = -70, -50           # shift whole group so card + badge sit centred
card = ((300 + DX) * SS, (190 + DY) * SS, (680 + DX) * SS, (830 + DY) * SS)
shadow = Image.new("L", (S, S), 0)
ImageDraw.Draw(shadow).rounded_rectangle(
    [card[0] + 20 * SS, card[1] + 30 * SS, card[2] + 20 * SS, card[3] + 30 * SS],
    radius=70 * SS, fill=90,
)
shadow = shadow.filter(ImageFilter.GaussianBlur(30 * SS))
img.paste((30, 20, 90), (0, 0), shadow)

d = ImageDraw.Draw(img)

# Portrait video card (9:16-ish)
d.rounded_rectangle(card, radius=70 * SS, fill=WHITE)

# Play triangle in card centre
cx, cy = (card[0] + card[2]) // 2 + 14 * SS, (card[1] + card[3]) // 2 - 10 * SS
r = 105 * SS
d.polygon(
    [(cx - r * 0.75, cy - r), (cx - r * 0.75, cy + r), (cx + r, cy)],
    fill=lerp(TOP, BOTTOM, 0.5),
)

# Upload badge (bottom-right), ring in background colour to separate from card
bx, by, br = (690 + DX) * SS, (760 + DY) * SS, 150 * SS
ring = 22 * SS
d.ellipse([bx - br - ring, by - br - ring, bx + br + ring, by + br + ring],
          fill=grad.resize((S, S), Image.BILINEAR).getpixel((bx, by)))
d.ellipse([bx - br, by - br, bx + br, by + br], fill=ACCENT)

# Up arrow, vertically centred in badge (spans by-80 .. by+80)
w = 26 * SS
d.rounded_rectangle([bx - w, by - 10 * SS, bx + w, by + 80 * SS], radius=w // 2, fill=WHITE)
d.polygon(
    [(bx, by - 80 * SS), (bx - 78 * SS, by + 10 * SS), (bx + 78 * SS, by + 10 * SS)],
    fill=WHITE,
)

img.resize((1024, 1024), Image.LANCZOS).save(OUT, "PNG", optimize=True)
print(OUT)
