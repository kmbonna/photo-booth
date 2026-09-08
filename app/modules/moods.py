from PIL import Image, ImageEnhance, ImageOps


def _apply_noir(img):
    img = ImageOps.grayscale(img).convert('RGB')
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = ImageEnhance.Brightness(img).enhance(0.88)
    return img


def _apply_70s(img):
    r, g, b = img.split()
    # lift shadows (fade blacks), warm cast: boost red, pull back blue
    r = r.point(lambda x: min(255, int(x * 1.12 + 18)))
    g = g.point(lambda x: min(255, int(x * 1.02 + 8)))
    b = b.point(lambda x: min(255, int(x * 0.78 + 12)))
    img = Image.merge('RGB', (r, g, b))
    img = ImageEnhance.Color(img).enhance(0.8)
    img = ImageEnhance.Contrast(img).enhance(0.88)
    return img


_MOODS = {
    'noir': _apply_noir,
    '70s':  _apply_70s,
}


def apply(img, mood):
    fn = _MOODS.get(mood)
    return fn(img) if fn else img
