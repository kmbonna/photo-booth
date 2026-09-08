import os
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from modules import moods, log
logger = log.get(__name__)

# Strip canvas
STRIP_W  = 900
PHOTO_W  = 840   # 30px margin each side
PHOTO_H  = 630   # 4:3 crop
GAP      = 16
TOP_PAD  = 40
BOTTOM_H = 90
BOT_PAD  = 30

# STRIP_H is computed inside compose() based on PHOTOS_PER_SESSION

# Per-mood strip palettes: (background, frame/accent, text)
_PALETTES = {
    'default': ((247, 240, 227), (160,  82,  45), ( 59,  42,  26)),
    'noir':    (( 18,  18,  18), (200, 200, 200), (220, 220, 220)),
    '70s':     ((228, 195, 140), (185,  95,  35), ( 75,  40,  10)),
}


def _font(size, bold=False):
    candidates = [
        'arialbd.ttf'  if bold else 'arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'    if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _crop_center(img, tw, th):
    """Center-crop img to target aspect ratio, then resize."""
    sw, sh = img.size
    t_ratio = tw / th
    s_ratio = sw / sh
    if s_ratio > t_ratio:          # too wide
        nw = int(sh * t_ratio)
        img = img.crop(((sw - nw) // 2, 0, (sw - nw) // 2 + nw, sh))
    elif s_ratio < t_ratio:        # too tall
        nh = int(sw / t_ratio)
        img = img.crop((0, (sh - nh) // 2, sw, (sh - nh) // 2 + nh))
    return img.resize((tw, th), Image.LANCZOS)


def _polaroid_border(photo):
    """Wrap photo in a worn Polaroid-style border — aged cream, unique imperfections each time."""
    PL, PR, PT, PB = 14, 14, 12, 50          # left, right, top, bottom border widths
    inner_w = PHOTO_W - PL - PR               # 812
    inner_h = PHOTO_H - PT - PB               # 568

    inner = photo.resize((inner_w, inner_h), Image.LANCZOS)

    # Aged cream base — warm, not pure white
    base = np.array([248, 241, 225], dtype=np.float32)
    arr  = np.broadcast_to(base, (PHOTO_H, PHOTO_W, 3)).copy()

    # Fine grain/texture across the whole border
    arr += np.random.normal(0, 6, arr.shape)

    # Corner aging — yellowed and slightly dingy at the corners
    yy, xx = np.mgrid[0:PHOTO_H, 0:PHOTO_W].astype(np.float32)
    age = np.zeros((PHOTO_H, PHOTO_W), dtype=np.float32)
    for cy, cx in [(0, 0), (0, PHOTO_W-1), (PHOTO_H-1, 0), (PHOTO_H-1, PHOTO_W-1)]:
        dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
        age += np.clip(1 - dist / 110, 0, 1)
    age = np.clip(age, 0, 1)[:, :, np.newaxis]
    arr[:, :, 0:1] += age * 14    # more red
    arr[:, :, 1:2] += age * 4     # slight green
    arr[:, :, 2:3] -= age * 28    # less blue → warm yellowing

    # Outer edge wear — subtle darkening at the very border edges
    fade_px = 10
    for i in range(fade_px):
        s = ((fade_px - i) / fade_px) ** 2 * 22
        arr[i, :]            -= s
        arr[PHOTO_H - 1 - i, :] -= s
        arr[:, i]            -= s
        arr[:, PHOTO_W - 1 - i] -= s

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    bordered = Image.fromarray(arr)
    bordered.paste(inner, (PL, PT))

    # Random fine scratches — only on the border, not the photo
    draw = ImageDraw.Draw(bordered)
    rng  = np.random.default_rng()
    for _ in range(int(rng.integers(2, 6))):
        side = int(rng.integers(4))
        if side == 0:    sx, sy = int(rng.integers(0, PHOTO_W)),     int(rng.integers(0, PT))
        elif side == 1:  sx, sy = int(rng.integers(0, PHOTO_W)),     int(rng.integers(PT + inner_h, PHOTO_H))
        elif side == 2:  sx, sy = int(rng.integers(0, PL)),          int(rng.integers(0, PHOTO_H))
        else:            sx, sy = int(rng.integers(PL + inner_w, PHOTO_W)), int(rng.integers(0, PHOTO_H))
        length = int(rng.integers(10, 55))
        dx     = int(rng.integers(-length, length + 1))
        dy     = int(rng.integers(-2, 3))
        c      = int(rng.integers(185, 225))
        draw.line([(sx, sy), (sx + dx, sy + dy)], fill=(c, c - 6, c - 18), width=1)

    # Subtle inner shadow where border meets photo — makes it feel inset
    draw.rectangle([PL, PT, PL + inner_w - 1, PT + inner_h - 1],
                   outline=(178, 162, 138), width=1)

    return bordered


def compose(session_id, mood='default'):
    """Build the 4-photo strip and save it as strip.jpg in the session folder."""
    base = os.environ.get('SESSIONS_DIR') or os.path.join(os.path.dirname(__file__), '..', 'sessions')
    session_dir = os.path.normpath(os.path.join(base, session_id))

    BG, ACCENT, TEXT = _PALETTES.get(mood, _PALETTES['default'])

    total   = int(os.environ.get('PHOTOS_PER_SESSION', 4))
    strip_h = TOP_PAD + total * PHOTO_H + (total - 1) * GAP + BOTTOM_H + BOT_PAD
    photos = []
    for i in range(1, total + 1):
        path = os.path.join(session_dir, f'photo_{i}.jpg')
        if not os.path.exists(path):
            raise FileNotFoundError(f"photo_{i}.jpg missing for session {session_id}")
        img = _crop_center(Image.open(path).convert('RGB'), PHOTO_W, PHOTO_H)
        photos.append(moods.apply(img, mood))

    strip = Image.new('RGB', (STRIP_W, strip_h), BG)
    draw  = ImageDraw.Draw(strip)

    mx = (STRIP_W - PHOTO_W) // 2   # horizontal margin
    y  = TOP_PAD

    for photo in photos:
        if mood == '70s':
            strip.paste(_polaroid_border(photo), (mx, y))
        elif mood == 'noir':
            # Contact sheet: thin white frame, no fill
            draw.rectangle([mx - 3, y - 3, mx + PHOTO_W + 3, y + PHOTO_H + 3],
                           outline=(60, 60, 60), width=3)
            draw.rectangle([mx - 1, y - 1, mx + PHOTO_W + 1, y + PHOTO_H + 1],
                           outline=(220, 220, 220), width=1)
            strip.paste(photo, (mx, y))
        else:
            draw.rectangle([mx - 2, y - 2, mx + PHOTO_W + 1, y + PHOTO_H + 1],
                           outline=ACCENT, width=2)
            strip.paste(photo, (mx, y))
        y += PHOTO_H + GAP

    # Branding footer
    line_y = strip_h - BOTTOM_H - BOT_PAD + 10
    draw.line([(mx, line_y), (mx + PHOTO_W, line_y)], fill=ACCENT, width=1)

    f_title = _font(22, bold=True)
    f_date  = _font(15)
    draw.text((STRIP_W // 2, line_y + 14), 'photobooth',
              font=f_title, fill=TEXT,   anchor='mt')
    draw.text((STRIP_W // 2, line_y + 46), datetime.now().strftime('%d %b %Y'),
              font=f_date,  fill=ACCENT, anchor='mt')

    out = os.path.join(session_dir, 'strip.jpg')
    strip.save(out, 'JPEG', quality=int(os.environ.get('STRIP_JPEG_QUALITY', 92)))
    return out
