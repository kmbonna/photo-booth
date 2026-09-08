from PIL import Image, ImageEnhance, ImageOps


def _apply_noir(img):
    img = ImageOps.grayscale(img).convert('RGB')
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Brightness(img).enhance(0.88)
    return img


def _apply_70s(img):
    r, g, b = img.split()
    # heavy warm cast matching Kodachrome/Polaroid reference:
    # blown orange highlights, crushed blues, lifted blacks throughout
    r = r.point(lambda x: min(255, int(x * 1.22 + 38)))
    g = g.point(lambda x: min(255, int(x * 0.95 + 22)))
    b = b.point(lambda x: min(255, int(x * 0.52 + 28)))
    img = Image.merge('RGB', (r, g, b))
    img = ImageEnhance.Color(img).enhance(1.05)    # keep reds/oranges punchy
    img = ImageEnhance.Contrast(img).enhance(0.76) # hazy, soft — no punchy blacks
    img = ImageEnhance.Brightness(img).enhance(0.93)
    return img


_MOODS = {
    'noir': _apply_noir,
    '70s':  _apply_70s,
}


def apply(img, mood):
    fn = _MOODS.get(mood)
    return fn(img) if fn else img
