#!/usr/bin/env python3
"""Convert the Singer Kitchens WordPress export into Eleventy source files.

Usage (from the repo root):
    python3 tools/convert_wp.py

Reads  source/singerkitchens.WordPress.*.xml and source/uploads/ (both git-ignored)
Writes src/pages/*.njk, src/posts/*.md, src/service-area/*.njk, src/images/**.webp,
       src/_data/generated/*.json and reports/*.json

Copy is moved over word for word: text is never rewritten, only the markup around it is
cleaned (inline styles, Elementor classes and empty wrappers removed).
"""
import glob
import hashlib
import html
import json
import os
import re
import shutil
import sys
import unicodedata
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse, quote

sys.path.insert(0, os.path.dirname(__file__))
import wp_export as W  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'src')
UPLOADS = os.path.join(ROOT, 'source', 'uploads')
REPORTS = os.path.join(ROOT, 'reports')

MAIN_PHONE = '(504) 539-4605'
MAIN_TEL = 'tel:+15045394605'
CONSULT = '/request-consultation/'
GHL_CONSULT_FORM = 'aYZUPqktOVdbueGKsdou'

CORE_PATHS = [
    '/', '/about/', '/our-process/', '/as-seen-on/', '/employment/', '/pro-partners/',
    '/remodeling/', '/small-kitchen-remodeling/', '/kitchens/', '/kitchen-cabinets/', '/quick-refresh/',
    '/bathrooms/', '/closets/', '/portfolio/', '/cabinets/', '/countertops/', '/storage-solutions/',
    '/blog/', '/videos/', '/kitchen-renovation-roi/', '/top-kitchen-design-trends/', '/kitchen-design-checklist/',
    '/kitchen-design-secrets/', '/cabinet-repainting-vs-remodeling/', '/kitchen-remodeling-faqs/',
    '/showrooms/', '/reviews/', '/financing/', '/request-consultation/',
]
# Service pages that get the compact four-step strip above the final call to action.
PROCESS_STRIP_PATHS = ['/remodeling/', '/small-kitchen-remodeling/', '/kitchens/', '/kitchen-cabinets/', '/cabinets/',
                       '/countertops/', '/quick-refresh/', '/storage-solutions/', '/closets/']
# Pages built by hand as templates (their copy still comes from the export, checked by tools/check_text.py)
REDIRECTED_PAGES = {}  # /kitchen-design/ is now published as its own page
BESPOKE = {'/': 'home', '/showrooms/': 'showrooms'}

HOME_HERO_FILES = ['2026/03/new-slider2_26.webp']
REPORT = {'missing_images': [], 'replaced_forms': [], 'notes': [], 'unknown_widgets': {}, 'shortcodes': {}}

# ------------------------------------------------------------------------------------------
# Load export
# ------------------------------------------------------------------------------------------
xml_path = sorted(glob.glob(os.path.join(ROOT, 'source', 'singerkitchens.WordPress.*.xml')))[-1]
EXP = W.load(xml_path)
ITEMS = EXP['items']
BY_ID = {i['id']: i for i in ITEMS}
ATTACH = {i['id']: i for i in ITEMS if i['type'] == 'attachment'}
ATTACH_BY_FILE = {}
for a in ATTACH.values():
    if a['attachment_url']:
        rel = a['attachment_url'].split('/wp-content/uploads/')[-1]
        ATTACH_BY_FILE[rel] = a
PUBLISHED = [i for i in ITEMS if i['status'] == 'publish' and i['type'] in ('page', 'post', 'service-area')]
PATH_OF = {i['id']: W.path_of(i) for i in PUBLISHED}
PUBLISHED_PATHS = set(PATH_OF.values())


def esc(s):
    return html.escape(s or '', quote=True)


# ------------------------------------------------------------------------------------------
# Links
# ------------------------------------------------------------------------------------------
def norm_link(url):
    """Normalise a link: internal links become root-relative final URLs."""
    if not url:
        return ''
    u = url.strip()
    if u.startswith(('mailto:', 'tel:', '#', 'sms:')):
        if u.startswith('tel:'):
            digits = re.sub(r'\D', '', u)
            if len(digits) == 10:
                digits = '1' + digits
            return 'tel:+' + digits
        return u
    # "http://info@singerkitchens.com" style broken email links
    m = re.match(r'^https?://([\w.+-]+@[\w.-]+\.\w+)/?$', u)
    if m:
        return 'mailto:' + m.group(1)
    if re.match(r'^(www\.)?singerkitchens\.com', u):
        u = 'https://' + u
    p = urlparse(u)
    host = (p.netloc or '').lower()
    if host and host not in ('singerkitchens.com', 'www.singerkitchens.com'):
        return u
    path = p.path or '/'
    if not host and not u.startswith('/'):
        return u  # relative or odd, leave
    if path.startswith('/wp-content/uploads/'):
        rel = unquote(path.split('/wp-content/uploads/')[-1])
        im = image_for_file(rel, role='content', want_link=True) if re.search(r'\.(jpe?g|png|webp|gif|avif)$', rel, re.I) else None
        if im:
            return im['src']
        copied = copy_upload(rel)
        return copied or u
    if '.' not in path.rsplit('/', 1)[-1] and not path.endswith('/'):
        path += '/'
    if path in ('/home/',):
        path = '/'
    if path == '/kitchen-design/':
        pass  # kept as its own page (see README / redirects)
    # old service-area links without the /service-area/ prefix (e.g. /mandeville/kitchen-remodeling/)
    if path not in PUBLISHED_PATHS and ('/service-area' + path) in PUBLISHED_PATHS:
        path = '/service-area' + path
    out = path
    if p.query:
        out += '?' + p.query
    if p.fragment:
        out += '#' + p.fragment
    return out


