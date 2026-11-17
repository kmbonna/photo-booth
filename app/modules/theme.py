"""Theme loading.

A theme is a folder in THEMES_DIR (default app/themes) selected by THEME in .env:

    themes/<name>/
        theme.json   text overrides, allowed moods, custom moods (all optional)
        theme.css    visual overrides, loaded after style.css (optional)
        *.png/svg    assets, served at /theme/<file>

theme.json keys:
    text          {welcome_eyebrow, welcome_headline, welcome_subline, start_button}
                  HTML allowed (operator-controlled).
    moods         list of mood ids to offer, in order. Omit to offer all.
    custom_moods  {id: {label, desc, swatch, grade, border, background, accent,
                        text, footer, frame}} — event/brand moods.
                  grade:  built-in mood whose photo grading to use (default|noir|70s)
                  border: plain|polaroid|noir
                  frame:  transparent PNG in the theme folder, laid over each photo
                  background/accent/text: [r, g, b] strip colours

Loaded once at startup — restart the service after changing THEME or theme files.
"""
import json
import os
import re

from modules import log
logger = log.get(__name__)

BUILTIN_MOODS = {
    'default': {'label': 'Default', 'desc': 'Sometimes, less is more'},
    'noir':    {'label': 'Noir',    'desc': 'Silver screen &amp; timeless'},
    '70s':     {'label': '70s',     'desc': "From your parents' photo album"},
}

DEFAULT_TEXT = {
    'welcome_eyebrow':  '&#9673; Now Showing &#9673;',
    'welcome_headline': 'Looking to<br><em>savour a moment?</em>',
    'welcome_subline':  'Step inside. Make it last.',
    'start_button':     "Let's Go",
}

_ID_RE = re.compile(r'^[a-z0-9_-]+$')


def _themes_dir():
    return os.environ.get('THEMES_DIR') or os.path.join(os.path.dirname(__file__), '..', 'themes')


def _load():
    name = os.environ.get('THEME', '').strip()
    theme = {'name': name or None, 'dir': None, 'has_css': False,
             'text': dict(DEFAULT_TEXT), 'moods': [], 'custom': {}}

    data = {}
    if name:
        path = os.path.normpath(os.path.join(_themes_dir(), name))
        cfg = os.path.join(path, 'theme.json')
        if not _ID_RE.match(name) or not os.path.isdir(path):
            logger.error("theme '%s' not found in %s — using default look", name, _themes_dir())
            theme['name'] = None
        else:
            theme['dir'] = path
            theme['has_css'] = os.path.isfile(os.path.join(path, 'theme.css'))
            if os.path.isfile(cfg):
                try:
                    with open(cfg, encoding='utf-8') as f:
                        data = json.load(f)
                except (OSError, ValueError) as e:
                    logger.error("theme '%s': bad theme.json (%s) — ignoring it", name, e)

    theme['text'].update({k: v for k, v in data.get('text', {}).items() if k in DEFAULT_TEXT})

    for mid, m in data.get('custom_moods', {}).items():
        if not _ID_RE.match(mid):
            logger.error("theme: invalid custom mood id '%s' — skipped", mid)
            continue
        if m.get('grade', 'default') not in BUILTIN_MOODS:
            logger.error("theme: custom mood '%s' has unknown grade '%s' — skipped", mid, m.get('grade'))
            continue
        if m.get('frame') and theme['dir']:
            m['frame_path'] = os.path.join(theme['dir'], os.path.basename(m['frame']))
        theme['custom'][mid] = m

    catalog = {**BUILTIN_MOODS, **theme['custom']}
    wanted = data.get('moods') or list(catalog)
    allowed = [m for m in wanted if m in catalog]
    for m in set(wanted) - set(allowed):
        logger.error("theme: unknown mood '%s' in moods list — skipped", m)
    if not allowed:
        logger.error("theme: no valid moods — offering all built-in moods")
        allowed = list(BUILTIN_MOODS)

    theme['moods'] = [{'id': mid,
                       'label': catalog[mid].get('label', mid),
                       'desc': catalog[mid].get('desc', ''),
                       'swatch': catalog[mid].get('swatch')} for mid in allowed]

    logger.info("theme: %s · moods: %s", theme['name'] or 'default', ', '.join(allowed))
    return theme


THEME = _load()


def mood_ids():
    return [m['id'] for m in THEME['moods']]


def custom_mood(mood_id):
    """Definition dict for a theme's custom mood, or None for built-in moods."""
    return THEME['custom'].get(mood_id)
