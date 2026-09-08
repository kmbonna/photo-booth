import os
from datetime import datetime
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

STRIP_H = TOP_PAD + 4 * PHOTO_H + 3 * GAP + BOTTOM_H + BOT_PAD

# Colours — matches app CSS variables
BG      = (247, 240, 227)   # --bg
ACCENT  = (160, 82,  45)    # --accent
BROWN   = (59,  42,  26)    # --brown


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


def compose(session_id, mood='default'):
    """Build the 4-photo strip and save it as strip.jpg in the session folder."""
    base = os.environ.get('SESSIONS_DIR') or os.path.join(os.path.dirname(__file__), '..', 'sessions')
    session_dir = os.path.normpath(os.path.join(base, session_id))

    photos = []
    for i in range(1, 5):
        path = os.path.join(session_dir, f'photo_{i}.jpg')
        if not os.path.exists(path):
            raise FileNotFoundError(f"photo_{i}.jpg missing for session {session_id}")
        img = _crop_center(Image.open(path).convert('RGB'), PHOTO_W, PHOTO_H)
        photos.append(moods.apply(img, mood))

    strip = Image.new('RGB', (STRIP_W, STRIP_H), BG)
    draw  = ImageDraw.Draw(strip)

    mx = (STRIP_W - PHOTO_W) // 2   # horizontal margin
    y  = TOP_PAD

    for photo in photos:
        # Thin accent frame
        draw.rectangle([mx - 2, y - 2, mx + PHOTO_W + 1, y + PHOTO_H + 1],
                        outline=ACCENT, width=2)
        strip.paste(photo, (mx, y))
        y += PHOTO_H + GAP

    # Branding footer
    line_y = STRIP_H - BOTTOM_H - BOT_PAD + 10
    draw.line([(mx, line_y), (mx + PHOTO_W, line_y)], fill=ACCENT, width=1)

    f_title = _font(22, bold=True)
    f_date  = _font(15)
    draw.text((STRIP_W // 2, line_y + 14), 'photobooth',
              font=f_title, fill=BROWN,   anchor='mt')
    draw.text((STRIP_W // 2, line_y + 46), datetime.now().strftime('%d %b %Y'),
              font=f_date,  fill=ACCENT,  anchor='mt')

    out = os.path.join(session_dir, 'strip.jpg')
    strip.save(out, 'JPEG', quality=int(os.environ.get('STRIP_JPEG_QUALITY', 92)))
    return out