def copy_upload(rel):
    src = os.path.join(UPLOADS, rel)
    if not os.path.exists(src):
        return None
    dst = os.path.join(SRC, 'wp-content', 'uploads', rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
    return '/wp-content/uploads/' + quote(rel)


# ------------------------------------------------------------------------------------------
# Images
# ------------------------------------------------------------------------------------------
from PIL import Image, ImageOps  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
IMG_CACHE = {}
ALT_OVERRIDES = json.load(open(os.path.join(SRC, '_data', 'alt-overrides.json'))) if os.path.exists(os.path.join(SRC, '_data', 'alt-overrides.json')) else {}
ALT_WORD_RE = re.compile(r'\bcustom\b\s*', re.I)


def find_original(rel):
    """Given an uploads-relative path (maybe a resized variant), return the original file path."""
    cands = []
    base, ext = os.path.splitext(rel)
    stripped = re.sub(r'-\d+x\d+$', '', base)
    stripped2 = re.sub(r'-scaled$', '', stripped)
    for b in (stripped2, stripped, base):
        for e in (ext, ext.lower(), ext.upper()):
            cands.append(b + e)
    for c in cands:
        for form in ('NFC', 'NFD'):
            p = os.path.join(UPLOADS, unicodedata.normalize(form, c))
            if os.path.exists(p):
                return p, c
    # case-insensitive match in the same folder
    d = os.path.join(UPLOADS, os.path.dirname(rel))
    if os.path.isdir(d):
        names = {n.lower(): n for n in os.listdir(d)}
        for c in cands:
            n = names.get(os.path.basename(c).lower())
            if n:
                return os.path.join(d, n), os.path.join(os.path.dirname(rel), n)
    # last resort: same stem with another extension (e.g. .webp generated by an optimiser)
    for e in ('.jpg', '.jpeg', '.png', '.webp', '.JPG', '.PNG'):
        p = os.path.join(UPLOADS, stripped2 + e)
        if os.path.exists(p):
            return p, stripped2 + e
    return None, None


def clean_alt(text):
    t = (text or '').strip()
    t = ALT_WORD_RE.sub('', t).strip()
    t = re.sub(r'\s{2,}', ' ', t)
    return t[:1].upper() + t[1:] if t else t


def looks_like_filename(t):
    t = (t or '').strip()
    if not t:
        return True
    if re.fullmatch(r'[\w\-. ()]*\d[\w\-. ()]*', t) and not re.search(r'[a-zA-Z]{4,}\s+[a-zA-Z]{3,}', t):
        return True
    if re.search(r'(IMG|DSC|AdobeStock|Screenshot|Picture\d|marquee|slider|^\d+mls)', t, re.I) and len(t.split()) < 4:
        return True
    return False


def humanize(stem):
    s = re.sub(r'[-_]+', ' ', stem)
    s = re.sub(r'\b(min|scaled|copy|final|v\d|web|new|updated|compressed|\d+x\d+|\d+)\b', ' ', s, flags=re.I)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return s


def alt_for(att, rel, context):
    """Descriptive alt text: attachment alt > title > caption > file name words > page context."""
    candidates = []
    if att:
        candidates += [att['meta'].get('_wp_attachment_image_alt'), att['title'], att['excerpt']]
    for c in candidates:
        c = html.unescape(re.sub(r'<[^>]+>', '', c or '')).strip()
        if c and not looks_like_filename(c):
            return clean_alt(c)
    words = humanize(os.path.splitext(os.path.basename(rel))[0])
    if len(words.split()) >= 2 and not looks_like_filename(words):
        return clean_alt(words.capitalize())
    if context:
        return clean_alt(context)
    return 'Kitchen project by Singer Kitchens'


def image_for_file(rel, role='content', att=None, context='', want_link=False):
    rel = unquote(rel)
    key = (rel, role)
    if key in IMG_CACHE:
        r = dict(IMG_CACHE[key])
        return r
    src_path, orig_rel = find_original(rel)
    if not src_path:
        if not want_link:
            REPORT['missing_images'].append({'file': rel, 'used_on': context})
        return None
    if att is None:
        att = ATTACH_BY_FILE.get(orig_rel) or ATTACH_BY_FILE.get(rel)
    maxw = 1600 if role == 'hero' else (480 if role == 'logo' else 1200)
    out_rel = re.sub(r'\.[A-Za-z0-9]+$', '', orig_rel)
    out_rel = unicodedata.normalize('NFKD', out_rel).encode('ascii', 'ignore').decode()
    out_rel = re.sub(r'[^A-Za-z0-9/_.-]+', '-', out_rel)
    suffix = '' if maxw == 1200 else ('-hero' if role == 'hero' else '-sm')
    out_rel = out_rel + suffix + '.webp'
    out_path = os.path.join(SRC, 'images', out_rel)
    if os.path.exists(out_path):
        with Image.open(out_path) as im:
            w, h = im.size
    else:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        try:
            with Image.open(src_path) as im:
                im = ImageOps.exif_transpose(im)
                if im.mode in ('P', 'LA'):
                    im = im.convert('RGBA')
                elif im.mode not in ('RGB', 'RGBA'):
                    im = im.convert('RGB')
                if im.width > maxw:
                    im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
                im.save(out_path, 'WEBP', quality=80, method=5)
                w, h = im.size
        except Exception as e:  # unreadable file
            REPORT['missing_images'].append({'file': rel, 'used_on': context, 'error': str(e)})
            return None
    stem = out_rel[:-len(suffix + '.webp')]
    res = {'src': '/images/' + out_rel, 'w': w, 'h': h, 'alt': ALT_OVERRIDES.get(stem) or alt_for(att, orig_rel, context), 'orig': orig_rel, 'override': stem in ALT_OVERRIDES}
    IMG_CACHE[key] = res
    return dict(res)


def image(ref, role='content', context=''):
    """ref: Elementor image dict, attachment id, or URL."""
    att = None
    url = None
    if isinstance(ref, dict):
        if ref.get('id') and int(ref.get('id') or 0) in ATTACH:
            att = ATTACH[int(ref['id'])]
            url = att['attachment_url']
        url = url or ref.get('url')
    elif isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        att = ATTACH.get(int(ref))
        url = att['attachment_url'] if att else None
    else:
        url = ref
    if not url:
        return None
    if '/wp-content/uploads/' not in url:
        if url.startswith('http'):
            REPORT['notes'].append('External image kept as-is: %s (%s)' % (url, context))
            return {'src': url, 'w': None, 'h': None, 'alt': clean_alt(context) or 'Singer Kitchens'}
        return None
    rel = url.split('/wp-content/uploads/')[-1]
    return image_for_file(rel, role, att, context)


class Page:
    """Per-page render state."""

    def __init__(self, path, title, ctx=None):
        self.path = path
        self.title = title
        self.first_img = True
        self.ctx = ctx or {}
        self.h1s = []
        self.og_image = None


def img_tag(im, page, cls='', sizes=None, eager=False):
    if not im:
        return ''
    first = page.first_img
    page.first_img = False
    if first and not page.og_image:
        page.og_image = im['src']
    attrs = ['src="%s"' % esc(im['src']), 'alt="%s"' % esc(im['alt'])]
    if im.get('w'):
        attrs += ['width="%d"' % im['w'], 'height="%d"' % im['h']]
    if first or eager:
        attrs.append('fetchpriority="high"' if first else 'loading="eager"')
    else:
        attrs += ['loading="lazy"', 'decoding="async"']
    if cls:
        attrs.append('class="%s"' % cls)
    return '<img %s>' % ' '.join(attrs)


# ------------------------------------------------------------------------------------------
# HTML cleaning (keeps every word, drops styling)
# ------------------------------------------------------------------------------------------
KEEP_TAGS = {'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
             'blockquote', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'img', 'figure', 'figcaption',
             'iframe', 'hr', 'sup', 'sub', 's', 'del', 'code', 'pre', 'div', 'dl', 'dt', 'dd', 'caption', 'mark',
             'small', 'cite', 'abbr', 'details', 'summary', 'section', 'article', 'video', 'source', 'audio', 'picture'}
VOID = {'br', 'img', 'hr', 'source'}
DROP_WITH_CONTENT = {'script', 'style', 'noscript', 'svg', 'button', 'form', 'input', 'select', 'textarea', 'head', 'title', 'meta', 'link'}
KEEP_ATTRS = {'a': {'href', 'target', 'title'}, 'img': {'src', 'alt', 'width', 'height'},
              'iframe': {'src', 'title', 'allow', 'allowfullscreen', 'width', 'height', 'id', 'data-layout',
                         'data-trigger-type', 'data-trigger-value', 'data-activation-type', 'data-activation-value',
                         'data-deactivation-type', 'data-deactivation-value', 'data-form-name', 'data-height',
                         'data-layout-iframe-id', 'data-form-id', 'referrerpolicy', 'frameborder', 'style'},
              'td': {'colspan', 'rowspan'}, 'th': {'colspan', 'rowspan'}, 'ol': {'start'},
              'video': {'src', 'controls', 'poster'}, 'source': {'src', 'type'}, 'div': {'id'}, 'section': {'id'},
              'h2': {'id'}, 'h3': {'id'}}


class Cleaner(HTMLParser):
    def __init__(self, page):
        super().__init__(convert_charrefs=True)
        self.page = page
        self.out = []
        self.drop = 0
        self.stack = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.drop:
            if tag in DROP_WITH_CONTENT and tag not in VOID and tag not in ('input', 'meta', 'link'):
                self.drop += 1
            return
        if tag in DROP_WITH_CONTENT:
            if tag not in ('input', 'meta', 'link'):
                self.drop = 1
            return
        if tag == 'b':
            tag = 'strong'
        if tag == 'i':
            tag = 'em'
        if tag not in KEEP_TAGS:
            self.stack.append(None)
            return
        a = dict(attrs)
        keep = KEEP_ATTRS.get(tag, set())
        if tag == 'img':
            src = a.get('src') or ''
            ctx = a.get('alt') or self.page.title
            im = image(src, 'content', ctx) if '/wp-content/uploads/' in src else None
            if im:
                if a.get('alt') and not looks_like_filename(a.get('alt')) and not im.get('override'):
                    im['alt'] = clean_alt(html.unescape(a['alt']))
                self.out.append(img_tag(im, self.page))
            elif src.startswith('http') and '/wp-content/uploads/' not in src:
                self.out.append('<img src="%s" alt="%s" loading="lazy">' % (esc(src), esc(clean_alt(a.get('alt')) or self.page.title)))
            return
        parts = []
        for k, v in attrs:
            if k not in keep or v is None and k not in ('allowfullscreen',):
                continue
            if tag == 'iframe' and k == 'style':
                continue
            if tag == 'a' and k == 'href':
                v = norm_link(v)
            if v is None:
                parts.append(k)
            else:
                parts.append('%s="%s"' % (k, esc(v)))
        if tag == 'a':
            href = a.get('href') or ''
            nh = norm_link(href)
            if nh.startswith('http') or a.get('target') == '_blank':
                parts = [p for p in parts if not p.startswith('target=')]
                if nh.startswith('http'):
                    parts += ['target="_blank"', 'rel="noopener"']
        if tag == 'iframe':
            src = a.get('src') or ''
            if 'leadconnectorhq.com/widget/form' in src or 'msgsndr' in src:
                self.page.ctx.setdefault('forms', []).append(src)
            else:
                parts.append('loading="lazy"')
        self.out.append('<%s%s>' % (tag, (' ' + ' '.join(parts)) if parts else ''))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID and not self.drop:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.drop:
            if tag in DROP_WITH_CONTENT:
                self.drop -= 1
            return
        if tag in VOID:
            return
        if tag == 'b':
            tag = 'strong'
        if tag == 'i':
            tag = 'em'
        # pop to matching
        if tag in self.stack:
            while self.stack:
                t = self.stack.pop()
                if t is None:
                    continue
                self.out.append('</%s>' % t)
                if t == tag:
                    break
        elif not self.stack or self.stack[-1] is None:
            if self.stack:
                self.stack.pop()

    def handle_data(self, data):
        if self.drop:
            return
        self.out.append(html.escape(data, quote=False))

    def result(self):
        while self.stack:
            t = self.stack.pop()
            if t:
                self.out.append('</%s>' % t)
        s = ''.join(self.out)
        # tidy empty wrappers (keep paragraphs that hold only &nbsp; out)
        for _ in range(3):
            s = re.sub(r'<(p|div|strong|em|span|h\d)>(\s| |<br>)*</\1>', '', s)
        return s.strip()


def clean_html(raw, page):
    if not raw:
        return ''
    raw = render_shortcodes(raw, page)
    c = Cleaner(page)
    c.feed(raw)
    c.close()
    return c.result()


# ------------------------------------------------------------------------------------------
# Shortcodes and classic content
# ------------------------------------------------------------------------------------------
def wpautop(text):
    if '<p' in text and '\n\n' not in text:
        return text
    text = text.replace('\r\n', '\n')
    blocks = re.split(r'\n\s*\n', text)
    out = []
    block_re = re.compile(r'^\s*<(/?)(p|div|h\d|ul|ol|li|table|blockquote|figure|iframe|hr|pre|section|!--|\[)', re.I)
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if block_re.match(b):
            out.append(b)
        else:
            out.append('<p>' + b.replace('\n', '<br>\n') + '</p>')
    return '\n'.join(out)


def gallery_html(images, page, cls='gallery'):
    figs = []
    for im in images:
        if not im:
            continue
        figs.append('<figure>%s</figure>' % img_tag(im, page))
    if not figs:
        return ''
    return '<div class="%s">%s</div>' % (cls, ''.join(figs))


def modula_images(gid, page):
    g = BY_ID.get(int(gid))
    if not g:
        REPORT['notes'].append('Modula gallery %s not in export (%s)' % (gid, page.path))
        return []
    data = W.php_unserialize(g['meta'].get('modula-images')) or []
    out = []
    for row in data:
        im = image(int(row.get('id')), 'content', page.title + ' kitchen project photo') if row.get('id') else None
        if im and row.get('alt') and not looks_like_filename(row['alt']) and not im.get('override'):
            im['alt'] = clean_alt(row['alt'])
        out.append(im)
    return out


def youtube_id(url):
    m = re.search(r'(?:youtu\.be/|v=|embed/|shorts/)([\w-]{11})', url or '')
    return m.group(1) if m else None


def video_html(url, title='Video', shorts=False):
    vid = youtube_id(url)
    if vid:
        short = shorts or 'shorts' in (url or '')
        return ('<div class="video%s"><iframe src="https://www.youtube.com/embed/%s" title="%s" loading="lazy" '
                'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
                'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>') % (
            ' video-short' if short else '', vid, esc(title))
    if url and 'vimeo' in url:
        m = re.search(r'vimeo\.com/(\d+)', url)
        if m:
            return '<div class="video"><iframe src="https://player.vimeo.com/video/%s" title="%s" loading="lazy" allowfullscreen></iframe></div>' % (m.group(1), esc(title))
    if url and url.endswith('.mp4'):
        link = norm_link(url)
        return '<div class="video"><video src="%s" controls preload="none"></video></div>' % esc(link)
    return ''


def ghl_form(form_id, page, title='Form'):
    page.ctx.setdefault('forms', []).append(form_id)
    return ('<div class="ghl-form"><iframe src="https://api.leadconnectorhq.com/widget/form/{id}" '
            'style="width:100%;height:100%;border:none;border-radius:3px" id="inline-{id}" data-layout="{{\'id\':\'INLINE\'}}" '
            'data-trigger-type="alwaysShow" data-trigger-value="" data-activation-type="alwaysActivated" data-activation-value="" '
            'data-deactivation-type="neverDeactivate" data-deactivation-value="" data-form-name="{t}" data-height="900" '
            'data-layout-iframe-id="inline-{id}" data-form-id="{id}" title="{t}"></iframe></div>').format(id=form_id, t=esc(title))


def replaced_form(kind, page):
    REPORT['replaced_forms'].append({'page': page.path, 'was': kind, 'now': 'GoHighLevel consultation form ' + GHL_CONSULT_FORM})
    return ghl_form(GHL_CONSULT_FORM, page, 'Request Consultation')


def render_shortcodes(text, page):
    def sc(m):
        name, args = m.group(1), m.group(2) or ''
        REPORT['shortcodes'][name] = REPORT['shortcodes'].get(name, 0) + 1
        a = dict(re.findall(r'(\w+)=["”“″]?([^"”“″\s\]]+)', args))
        if name == 'modula':
            return gallery_html(modula_images(a.get('id', 0), page), page)
        if name == 'gallery':
            ids = [x for x in re.split(r'\s*,\s*', a.get('ids', '')) if x.strip().isdigit()]
            return gallery_html([image(int(x), 'content', page.title) for x in ids], page)
        if name in ('gravityform', 'contact-form-7', 'contact_form_7'):
            return replaced_form(name, page)
        if name == 'trustindex':
            return '<!--reviews-->'
        if name in ('oceanwp_date',):
            return '2026'
        return m.group(0)
    text = re.sub(r'\[embed\](.*?)\[/embed\]', lambda m: video_html(m.group(1)), text)
    text = re.sub(r'\[video [^\]]*?(?:mp4|src)="([^"]+)"[^\]]*\](?:\[/video\])?', lambda m: video_html(m.group(1)), text)
    text = re.sub(r'\[caption[^\]]*\](.*?)\[/caption\]', lambda m: '<figure>%s</figure>' % m.group(1), text, flags=re.S)
    text = re.sub(r'\[(modula|gallery|gravityform|contact-form-7|contact_form_7|trustindex|oceanwp_date)\b([^\]]*)\]', sc, text)
    # bare YouTube URLs on their own line (oEmbed)
    text = re.sub(r'(?m)^\s*(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]{11}\S*)\s*$', lambda m: video_html(m.group(1)), text)
    return text


# ------------------------------------------------------------------------------------------
# Elementor renderer
# ------------------------------------------------------------------------------------------
DYN_RE = re.compile(r'name="([\w-]+)" settings="([^"]*)"')


def dyn_value(s, key, page):
    """Resolve an Elementor dynamic tag for setting `key` using page.ctx['acf'] / page title."""
    dyn = (s.get('__dynamic__') or {}) if isinstance(s.get('__dynamic__'), dict) else {}
    tag = dyn.get(key)
    if not tag:
        return None
    m = DYN_RE.search(tag)
    if not m:
        return None
    name = m.group(1)
    try:
        st = json.loads(unquote(m.group(2)))
    except Exception:
        st = {}
    acf = page.ctx.get('acf') or {}
    if name == 'page-title':
        return page.ctx.get('item_title', page.title)
    if name == 'post-featured-image':
        tid = acf.get('_thumbnail_id')
        return {'id': int(tid)} if tid and tid.isdigit() else st.get('fallback')
    if name in ('acf-text', 'acf-url'):
        field = (st.get('key') or '').split(':')[-1]
        v = acf.get(field)
        if v is None or v == '':
            return None
        return (st.get('before') or '') + v + (st.get('after') or '')
    if name == 'acf-image':
        field = (st.get('key') or '').split(':')[-1]
        v = acf.get(field)
        if v and str(v).isdigit():
            return {'id': int(v)}
        return st.get('fallback')
    return None


def setting(s, key, page):
    v = dyn_value(s, key, page)
    if v is not None:
        return v
    return s.get(key)


def is_lets_talk(text):
    t = (text or '').lower().replace('’', "'")
    return "let's talk" in t


def button_html(s, page, cls='btn'):
    text = setting(s, 'text', page) or ''
    link = setting(s, 'link', page) or {}
    href = norm_link(link.get('url') if isinstance(link, dict) else link)
    if is_lets_talk(text):
        href = CONSULT
    if not text.strip():
        return ''
    if not href:
        href = CONSULT
    ext = ' target="_blank" rel="noopener"' if href.startswith('http') else ''
    return '<p class="btn-row"><a class="%s" href="%s"%s>%s</a></p>' % (cls, esc(href), ext, esc(html.unescape(text)).replace('&lt;br&gt;', '<br>'))


def heading_html(s, page):
    title = setting(s, 'title', page)
    if not title or not str(title).strip():
        return ''
    tag = s.get('header_size') or 'h2'
    if tag not in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        tag = 'p' if tag in ('p', 'div', 'span') else 'h2'
    inner = clean_html(str(title), page)
    if not inner:
        return ''
    link = s.get('link')
    if isinstance(link, dict) and link.get('url'):
        href = norm_link(link['url'])
        # Home: "Cabinets & Countertops" heading should link to /cabinets/ (site plan fix)
        if page.path == '/' and 'Cabinets &amp; Countertops' in inner:
            href = '/cabinets/'
        inner = '<a href="%s">%s</a>' % (esc(href), inner)
    if tag == 'h1':
        page.h1s.append(re.sub(r'<[^>]+>', '', inner))
    cls = ' class="el-sub"' if tag == 'p' else ''
    return '<%s%s>%s</%s>' % (tag, cls, inner, tag)


def widget_html(e, page):
    s = e.get('settings') or {}
    if not isinstance(s, dict):
        s = {}
    wt = e.get('widgetType')
    if s.get('hide_desktop') and s.get('hide_tablet'):
        return ''
    if wt == 'heading':
        return heading_html(s, page)
    if wt == 'text-editor':
        raw = setting(s, 'editor', page) or ''
        raw = wpautop(raw) if '<p' not in raw and '\n\n' in raw else raw
        body = clean_html(raw, page)
        return '<div class="el-text">%s</div>' % body if body else ''
    if wt == 'button':
        return button_html(s, page)
    if wt == 'image':
        ref = setting(s, 'image', page)
        im = image(ref, 'content', s.get('caption') or page.title)
        if not im:
            return ''
        t = img_tag(im, page)
        lt = s.get('link_to')
        link = s.get('link') if isinstance(s.get('link'), dict) else {}
        if lt == 'custom' and link.get('url'):
            href = norm_link(link['url'])
            t = '<a href="%s">%s</a>' % (esc(href), t)
        cap = s.get('caption') if s.get('caption_source') == 'custom' else ''
        return '<figure class="el-img">%s%s</figure>' % (t, '<figcaption>%s</figcaption>' % esc(cap) if cap else '')
    if wt in ('spacer',):
        return ''
    if wt == 'divider':
        txt = s.get('text') if s.get('look') == 'line_text' else ''
        return '<hr class="el-divider">' if not txt else '<p class="el-divider-text">%s</p>' % esc(txt)
    if wt == 'video':
        url = s.get('youtube_url') or s.get('vimeo_url') or (s.get('hosted_url') or {}).get('url') if isinstance(s.get('hosted_url'), dict) else (s.get('youtube_url') or s.get('vimeo_url'))
        return video_html(url, page.title + ' video')
    if wt in ('html', 'shortcode'):
        raw = s.get('html') or s.get('shortcode') or ''
        if 'trustindex' in raw:
            page.ctx['reviews'] = True
            return '{% endraw %}{% include "partials/google-reviews.njk" %}{% raw %}'
        m = re.search(r'leadconnectorhq\.com/widget/form/(\w+)', raw)
        if m:
            return ghl_form(m.group(1), page, page.title)
        if re.search(r'<!DOCTYPE|<html', raw, re.I):
            page.ctx['standalone_html'] = raw
            return '{% endraw %}{% include "partials/embedded-tool.njk" %}{% raw %}'
        vid = re.search(r'youtube\.com/embed/([\w-]{11})', raw)
        if vid and raw.count('<iframe') == 1:
            return video_html('https://youtu.be/' + vid.group(1), page.title + ' video', shorts='Shorts' in raw or 'height="560"' in raw)
        if 'calendar' in raw or 'booking' in raw:
            m2 = re.search(r'src="([^"]+)"', raw)
            if m2:
                return '<div class="embed"><iframe src="%s" title="Booking calendar" loading="lazy" style="width:100%%;min-height:900px;border:none"></iframe></div>' % esc(m2.group(1))
        body = clean_html(render_shortcodes(raw, page), page)
        return '<div class="el-html">%s</div>' % body if body else ''
    if wt == 'google_maps':
        addr = s.get('address') or ''
        return ('<div class="map"><iframe src="https://maps.google.com/maps?q=%s&amp;t=m&amp;z=15&amp;output=embed&amp;iwloc=near" '
                'title="Map: %s" loading="lazy"></iframe></div>') % (quote(addr), esc(addr))
    if wt in ('image-carousel', 'gallery', 'image-gallery'):
        lst = s.get('carousel') or s.get('gallery') or s.get('wp_gallery') or []
        ims = [image(x, 'content', page.title) for x in lst]
        return gallery_html(ims, page, 'gallery gallery-grid')
    if wt == 'slides':
        out = []
        for i, sl in enumerate(s.get('slides') or []):
            im = image(sl.get('background_image'), 'hero', sl.get('heading') or page.title)
            out.append('<div class="slide-static">%s<div class="slide-card"><h2>%s</h2>%s%s</div></div>' % (
                img_tag(im, page) if im and i == 0 else '', esc(sl.get('heading')),
                '<p>%s</p>' % esc(sl.get('description')) if sl.get('description') else '',
                '<p class="btn-row"><a class="btn" href="%s">%s</a></p>' % (
                    CONSULT if is_lets_talk(sl.get('button_text')) else esc(norm_link((sl.get('link') or {}).get('url'))),
                    esc(sl.get('button_text'))) if sl.get('button_text') else ''))
        return ''.join(out)
    if wt == 'call-to-action':
        im = image(s.get('bg_image'), 'content', s.get('title') or page.title)
        link = norm_link((s.get('link') or {}).get('url'))
        return ('<div class="cta-card"><a href="%s">%s<span class="cta-title">%s</span>%s<span class="cta-more">%s</span></a></div>') % (
            esc(link), img_tag(im, page) if im else '', esc(s.get('title')),
            '<span class="cta-desc">%s</span>' % esc(s.get('description')) if s.get('description') else '',
            esc(s.get('button') or ''))
    if wt == 'icon-box':
        title = setting(s, 'title_text', page) or ''
        desc = setting(s, 'description_text', page) or ''
        link = norm_link((s.get('link') or {}).get('url')) if isinstance(s.get('link'), dict) else ''
        tag = s.get('title_size') or 'h3'
        tag = tag if tag in ('h2', 'h3', 'h4', 'h5', 'h6') else 'p'
        t = esc(html.unescape(title))
        if link:
            t = '<a href="%s">%s</a>' % (esc(link), t)
        d = clean_html(desc, page) if desc.strip(' .\n') else ''
        return '<div class="icon-box"><%s>%s</%s>%s</div>' % (tag, t, tag, '<div class="el-text">%s</div>' % d if d else '')
    if wt == 'image-box':
        im = image(setting(s, 'image', page), 'logo', s.get('title_text') or page.title)
        return '<div class="icon-box">%s<h3>%s</h3>%s</div>' % (
            img_tag(im, page) if im else '', esc(s.get('title_text')),
            '<p>%s</p>' % esc(s.get('description_text')) if s.get('description_text') else '')
    if wt == 'icon-list':
        lis = []
        for it in s.get('icon_list') or []:
            txt = clean_html(it.get('text') or '', page)
            link = it.get('link') if isinstance(it.get('link'), dict) else {}
            href = norm_link(link.get('url')) if link.get('url') and (link['url'].startswith(('http', '/', 'tel:', 'mailto:')) or 'singerkitchens.com' in link['url']) else ''
            lis.append('<li>%s</li>' % ('<a href="%s">%s</a>' % (esc(href), txt) if href else txt))
        return '<ul class="icon-list">%s</ul>' % ''.join(lis)
    if wt == 'icon':
        return ''
    if wt in ('rating', 'star-rating'):
        title = s.get('title') or ''
        return '<p class="stars" aria-label="5 stars">★★★★★%s</p>' % (' ' + esc(title) if title else '')
    if wt == 'progress':
        return '<div class="progress"><span>%s</span><span class="bar"><span style="width:%s%%"></span></span></div>' % (
            esc(s.get('title')), (s.get('percent') or {}).get('size', 100) if isinstance(s.get('percent'), dict) else 100)
    if wt == 'portfolio':
        ids = s.get('posts_posts_ids') or []
        return portfolio_grid(ids, page)
    if wt == 'posts':
        page.ctx['post_list'] = True
        return '{% endraw %}{% include "partials/post-list.njk" %}{% raw %}'
    if wt == 'template':
        tid = s.get('template_id')
        t = BY_ID.get(int(tid)) if tid and str(tid).isdigit() else None
        data = W.elementor(t) if t else None
        return render_elements(data, page, nested=True) if data else ''
    if wt == 'form':
        return replaced_form('elementor form', page)
    if wt == 'wb-before-after-image-slider-elementor':
        b = image(s.get('before_image') or s.get('wb_before_image'), 'content', 'Before: ' + page.title)
        a = image(s.get('after_image') or s.get('wb_after_image'), 'content', 'After: ' + page.title)
        if not (a or b):
            imgs = [v for k, v in s.items() if isinstance(v, dict) and v.get('url')]
            b = image(imgs[0], 'content', 'Before: ' + page.title) if imgs else None
            a = image(imgs[1], 'content', 'After: ' + page.title) if len(imgs) > 1 else None
        return '<div class="before-after"><figure>%s<figcaption>Before</figcaption></figure><figure>%s<figcaption>After</figcaption></figure></div>' % (
            img_tag(b, page) if b else '', img_tag(a, page) if a else '')
    if wt in ('nav-menu', 'social-icons', 'search-form', 'sitemap'):
        if wt == 'social-icons':
            links = []
            for it in s.get('social_icon_list') or []:
                u = (it.get('link') or {}).get('url')
                name = ((it.get('social_icon') or {}).get('value') or '').split('-')[-1].title()
                if u:
                    links.append('<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(u), esc(name)))
            return '<p class="social">%s</p>' % ' '.join(links)
        return ''
    if wt == 'loop-grid':
        return service_loop(page)
    if wt in ('loop-carousel', 'reviews', 'testimonial-carousel'):
        return '{% endraw %}{% include "partials/testimonials.njk" %}{% raw %}'
    if wt == 'call-to-action':
        return ''
    REPORT['unknown_widgets'].setdefault(wt, []).append(page.path)
    return ''


def portfolio_grid(ids, page):
    cards = []
    for pid in ids:
        it = BY_ID.get(int(pid))
        if not it or it['status'] != 'publish':
            continue
        im = image(it['meta'].get('_thumbnail_id'), 'content', html.unescape(it['title']) + ' kitchen') if it['meta'].get('_thumbnail_id') else None
        if not im:
            # fall back to the first image in the project's gallery
            m = re.search(r'\[modula id="?(\d+)', it['meta'].get('_elementor_data') or '')
            if m:
                ims = [x for x in modula_images(m.group(1), Page(PATH_OF.get(it['id'], ''), it['title'])) if x]
                im = ims[0] if ims else None
        cards.append('<a class="card" href="%s">%s<span class="card-title">%s</span></a>' % (
            esc(PATH_OF.get(it['id'], '/portfolio/')), img_tag(im, page) if im else '', esc(html.unescape(it['title']))))
    return '<div class="card-grid">%s</div>' % ''.join(cards)


def service_loop(page):
    """Service-area 'loop grid': the service pages under this area (or its siblings)."""
    item = page.ctx.get('item')
    if not item:
        return ''
    parent = item['parent'] or item['id']
    kids = [i for i in PUBLISHED if i['type'] == 'service-area' and i['parent'] == parent]
    cards = []
    for k in sorted(kids, key=lambda x: x['menu_order']):
        desc = k['meta'].get('short_description') or ''
        im = image(k['meta'].get('service_icon'), 'logo', k['meta'].get('page_topic') or k['title']) if (k['meta'].get('service_icon') or '').isdigit() else None
        cards.append('<a class="card card-text" href="%s">%s<span class="card-title">%s</span><span class="card-desc">%s</span></a>' % (
            esc(PATH_OF[k['id']]), img_tag(im, page) if im else '', esc(html.unescape(k['title'])), esc(desc)))
    return '<div class="card-grid">%s</div>' % ''.join(cards) if cards else ''


def col_size(c):
    s = c.get('settings') or {}
    if not isinstance(s, dict):
        return 50
    return s.get('_column_size') or s.get('_inline_size') or 50


def render_elements(elements, page, nested=False):
    out = []
    for e in elements or []:
        et = e.get('elType')
        s = e.get('settings') or {}
        if not isinstance(s, dict):
            s = {}
        if s.get('hide_desktop'):
            continue
        if et in ('section', 'container'):
            out.append(render_section(e, page, nested))
        elif et == 'column':
            out.append(render_elements(e.get('elements'), page, True))
        elif et == 'widget':
            out.append(widget_html(e, page))
    return ''.join(x for x in out if x)


def render_section(e, page, nested):
    s = e.get('settings') or {}
    if not isinstance(s, dict):
        s = {}
    cols = [c for c in e.get('elements') or [] if c.get('elType') == 'column' and not (c.get('settings') or {}).get('hide_desktop')]
    inner_parts = []
    if cols and all(c.get('elType') == 'column' for c in e.get('elements') or []):
        rendered = [(col_size(c), render_elements(c.get('elements'), page, True)) for c in cols]
        filled = [(sz, h) for sz, h in rendered if h.strip()]
        if len(filled) > 1:
            tmpl = ' '.join('%sfr' % round(float(sz)) for sz, _ in filled)
            inner_parts.append('<div class="el-row" style="--cols:%s">%s</div>' % (
                tmpl, ''.join('<div class="el-col">%s</div>' % h for _, h in filled)))
        elif filled:
            inner_parts.append(filled[0][1])
    else:  # flexbox container
        inner_parts.append(render_elements(e.get('elements'), page, True))
    inner = ''.join(inner_parts)
    bg = setting(s, 'background_image', page)
    bg_html = ''
    if isinstance(bg, dict) and (bg.get('url') or bg.get('id')) and not nested:
        text_only = re.sub(r'<[^>]+>', '', inner).strip()
        im = image(bg, 'hero', page.title)
        if im:
            bg_html = img_tag(im, page, cls='band-img')
            if not text_only:
                return '<section class="band band-photo">%s</section>' % bg_html
    if not inner.strip():
        return ''
    anchor = s.get('_element_id')
    aid = ' id="%s"' % esc(anchor) if anchor else ''
    if nested:
        return '<div class="el-block"%s>%s</div>' % (aid, inner)
    if bg_html:
        return '<section class="band band-photo band-photo-text"%s>%s<div class="wrap"><div class="band-card">%s</div></div></section>' % (aid, bg_html, inner)
    return '<section class="band"%s><div class="wrap">%s</div></section>' % (aid, inner)


# ------------------------------------------------------------------------------------------
# SEO (Yoast) resolution
# ------------------------------------------------------------------------------------------
SEP = '|'


def yoast_vars(s, item):
    title = html.unescape(item['title'])
    s = s.replace('%%title%%', title).replace('%%sitename%%', 'Singer Kitchens').replace('%%sep%%', SEP)
    s = s.replace('%%page%%', '').replace('%%sitedesc%%', EXP['tagline'] or '')
    s = s.replace('%%primary_category%%', '').replace('%%category%%', '')
    s = re.sub(r'%%[a-z_]+%%', '', s)
    s = re.sub(r'\s+', ' ', s).replace(' ' + SEP + ' ' + SEP, ' ' + SEP).strip()
    return s


def text_excerpt(raw, limit=156):
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', raw or '', flags=re.S)
    t = re.sub(r'\[[^\]]+\]', '', t)
    t = re.sub(r'</?(p|div|h\d|li|ul|ol|br|tr|td|figure|figcaption|section|blockquote)[^>]*>', ' ', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = html.unescape(t)
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) <= limit:
        return t
    cut = t[:limit]
    if ' ' in cut:
        cut = cut[:cut.rfind(' ')]
    return cut.rstrip(' ,;:')


def seo_for(item):
    m = item['meta']
    yt = m.get('_yoast_wpseo_title')
    if yt:
        title = yoast_vars(yt, item)
        title_src = 'yoast'
    else:
        title = '%s %s Singer Kitchens %s Kitchen Remodeling New Orleans' % (html.unescape(item['title']), SEP, SEP)
        title_src = 'template'
    md = m.get('_yoast_wpseo_metadesc')
    if md:
        desc = yoast_vars(md, item)
        desc = desc.replace('[[++service_phone]]', MAIN_PHONE)
        desc_src = 'yoast'
    else:
        desc = text_excerpt(item['content'])
        desc_src = 'excerpt'
    noindex = m.get('_yoast_wpseo_meta-robots-noindex') == '1'
    return dict(title=title, description=desc, noindex=noindex, title_src=title_src, desc_src=desc_src,
                canonical=m.get('_yoast_wpseo_canonical') or '')


# ------------------------------------------------------------------------------------------
# Writers
# ------------------------------------------------------------------------------------------
def fm(d):
    return '---json\n' + json.dumps(d, indent=2, ensure_ascii=False) + '\n---\n'


def page_file_name(path):
    n = path.strip('/').replace('/', '--') or 'home'
    return n


def raw_wrap(body):
    body = body.replace('{% raw %}{% endraw %}', '')
    return '{% raw %}' + body + '{% endraw %}'


def insert_before_final_cta(body, include):
    """Insert an include before the last top-level band that holds a button (the final call to action)."""
    bands = [m.start() for m in re.finditer(r'<section class="band', body)]
    for start in reversed(bands):
        seg = body[start:]
        if 'class="btn' in seg or 'ghl-form' in seg:
            # only accept if this band is in the last third of the page
            if start > len(body) * 0.5:
                return body[:start] + '{% endraw %}' + include + '{% raw %}' + body[start:]
            break
    return body + '{% endraw %}' + include + '{% raw %}'


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


PAGES_INDEX = []


def convert_page(item):
    path = PATH_OF[item['id']]
    title = html.unescape(item['title'])
    page = Page(path, title, {'item': item, 'acf': item['meta'], 'item_title': title})
    data = W.elementor(item)
    if data:
        body = render_elements(data, page)
        source = 'elementor'
    else:
        body = '<section class="band"><div class="wrap prose">%s</div></section>' % clean_html(wpautop(item['content']), page)
        source = 'post_content'
    seo = seo_for(item)
    core = path in CORE_PATHS
    d = {
        'layout': 'layouts/page.njk', 'title': title, 'seoTitle': seo['title'], 'description': seo['description'],
        'permalink': path, 'core': core, 'wpId': item['id'], 'source': source,
        'published': item['date'], 'modified': item['modified'],
    }
    if seo['noindex'] or re.search(r'thank-you|thank_you', path):
        d['noindex'] = True
    if page.og_image:
        d['ogImage'] = page.og_image
    if page.h1s:
        d['h1'] = page.h1s[0]
    if page.ctx.get('forms'):
        d['forms'] = sorted(set(re.sub(r'.*/form/', '', f) for f in page.ctx['forms']))
    if path in PROCESS_STRIP_PATHS:
        body = insert_before_final_cta(body, '{% include "partials/process-strip.njk" %}')
        d['processStrip'] = True
    if path == '/our-process/':
        # four steps in full, right after the existing H1 and subhead
        marker = '<h3>Your Vision. Our Expertise.</h3>'
        assert marker in body, 'our-process subhead not found'
        i = body.index(marker) + len(marker)
        # close the open band so the timeline is its own full-width section, then reopen
        body = body[:i] + '</div></div></section>{% endraw %}{% include "partials/process-timeline.njk" %}{% raw %}<section class="band"><div class="wrap"><div class="el-block">' + body[i:]
        btn = '<p class="btn-row"><a class="btn" href="/request-consultation/">Request a Free Design Consultation</a></p>'
        assert btn in body, 'our-process showroom button not found'
        body = body.replace(btn, '{% endraw %}{% include "partials/showroom-cards.njk" %}{% raw %}' + btn, 1)
        d['processTimeline'] = True
    if path == '/request-consultation/':
        j = body.index('ghl-form')
        k = body.index('</section>', j) + len('</section>')
        body = body[:k] + '{% endraw %}{% include "partials/next-steps.njk" %}{% raw %}' + body[k:]
        d['nextSteps'] = True
    if page.ctx.get('standalone_html'):
        tool_name = page_file_name(path)
        write(os.path.join(SRC, 'embedded-tools', tool_name + '.html'), page.ctx['standalone_html'])
        d['embeddedTool'] = '/embedded-tools/%s.html' % tool_name
    if path in REDIRECTED_PAGES:
        # kept in the repo for reference, not published: netlify.toml 301s this URL (see README)
        d['permalink'] = False
        d['eleventyExcludeFromCollections'] = True
        d['redirectedTo'] = REDIRECTED_PAGES[path]
    if path == '/blog/':
        d['pagination'] = {'data': 'collections.posts', 'size': 9, 'alias': 'postsPage'}
        d['permalink'] = "{% if pagination.pageNumber > 0 %}/blog/{{ pagination.pageNumber + 1 }}/{% else %}/blog/{% endif %}"
        d['blogIndex'] = True
    bespoke = BESPOKE.get(path)
    PAGES_INDEX.append({'path': path, 'title': title, 'core': core, 'type': 'page', 'id': item['id'], 'seo': seo,
                        'bespoke': bool(bespoke)})
    if bespoke:
        # still save the converted body for reference / text checks
        write(os.path.join(ROOT, 'reports', 'converted', page_file_name(path) + '.html'), body)
        return
    write(os.path.join(SRC, 'pages', page_file_name(path) + '.njk'), fm(d) + raw_wrap(body) + '\n')


def convert_post(item):
    path = PATH_OF[item['id']]
    title = html.unescape(item['title'])
    page = Page(path, title, {'item': item})
    data = W.elementor(item)
    if data:
        body = render_elements(data, page)
        # posts render inside the post layout's wrap; strip band wrappers to keep a single column
        body = re.sub(r'<section class="band"><div class="wrap">', '<div class="post-section">', body)
        body = body.replace('</div></section>', '</div>')
    else:
        body = clean_html(wpautop(item['content']), page)
    seo = seo_for(item)
    thumb = item['meta'].get('_thumbnail_id')
    feat = image(int(thumb), 'hero', title) if thumb and thumb.isdigit() else None
    cats = [c[2] for c in item['cats'] if c[0] == 'category']
    tags = [c[2] for c in item['cats'] if c[0] == 'post_tag']
    excerpt = text_excerpt(item['excerpt']) if item['excerpt'] else text_excerpt(body, 160)
    d = {'layout': 'layouts/post.njk', 'title': title, 'seoTitle': seo['title'], 'description': seo['description'],
         'date': item['date'].replace(' ', 'T'), 'modified': item['modified'], 'permalink': path, 'excerpt': excerpt,
         'categories': cats, 'tags': ['posts'], 'wpTags': tags, 'author': item['creator'], 'wpId': item['id']}
    if feat:
        d['image'] = feat
    elif page.og_image:
        d['ogImage'] = page.og_image
    if seo['noindex']:
        d['noindex'] = True
    body = re.sub(r'\n\s*\n', '\n', body)
    body = re.sub(r'(?m)^[ \t]+', '', body)
    # markdown file whose body is a single HTML block (Markdown can be added by editors)
    write(os.path.join(SRC, 'posts', item['slug'] + '.md'), fm(d) + '<div class="post-body">' + body.replace('{%', '{ %').replace('{{', '{ {') + '</div>\n')
    PAGES_INDEX.append({'path': path, 'title': title, 'core': False, 'type': 'post', 'id': item['id'], 'seo': seo})


SERVICE_TEMPLATE = W.elementor(BY_ID[6945])


def convert_service_area(item):
    path = PATH_OF[item['id']]
    title = html.unescape(item['title'])
    page = Page(path, title, {'item': item, 'acf': item['meta'], 'item_title': title})
    body = render_elements(SERVICE_TEMPLATE, page)
    seo = seo_for(item)
    d = {'layout': 'layouts/page.njk', 'title': title, 'seoTitle': seo['title'], 'description': seo['description'],
         'permalink': path, 'core': False, 'wpId': item['id'], 'source': 'service-area template 6945 + ACF fields',
         'serviceArea': item['meta'].get('service_area'), 'published': item['date'], 'modified': item['modified']}
    if page.og_image:
        d['ogImage'] = page.og_image
    schema = item['meta'].get('location_schema')
    if schema:
        try:
            json.loads(schema)
            d['extraSchema'] = schema
        except Exception:
            REPORT['notes'].append('Invalid location schema JSON on %s (dropped)' % path)
    write(os.path.join(SRC, 'pages', page_file_name(path) + '.njk'), fm(d) + raw_wrap(body) + '\n')
    PAGES_INDEX.append({'path': path, 'title': title, 'core': False, 'type': 'service-area', 'id': item['id'], 'seo': seo})


def main():
    for d in ('pages', 'posts'):
        shutil.rmtree(os.path.join(SRC, d), ignore_errors=True)
    for item in PUBLISHED:
        if item['type'] == 'page':
            convert_page(item)
        elif item['type'] == 'post':
            convert_post(item)
        elif item['type'] == 'service-area':
            convert_service_area(item)
    os.makedirs(os.path.join(SRC, '_data', 'generated'), exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)
    # images used by hand-built templates (home page etc.)
    # extra images used only by hand-built templates
    for sr in json.load(open(os.path.join(SRC, '_data', 'showrooms.json'))):
        for ph in sr['photos']:
            image_for_file(ph['file'], 'content', context=sr['name'])
    for f in HOME_HERO_FILES:
        image_for_file(f, 'hero', context='Singer Kitchens kitchen')
    manifest = {}
    for (rel, role), v in IMG_CACHE.items():
        key = v['orig'] + ('#hero' if role == 'hero' else ('#sm' if role == 'logo' else ''))
        manifest[key] = {k: v[k] for k in ('src', 'w', 'h', 'alt')}
    write(os.path.join(SRC, '_data', 'generated', 'images.json'), json.dumps(manifest, indent=1, sort_keys=True))
    write(os.path.join(REPORTS, 'pages-index.json'), json.dumps(PAGES_INDEX, indent=1, ensure_ascii=False))
    REPORT['missing_images'] = [dict(t) for t in {tuple(sorted(x.items())) for x in REPORT['missing_images']}]
    write(os.path.join(REPORTS, 'convert-report.json'), json.dumps(REPORT, indent=1, ensure_ascii=False))
    print('pages/posts/areas:', len(PAGES_INDEX), 'images:', len(IMG_CACHE))
    print('missing images:', len(REPORT['missing_images']))
    print('unknown widgets:', {k: len(v) for k, v in REPORT['unknown_widgets'].items()})
    print('replaced forms:', len(REPORT['replaced_forms']))


if __name__ == '__main__':
    main()
