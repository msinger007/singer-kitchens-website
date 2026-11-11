#!/usr/bin/env python3
"""Pre-launch SEO scan of the built site (_site).

Finds: broken internal links, links that go through a redirect, absolute links to the old domain,
Google-redirect-wrapped links, http:// links, external links (optionally checked online with --external),
duplicate / missing / over-long titles and meta descriptions, missing or multiple H1s, noindex pages in
the sitemap, and dated content (years, "COVID", hurricane, giveaway, "new for 2021", etc.).

Usage: npm run build && python3 tools/seo_scan.py [--external]
Writes reports/seo-scan.json and reports/seo-scan.md.
"""
import collections, concurrent.futures, html, json, os, re, sys, tomllib, urllib.request, ssl
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote, parse_qs

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = os.path.join(ROOT, '_site')
DOMAINS = ('www.singerkitchens.com', 'singerkitchens.com')
YEAR_NOW = 2026
REDIRECTS = {}
for r in tomllib.load(open(os.path.join(ROOT, 'netlify.toml'), 'rb')).get('redirects', []):
    if not r.get('query'):
        REDIRECTS[r['from']] = r['to']
DATED = re.compile(r'\b(20(?:1\d|2[0-5]))\b|\bcovid\b|coronavirus|pandemic|social distanc|hurricane ida|\bgiveaway\b|'
                   r'\bthis (?:year|spring|summer|fall|winter)\b|\bnew for\b|\blimited time\b|\bexpires?\b', re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ''; self.desc = None; self.canonical = None; self.robots = ''
        self.h1 = []; self.links = []; self.imgs = []; self.text = []
        self._in = None; self._skip = 0; self._buf = ''; self._main = 0; self._chrome = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self._skip += 1
        if tag == 'main':
            self._main = 1
        if tag == 'title':
            self._in = 'title'; self._buf = ''
        elif tag == 'h1':
            self._in = 'h1'; self._buf = ''
        elif tag == 'meta' and a.get('name') == 'description':
            self.desc = a.get('content', '')
        elif tag == 'meta' and a.get('name') == 'robots':
            self.robots = a.get('content', '')
        elif tag == 'link' and a.get('rel') == 'canonical':
            self.canonical = a.get('href')
        elif tag == 'a' and a.get('href'):
            self.links.append((a['href'], not self._main))
        elif tag in ('img', 'iframe', 'source') and a.get('src'):
            self.imgs.append(a['src'])

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self._skip:
            self._skip -= 1
        if tag == 'main':
            self._main = 0
        if tag == 'title' and self._in == 'title':
            self.title = self._buf.strip(); self._in = None
        elif tag == 'h1' and self._in == 'h1':
            self.h1.append(re.sub(r'\s+', ' ', self._buf).strip()); self._in = None

    def handle_data(self, d):
        if self._in:
            self._buf += d
        if not self._skip and self._main:
            self.text.append(d)


def built_path_exists(p):
    t = os.path.join(SITE, unquote(p).lstrip('/'))
    return os.path.isfile(t) or os.path.isfile(os.path.join(t, 'index.html'))


def load_pages():
    pages = {}
    for d, _, fs in os.walk(SITE):
        if 'embedded-tools' in d:
            continue
        for f in fs:
            if f != 'index.html' and not (f.endswith('.html') and f != 'index.html'):
                continue
            rel = '/' + os.path.relpath(os.path.join(d, f), SITE)
            url = rel[:-len('index.html')] if rel.endswith('index.html') else rel
            p = Page(); p.feed(open(os.path.join(d, f), encoding='utf-8').read())
            pages[url] = p
    return pages


def main():
    check_external = '--external' in sys.argv
    pages = load_pages()
    sitemap = set(re.findall(r'<loc>https?://[^/]+(/[^<]*)</loc>', open(os.path.join(SITE, 'sitemap.xml')).read()))
    out = {k: [] for k in ('broken_internal', 'via_redirect', 'old_domain_absolute', 'google_wrapped', 'http_links',
                           'external', 'missing_title', 'missing_desc', 'long_title', 'long_desc', 'short_desc',
                           'h1_none', 'h1_multi', 'noindex_in_sitemap', 'dated')}
    titles = collections.defaultdict(list); descs = collections.defaultdict(list)
    ext = collections.defaultdict(set)
    for url, p in sorted(pages.items()):
        if url in ('/404.html',):
            continue
        noindex = 'noindex' in p.robots
        if not noindex:
            titles[p.title].append(url)
            if p.desc:
                descs[p.desc].append(url)
        if noindex and url in sitemap:
            out['noindex_in_sitemap'].append(url)
        if not p.title: out['missing_title'].append(url)
        elif len(p.title) > 65 and not noindex: out['long_title'].append((url, len(p.title), p.title))
        if not p.desc and not noindex: out['missing_desc'].append(url)
        elif p.desc and len(p.desc) > 165 and not noindex: out['long_desc'].append((url, len(p.desc)))
        elif p.desc and len(p.desc) < 70 and not noindex: out['short_desc'].append((url, len(p.desc), p.desc))
        if not noindex:
            if not p.h1: out['h1_none'].append(url)
            elif len(p.h1) > 1: out['h1_multi'].append((url, p.h1))
        for href, chrome in p.links:
            h = html.unescape(href)
            u = urlparse(h)
            if u.scheme in ('mailto', 'tel', 'sms', 'javascript') or h.startswith('#'):
                continue
            if u.netloc in ('www.google.com', 'google.com') and u.path == '/url':
                out['google_wrapped'].append((url, (parse_qs(u.query).get('q') or [''])[0]))
                continue
            if u.netloc in DOMAINS:
                out['old_domain_absolute'].append((url, h))
                path = u.path or '/'
            elif not u.netloc:
                if not h.startswith('/'):
                    continue
                path = u.path
            else:
                if u.scheme == 'http':
                    out['http_links'].append((url, h))
                if not chrome:
                    ext[h].add(url)
                continue
            if path.startswith('/.netlify/'):
                continue
            norm = path if path.endswith('/') or '.' in path.rsplit('/', 1)[-1] else path + '/'
            if built_path_exists(path) or built_path_exists(norm):
                continue
            tgt = REDIRECTS.get(path) or REDIRECTS.get(norm) or REDIRECTS.get(path.rstrip('/'))
            if tgt is None and any(path.startswith(f.rstrip('*')) for f in REDIRECTS if f.endswith('*')):
                tgt = '(wildcard redirect)'
            if tgt:
                out['via_redirect'].append((url, path, tgt))
            else:
                out['broken_internal'].append((url, path))
        text = re.sub(r'\s+', ' ', ' '.join(p.text))
        hits = []
        for m in DATED.finditer(text):
            s = text[max(0, m.start() - 70): m.end() + 70].strip()
            hits.append(s)
        dated_title = bool(re.search(r'\b20(1\d|2[0-5])\b', p.title + ' ' + ' '.join(p.h1)))
        if hits or dated_title:
            out['dated'].append({'url': url, 'title': p.title, 'h1': p.h1, 'dated_title': dated_title,
                                 'hits': len(hits), 'samples': hits[:4]})
    out['dup_titles'] = {t: u for t, u in titles.items() if len(u) > 1}
    out['dup_descs'] = {d: u for d, u in descs.items() if len(u) > 1}
    out['external_count'] = len(ext)
    if check_external:
        ctx = ssl.create_default_context(cafile=os.environ.get('SSL_CERT_FILE') or None)

        def probe(link):
            for method in ('HEAD', 'GET'):
                try:
                    req = urllib.request.Request(link, method=method, headers={'User-Agent': 'Mozilla/5.0 (link check)'})
                    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                        return link, r.status, r.geturl()
                except urllib.error.HTTPError as e:
                    if method == 'HEAD' and e.code in (403, 405, 400, 404, 429, 500, 501):
                        continue
                    return link, e.code, ''
                except Exception as e:
                    if method == 'HEAD':
                        continue
                    return link, 'ERR ' + type(e).__name__ + ' ' + str(e)[:80], ''
        with concurrent.futures.ThreadPoolExecutor(16) as ex:
            for link, status, final in ex.map(probe, sorted(ext)):
                ok = isinstance(status, int) and 200 <= status < 300
                if not ok or (final and urlparse(final).netloc.replace('www.', '').split(':')[0] != urlparse(link).netloc.replace('www.', '')):
                    out['external'].append({'link': link, 'status': status, 'final': final, 'pages': sorted(ext[link])})
    json.dump(out, open(os.path.join(ROOT, 'reports', 'seo-scan.json'), 'w'), indent=1, default=list)
    for k, v in out.items():
        print(k, len(v) if hasattr(v, '__len__') else v)


if __name__ == '__main__':
    main()
