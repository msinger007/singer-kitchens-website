#!/usr/bin/env python3
"""Static check of _site: every local src/href resolves to a built file (or a netlify.toml redirect)."""
import os, re, sys, tomllib, html
from urllib.parse import unquote, urlparse
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = os.path.join(ROOT, '_site')
redirects = {r['from'] for r in tomllib.load(open(os.path.join(ROOT, 'netlify.toml'), 'rb')).get('redirects', [])}
missing = {}
for d, _, fs in os.walk(SITE):
    for f in fs:
        if not f.endswith('.html') or 'embedded-tools' in d:
            continue
        page = '/' + os.path.relpath(os.path.join(d, f), SITE)
        h = open(os.path.join(d, f), encoding='utf-8').read()
        for attr, url in re.findall(r'\s(src|href)="([^"]+)"', h):
            url = html.unescape(url)
            if not url.startswith('/') or url.startswith('//'):
                continue
            p = unquote(urlparse(url).path)
            target = os.path.join(SITE, p.lstrip('/'))
            ok = os.path.isfile(target) or os.path.isfile(os.path.join(target, 'index.html')) or p in redirects or p.rstrip('/') in redirects
            if not ok:
                missing.setdefault(p, set()).add(page)
for p, pages in sorted(missing.items()):
    print('MISSING', p, '<-', ', '.join(sorted(pages)[:4]))
print('local links/images missing:', len(missing))
sys.exit(1 if missing else 0)
