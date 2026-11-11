"""Shared helpers for reading the WordPress export (XML) used by convert_wp.py and the checks.

The export and the uploads folder live in source/ (git-ignored). Nothing here touches the network.
"""
import json
import re
import xml.etree.ElementTree as ET

NS = {
    'wp': 'http://wordpress.org/export/1.2/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'excerpt': 'http://wordpress.org/export/1.2/excerpt/',
    'dc': 'http://purl.org/dc/elements/1.1/',
}
SITE = 'https://www.singerkitchens.com'


def load(path):
    root = ET.parse(path).getroot()
    ch = root.find('channel')
    items = []
    for it in ch.findall('item'):
        g = lambda p: it.findtext(p, namespaces=NS)
        meta = {}
        for m in it.findall('wp:postmeta', NS):
            meta[m.findtext('wp:meta_key', namespaces=NS)] = m.findtext('wp:meta_value', namespaces=NS)
        cats = [(c.get('domain'), c.get('nicename'), c.text) for c in it.findall('category')]
        items.append(dict(
            id=int(g('wp:post_id')), type=g('wp:post_type'), status=g('wp:status'),
            title=it.findtext('title') or '', link=it.findtext('link') or '', slug=g('wp:post_name') or '',
            parent=int(g('wp:post_parent') or 0), menu_order=int(g('wp:menu_order') or 0),
            date=g('wp:post_date'), modified=g('wp:post_modified'),
            content=g('content:encoded') or '', excerpt=g('excerpt:encoded') or '',
            attachment_url=g('wp:attachment_url'), meta=meta, cats=cats, creator=g('dc:creator')))
    return dict(title=ch.findtext('title'), tagline=ch.findtext('description'), items=items)


def path_of(item):
    """Site-relative URL path for an item (e.g. /about/)."""
    link = item['link'] or ''
    p = re.sub(r'^https?://(www\.)?singerkitchens\.com', '', link)
    return p or '/'


# --- PHP unserialize (enough for WordPress meta) ------------------------------------------
def php_unserialize(s):
    if not s:
        return None
    b = s.encode('utf-8')
    pos = [0]

    def read_until(ch):
        i = b.index(ch, pos[0])
        v = b[pos[0]:i]
        pos[0] = i + 1
        return v

    def parse():
        t = b[pos[0]:pos[0] + 1]
        pos[0] += 2
        if t == b'N':
            return None
        if t == b'b':
            return read_until(b';') == b'1'
        if t == b'i':
            return int(read_until(b';'))
        if t == b'd':
            return float(read_until(b';'))
        if t == b's':
            n = int(read_until(b':'))
            pos[0] += 1  # opening quote
            v = b[pos[0]:pos[0] + n].decode('utf-8', 'replace')
            pos[0] += n + 2  # closing quote and ;
            return v
        if t == b'a':
            n = int(read_until(b':'))
            pos[0] += 1  # {
            out = {}
            for _ in range(n):
                k = parse()
                out[k] = parse()
            pos[0] += 1  # }
            if all(isinstance(k, int) for k in out) and list(out) == list(range(len(out))):
                return [out[k] for k in range(len(out))]
            return out
        raise ValueError('unsupported php type %r at %d' % (t, pos[0]))

    try:
        return parse()
    except Exception:
        return None


def elementor(item):
    raw = item['meta'].get('_elementor_data')
    if not raw or len(raw) < 3:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None
