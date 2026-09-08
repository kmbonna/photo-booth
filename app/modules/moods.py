import numpy as np
from PIL import Image, ImageEnhance, ImageOps


def _vignette(arr, strength):
    """Darken corners. strength = brightness multiplier at the extreme corner (0=black, 1=no effect)."""
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    yn = (yy / (h - 1)) * 2 - 1
    xn = (xx / (w - 1)) * 2 - 1
    dist = np.sqrt(xn**2 + yn**2)
    mask = 1 - np.clip(dist / 1.41, 0, 1) * (1 - strength)
    return arr * mask[:, :, np.newaxis]


def _apply_noir(img):
    img = ImageOps.grayscale(img).convert('RGB')
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Brightness(img).enhance(0.88)

    arr = np.array(img, dtype=np.float32)

    # Heavy silver halide grain — pushed film look, same noise on all channels
    grain = np.random.normal(0, 28, (arr.shape[0], arr.shape[1]))
    arr[:, :, 0] += grain
    arr[:, :, 1] += grain
    arr[:, :, 2] += grain

    # Strong corner vignette — corners go to ~45% brightness like the reference
    arr = _vignette(arr, strength=0.45)

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _apply_70s(img):
    r, g, b = img.split()
    # heavy warm cast matching Kodachrome/Polaroid reference:
    # blown orange highlights, crushed blues, lifted blacks throughout
    r = r.point(lambda x: min(255, int(x * 1.22 + 38)))
    g = g.point(lambda x: min(255, int(x * 0.95 + 22)))
    b = b.point(lambda x: min(255, int(x * 0.52 + 28)))
    img = Image.merge('RGB', (r, g, b))
    img = ImageEnhance.Color(img).enhance(1.05)
    img = ImageEnhance.Contrast(img).enhance(0.76)
    img = ImageEnhance.Brightness(img).enhance(0.93)

    arr = np.array(img, dtype=np.float32)

    # Fine warm grain — Kodachrome character, warm-tinted noise
    grain = np.random.normal(0, 13, (arr.shape[0], arr.shape[1]))
    arr[:, :, 0] += grain * 1.2   # red channel gets more grain → warm feel
    arr[:, :, 1] += grain * 0.9
    arr[:, :, 2] += grain * 0.7

    # Soft vignette — corners at ~72% brightness
    arr = _vignette(arr, strength=0.72)

    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


_MOODS = {
    'noir': _apply_noir,
    '70s':  _apply_70s,
}


def apply(img, mood):
    fn = _MOODS.get(mood)
    return fn(img) if fn else img
