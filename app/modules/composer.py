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

    # Grain/texture — stronger so it reads on screen too
    arr += np.random.normal(0, 11, arr.shape)

    # Corner aging — pronounced yellowing and browning
    yy, xx = np.mgrid[0:PHOTO_H, 0:PHOTO_W].astype(np.float32)
    age = np.zeros((PHOTO_H, PHOTO_W), dtype=np.float32)
    for cy, cx in [(0, 0), (0, PHOTO_W-1), (PHOTO_H-1, 0), (PHOTO_H-1, PHOTO_W-1)]:
        dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
        age += np.clip(1 - dist / 130, 0, 1)
    age = np.clip(age, 0, 1)[:, :, np.newaxis]
    arr[:, :, 0:1] += age * 22    # heavy red
    arr[:, :, 1:2] += age * 8     # slight green
    arr[:, :, 2:3] -= age * 40    # strong blue pull → deep yellowing

    # Outer edge wear — more visible darkening
    fade_px = 14
    for i in range(fade_px):
        s = ((fade_px - i) / fade_px) ** 2 * 35
        arr[i, :]                -= s
        arr[PHOTO_H - 1 - i, :] -= s
        arr[:, i]                -= s
        arr[:, PHOTO_W - 1 - i] -= s

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    bordered = Image.fromarray(arr)
    bordered.paste(inner, (PL, PT))

    # Scratches — more of them, slightly more visible
    draw = ImageDraw.Draw(bordered)
    rng  = np.random.default_rng()
    for _ in range(int(rng.integers(4, 9))):
        side = int(rng.integers(4))
        if side == 0:   sx, sy = int(rng.integers(0, PHOTO_W)),          int(rng.integers(0, PT))
        elif side == 1: sx, sy = int(rng.integers(0, PHOTO_W)),          int(rng.integers(PT + inner_h, PHOTO_H))
        elif side == 2: sx, sy = int(rng.integers(0, PL)),               int(rng.integers(0, PHOTO_H))
        else:           sx, sy = int(rng.integers(PL + inner_w, PHOTO_W)), int(rng.integers(0, PHOTO_H))
        length = int(rng.integers(15, 70))
        dx     = int(rng.integers(-length, length + 1))
        dy     = int(rng.integers(-3, 4))
        c      = int(rng.integers(170, 215))
        w      = 1 if rng.random() > 0.3 else 2
        draw.line([(sx, sy), (sx + dx, sy + dy)], fill=(c, c - 8, c - 20), width=w)

    # Subtle inner shadow where border meets photo — makes it feel inset
    draw.rectangle([PL, PT, PL + inner_w - 1, PT + inner_h - 1],
                   outline=(178, 162, 138), width=1)

    return bordered


def _noir_border(photo):
    """Worn B&W Polaroid border — cool silver-grey, heavy corner damage, aggressive wear."""
    PL, PR, PT, PB = 14, 14, 12, 50
    inner_w = PHOTO_W - PL - PR   # 812
    inner_h = PHOTO_H - PT - PB   # 568

    inner = photo.resize((inner_w, inner_h), Image.LANCZOS)

    # Cool silver-grey base — no warmth, like old darkroom paper
    base = np.array([232, 229, 225], dtype=np.float32)
    arr  = np.broadcast_to(base, (PHOTO_H, PHOTO_W, 3)).copy()

    # Heavier, cooler grain
    arr += np.random.normal(0, 14, arr.shape)

    # Heavy corner staining — near-black damage, cool tone
    yy, xx = np.mgrid[0:PHOTO_H, 0:PHOTO_W].astype(np.float32)
    damage = np.zeros((PHOTO_H, PHOTO_W), dtype=np.float32)
    for cy, cx in [(0, 0), (0, PHOTO_W-1), (PHOTO_H-1, 0), (PHOTO_H-1, PHOTO_W-1)]:
        dist = np.sqrt((yy - cy)**2 + (xx - cx)**2)
        damage += np.clip(1 - dist / 120, 0, 1) ** 1.4
    damage = np.clip(damage, 0, 1)[:, :, np.newaxis]
    arr[:, :, 0:1] -= damage * 170
    arr[:, :, 1:2] -= damage * 165
    arr[:, :, 2:3] -= damage * 150   # blue pulled less → cool dark not warm dark

    # One random corner gets catastrophic extra damage — like the top-left in the reference
    rng = np.random.default_rng()
    heavy_cy, heavy_cx = [(0,0),(0,PHOTO_W-1),(PHOTO_H-1,0),(PHOTO_H-1,PHOTO_W-1)][int(rng.integers(4))]
    extra_dist = np.sqrt((yy - heavy_cy)**2 + (xx - heavy_cx)**2)
    extra = np.clip(1 - extra_dist / 95, 0, 1) ** 0.7
    arr[:, :, 0] -= extra * 75
    arr[:, :, 1] -= extra * 72
    arr[:, :, 2] -= extra * 65

    # Aggressive edge darkening — left side gets hit harder like the reference
    fade_px = 18
    for i in range(fade_px):
        s = ((fade_px - i) / fade_px) ** 1.4 * 55
        arr[i, :]                -= s
        arr[PHOTO_H - 1 - i, :] -= s
        arr[:, i]                -= s * 1.4   # left edge: noticeably more worn
        arr[:, PHOTO_W - 1 - i] -= s

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    bordered = Image.fromarray(arr)
    bordered.paste(inner, (PL, PT))

    # More scratches, cool-toned, some thicker
    draw = ImageDraw.Draw(bordered)
    for _ in range(int(rng.integers(6, 12))):
        side = int(rng.integers(4))
        if side == 0:   sx, sy = int(rng.integers(0, PHOTO_W)),            int(rng.integers(0, PT))
        elif side == 1: sx, sy = int(rng.integers(0, PHOTO_W)),            int(rng.integers(PT + inner_h, PHOTO_H))
        elif side == 2: sx, sy = int(rng.integers(0, PL)),                 int(rng.integers(0, PHOTO_H))
        else:           sx, sy = int(rng.integers(PL + inner_w, PHOTO_W)), int(rng.integers(0, PHOTO_H))
        length = int(rng.integers(15, 85))
        dx = int(rng.integers(-length, length + 1))
        dy = int(rng.integers(-3, 4))
        c  = int(rng.integers(150, 205))
        w  = 1 if rng.random() > 0.25 else 2
        draw.line([(sx, sy), (sx + dx, sy + dy)], fill=(c, c, c + 3), width=w)

    # Cool inner shadow at photo edge
    draw.rectangle([PL, PT, PL + inner_w - 1, PT + inner_h - 1],
                   outline=(155, 153, 150), width=1)

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
            strip.paste(_noir_border(photo), (mx, y))
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
