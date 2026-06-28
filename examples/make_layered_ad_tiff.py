"""Build the AURORA ad as a multi-page (layer-separated) TIFF -- portable.

Each page is a full-canvas RGBA image holding exactly one element on a
transparent background, so the pages map 1:1 to PSD layers.

Fonts are resolved by *role* (display / heavy / body) against a list of
candidate font files searched across several common font directories, so the
script runs on any machine. Set AD_FONT_DIR to add your own font folder.
"""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PIL.TiffImagePlugin import ImageFileDirectory_v2

W, H = 1080, 1350

# Directories searched for fonts, in order. The first is for Claude's cloud
# environment; the rest are common system locations on Linux/macOS/Windows.
FONT_DIRS = [
    os.environ.get("AD_FONT_DIR", ""),
    "/mnt/skills/examples/canvas-design/canvas-fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
    "/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "C:/Windows/Fonts",
]

# Each role lists candidate font files in preference order. Whatever is found
# first wins, so the design degrades gracefully to DejaVu (shipped with most
# Pillow installs) when the nicer display fonts are absent.
FONT_ROLES = {
    "display": [  # big condensed headline
        "BigShoulders-Bold.ttf", "Anton-Regular.ttf", "Oswald-Bold.ttf",
        "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf",
    ],
    "heavy": [  # bold sans for emphasis
        "Outfit-Bold.ttf", "Montserrat-Bold.ttf", "WorkSans-Bold.ttf",
        "DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf",
    ],
    "body": [  # regular bold body text
        "WorkSans-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial.ttf", "arial.ttf",
        "DejaVuSans.ttf",
    ],
}


def _find_font(candidates):
    for name in candidates:
        if os.path.isfile(name):  # absolute path given
            return name
        for directory in FONT_DIRS:
            if directory:
                path = os.path.join(directory, name)
                if os.path.isfile(path):
                    return path
    return None


def font(role, size):
    """Return a font for a logical role, falling back gracefully."""
    path = _find_font(FONT_ROLES[role])
    if path is not None:
        return ImageFont.truetype(path, size)
    # Last resort: Pillow's built-in bitmap font (size arg needs Pillow>=10.1).
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def new_layer():
    """Empty transparent full-canvas RGBA layer + its draw context."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def ctext(d, cx, y, text, fnt, fill):
    """Horizontally centered text."""
    w = d.textlength(text, font=fnt)
    d.text((cx - w / 2, y), text, font=fnt, fill=fill)


layers = []  # list of (name, RGBA image)

# --- 1. Background: diagonal gradient + soft decorative circles ---
top = np.array([255, 107, 74])
bot = np.array([138, 28, 92])
yy = np.linspace(0, 1, H)[:, None]
grad = (top * (1 - yy) + bot * yy).astype(np.uint8)
bg = Image.fromarray(np.repeat(grad[:, None, :], W, axis=1), "RGB").convert("RGBA")
deco = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dd = ImageDraw.Draw(deco)
dd.ellipse([140 - 220, 1180 - 220, 140 + 220, 1180 + 220], fill=(255, 255, 255, 18))
dd.ellipse([980 - 160, 250 - 160, 980 + 160, 250 + 160], fill=(255, 255, 255, 22))
bg = Image.alpha_composite(bg, deco)
layers.append(("Background", bg))

# --- 2. Logo ---
img, d = new_layer()
d.text((70, 70), "A U R O R A", font=font("heavy", 38), fill=(255, 255, 255, 235))
d.text((72, 120), "EST. 2014", font=font("body", 20), fill=(255, 255, 255, 170))
layers.append(("Logo", img))

# --- 3. Badge "50% OFF" ---
img, d = new_layer()
bx, by, br = 905, 250, 120
d.ellipse([bx - br, by - br, bx + br, by + br], fill=(255, 221, 87, 255))
ctext(d, bx, by - 70, "UP TO", font("body", 26), (90, 30, 60, 255))
ctext(d, bx, by - 44, "50%", font("display", 96), (90, 30, 60, 255))
ctext(d, bx, by + 40, "OFF", font("display", 54), (90, 30, 60, 255))
layers.append(("Badge", img))

# --- 4. Headline ---
img, d = new_layer()
d.text((68, 560), "SUMMER", font=font("display", 200), fill=(255, 255, 255, 255))
d.text((68, 750), "SALE", font=font("display", 200), fill=(255, 221, 87, 255))
layers.append(("Headline", img))

# --- 5. Subtitle ---
img, d = new_layer()
d.text((74, 980), "New-season essentials, handpicked for you.",
       font=font("heavy", 36), fill=(255, 255, 255, 235))
d.text((74, 1028), "Limited time only - while stocks last.",
       font=font("body", 28), fill=(255, 255, 255, 180))
layers.append(("Subtitle", img))

# --- 6. CTA button ---
img, d = new_layer()
btn = [74, 1110, 470, 1200]
d.rounded_rectangle(btn, radius=45, fill=(255, 255, 255, 255))
fnt = font("heavy", 40)
cta = "SHOP NOW  ->"
tw = d.textlength(cta, font=fnt)
d.text(((btn[0] + btn[2]) / 2 - tw / 2, btn[1] + 22), cta, font=fnt, fill=(170, 35, 90, 255))
layers.append(("CTA Button", img))

# --- 7. Footer ---
img, d = new_layer()
fft = font("body", 24)
d.text((74, 1270), "www.aurora-store.com", font=fft, fill=(255, 255, 255, 200))
ends = "Offer ends July 31"
fw = d.textlength(ends, font=fft)
d.text((W - 74 - fw, 1270), ends, font=fft, fill=(255, 255, 255, 200))
layers.append(("Footer", img))

# --- save as multi-page TIFF, tagging each page with its layer name ---
pages = []
for name, im in layers:
    # Store the layer name in the ImageDescription tag (270) so a converter
    # can recover it automatically.
    im.tag_v2 = ImageFileDirectory_v2()
    im.tag_v2[270] = name
    pages.append(im)
pages[0].save(
    "ad_layered.tiff",
    save_all=True,
    append_images=pages[1:],
    compression="tiff_lzw",
    dpi=(150, 150),
)
print("pages:", [name for name, _ in layers])

# --- flattened preview to confirm it composites to the original ad ---
flat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
for _, im in layers:
    flat = Image.alpha_composite(flat, im)
flat.convert("RGB").save("ad_layered_preview.png")
print("preview saved")
