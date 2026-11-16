"""Put the Modula / WordPress gallery photos back into the pages where the converter left empty galleries.

Why: convert_wp.py expanded each [modula] / [gallery] shortcode into local <img src="/images/..."> tags and then
ran the HTML cleaner over them, which dropped any <img> not pointing at /wp-content/uploads/. The result was an
empty <div><figure></figure>...</div> on every portfolio project page and on 18 blog posts.

reports/restored-galleries.json lists, for each file, its galleries in page order and the photos in each
(manifest keys from src/_data/generated/images.json). It was read from the live WordPress site's
Modula and [gallery] markup in November 2026; every gallery's photo count matched the empty slots here.

Run:  python3 tools/restore_galleries.py   (safe to re-run: files already restored have no empty galleries left)
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = json.load(open(os.path.join(ROOT, 'src', '_data', 'generated', 'images.json')))
DATA = json.load(open(os.path.join(ROOT, 'reports', 'restored-galleries.json')))
EMPTY = re.compile(r'(?:<p>)?<div>((?:<figure></figure>)+)</div>(?:</p>)?')
# Thumbnails show at roughly a third of the content width on desktop, half on phones.
SIZES = '(max-width: 600px) 50vw, (max-width: 1100px) 33vw, 400px'


def esc(s):
    return html.escape(str(s or ''), quote=True)


def gallery(keys):
    items = []
    for k in keys:
        im = MANIFEST[k]
        items.append(
            '<a class="gallery-item" href="%s"><img src="%s" alt="%s" sizes="%s" width="%d" height="%d" '
            'loading="lazy" decoding="async"></a>' % (esc(im['src']), esc(im['src']), esc(im['alt']), SIZES, im['w'], im['h']))
    return '<div class="gallery">%s</div>' % ''.join(items)


def main():
    done = 0
    for rel, groups in sorted(DATA.items()):
        path = os.path.join(ROOT, rel)
        text = open(path, encoding='utf-8').read()
        slots = EMPTY.findall(text)
        if not slots:
            continue
        counts = [s.count('<figure>') for s in slots]
        if counts != [len(g) for g in groups]:
            raise SystemExit('%s: empty galleries %s do not match the saved list %s' % (rel, counts, [len(g) for g in groups]))
        it = iter(groups)
        text = EMPTY.sub(lambda m: gallery(next(it)), text)
        open(path, 'w', encoding='utf-8').write(text)
        done += 1
        print('restored %-90s %s' % (rel, counts))
    print('%d files restored' % done)


if __name__ == '__main__':
    main()
