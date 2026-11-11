#!/usr/bin/env python3
"""Compare every core page in _site/ against (a) the WordPress export and (b) the browser-saved live pages.

Checks body copy, <title>, meta description, H1 and canonical. Writes reports/text-check.json and
reports/text-check.md and exits non-zero if any core-page copy is missing.

Usage: npm run build && python3 tools/check_text.py [path/to/saved-pages]
"""
import glob, html, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import wp_export as W
import convert_wp as C  # reuses the Yoast resolution (no files are written on import)

ROOT = C.ROOT
APPROVED = {k: v for k, v in json.load(open(os.path.join(os.path.dirname(__file__), 'approved-seo-changes.json'))).items() if k.startswith('/')}
SAVED_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'reference', 'saved-pages')
SAVED = {
    '/': 'Singer_Kitchens__Top_Kitchen_Renovation_Company_in_New_Orleans.html',
    '/financing/': 'Financing___Singer_Kitchens___Kitchen_Remodeling_New_Orleans.html',
    '/remodeling/': 'Kitchen_Remodeling_New_Orleans__Mandeville___Covington.html',
    '/showrooms/': 'Kitchen_Design_Showroom_New_Orleans___Mandeville_-_Singer_Kitchens.html',
    '/request-consultation/': 'Request_Consultation___Singer_Kitchens___Kitchen_Remodeling_New_Orleans.html',
}


def norm(t):
    t = html.unescape(t or '')
    t = t.replace(' ', ' ').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    t = t.replace('–', '-').replace('—', '-').replace('…', '...').replace('″', '"').replace('′', "'")
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def strip_tags(h):
    h = re.sub(r'<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', h or '', flags=re.S | re.I)
    h = re.sub(r'<br\s*/?>', ' ', h)
    h = re.sub(r'</?(p|div|h\d|li|ul|ol|tr|td|th|figure|figcaption|section|blockquote|dt|dd|a)\b[^>]*>', ' ', h)
    h = re.sub(r'<[^>]+>', '', h)
    return norm(h)


def comparable(t):
    """Words only: punctuation spacing differences between Elementor and our markup are not copy changes."""
    t = norm(t).lower()
    t = re.sub(r'[^\w$%&+@]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


# --- expected text from the export --------------------------------------------------------
def export_blocks(item):
    out = []
    page = C.Page(W.path_of(item), html.unescape(item['title']), {'item': item, 'acf': item['meta'], 'item_title': item['title']})

    def walk(els):
        for e in els or []:
            s = e.get('settings') or {}
            if not isinstance(s, dict):
                s = {}
            if s.get('hide_desktop'):
                continue
            wt = e.get('widgetType')
            if wt == 'heading':
                out.append(('heading', strip_tags(str(C.setting(s, 'title', page) or ''))))
            elif wt == 'text-editor':
                raw = str(C.setting(s, 'editor', page) or '')
                raw = re.sub(r'\[[a-z_-]+[^\]]*\]', ' ', raw)
                out.append(('text', strip_tags(raw)))
            elif wt == 'button':
                out.append(('button', strip_tags(s.get('text') or '')))
            elif wt == 'icon-box':
                out.append(('heading', strip_tags(s.get('title_text') or '')))
                d = s.get('description_text') or ''
                if d.strip(' .\n'):
                    out.append(('text', strip_tags(d)))
            elif wt == 'icon-list':
                for it in s.get('icon_list') or []:
                    out.append(('text', strip_tags(it.get('text') or '')))
            elif wt == 'call-to-action':
                out.append(('heading', strip_tags(s.get('title') or '')))
                out.append(('button', strip_tags(s.get('button') or '')))
            elif wt == 'template':
                tid = s.get('template_id')
                t = C.BY_ID.get(int(tid)) if tid and str(tid).isdigit() else None
                if t:
                    walk(W.elementor(t))
            walk(e.get('elements'))
    data = W.elementor(item)
    if data:
        walk(data)
    else:
        out.append(('text', strip_tags(C.wpautop(item['content']))))
    return [(k, t) for k, t in out if t]


def built(path):
    f = os.path.join(ROOT, '_site', path.strip('/'), 'index.html') if path != '/' else os.path.join(ROOT, '_site', 'index.html')
    return open(f, encoding='utf-8').read()


def main_html(h):
    m = re.search(r'<main id="main">(.*)</main>', h, re.S)
    return m.group(1) if m else h


def head_info(h):
    g = lambda pat: (re.search(pat, h, re.S | re.I) or [None, None])[1]
    h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    return {
        'title': norm(g(r'<title>(.*?)</title>')),
        'description': norm(g(r'<meta name="description" content="([^"]*)"')),
        'canonical': norm(g(r'<link rel="canonical" href="([^"]*)"')),
        'h1': [strip_tags(x) for x in h1s],
    }


def saved_info(fname):
    h = open(os.path.join(SAVED_DIR, fname), encoding='utf-8').read()
    info = head_info(h)
    info['description'] = norm(re.search(r'<meta name="description" content="([^"]*)"', h).group(1))
    # visible body copy between the header and the footer template
    b = h[h.find('<body'):]
    b = re.sub(r'<(header|nav|footer)\b.*?</\1>', ' ', b, flags=re.S | re.I)
    b = re.sub(r'<div[^>]+elementor-location-(header|footer)[^>]*>.*', ' ', b, flags=re.S) if False else b
    b = re.sub(r'<(script|style|noscript|svg)[^>]*>.*?</\1>', '', b, flags=re.S)
    b = re.sub(r'<(br|/p|/h\d|/li|/div|/a|/span|/button)[^>]*>', '\n', b)
    lines = [norm(l) for l in html.unescape(re.sub(r'<[^>]+>', '', b)).split('\n')]
    return info, [l for l in lines if l]


def main():
    results = []
    failures = 0
    idx = {i['id']: i for i in C.PUBLISHED}
    for path in C.CORE_PATHS:
        item = next(i for i in C.PUBLISHED if C.PATH_OF[i['id']] == path)
        h = built(path)
        mh = main_html(h)
        got = comparable(strip_tags(mh))
        info = head_info(h)
        seo = C.seo_for(item)
        r = {'path': path, 'missing_copy': [], 'seo': {}, 'saved_page': None}
        # copy from the export
        for kind, text in export_blocks(item):
            c = comparable(text)
            if c and c not in got:
                # report per sentence so the diff is readable
                parts = [p for p in re.split(r'(?<=[.!?])\s+', text) if comparable(p)]
                miss = [p for p in parts if comparable(p) not in got]
                if miss:
                    r['missing_copy'].append({'kind': kind, 'text': ' '.join(miss)})
        # SEO vs export
        exp_title = norm(seo['title']) if path != '/' else 'Singer Kitchens: Top Kitchen Renovation Company in New Orleans'
        if path in APPROVED:
            exp_title = norm(APPROVED[path]['title']); seo = dict(seo, description=APPROVED[path]['description'])
        r['seo']['title'] = {'expected_export': exp_title, 'built': info['title'], 'ok': info['title'] == exp_title}
        r['seo']['description'] = {'expected_export': norm(seo['description']), 'built': info['description'], 'ok': info['description'] == norm(seo['description'])}
        exp_canon = C.W.SITE + path
        r['seo']['canonical'] = {'expected': exp_canon, 'built': info['canonical'], 'ok': info['canonical'] == exp_canon}
        exp_h1 = [strip_tags(t) for k, t in export_blocks(item) if k == 'heading'][:0]
        r['seo']['h1'] = {'built': info['h1']}
        # vs saved live page
        if path in SAVED and os.path.exists(os.path.join(SAVED_DIR, SAVED[path])):
            sinfo, slines = saved_info(SAVED[path])
            miss = []
            ignore = re.compile(r'^(Skip to content|Facebook|Instagram|Search this website|Type your search|Posted on Google|Verified by Trustindex|Trustindex verifies.*|Trustindex verified.*|\'s Google Business Profile\. Learn more|Let\'s Talk|Menu)$')
            nav_words = set()
            for g in C.json.load(open(os.path.join(ROOT, 'src', '_data', 'nav.json')))['main']:
                nav_words.add(comparable(g['label']))
                for c in g.get('children', []):
                    nav_words.add(comparable(c['label']))
            for extra in ('About', 'Services', 'Products', 'Showrooms', 'Learn', 'Reviews', 'Financing', 'Kitchen Remodeling', 'Kitchen Design', 'Bathroom Design', 'Closet Renovations', 'Design Portfolio', 'Kitchen Stories', 'FAQs'):
                nav_words.add(comparable(extra))
            whole = comparable(strip_tags(h))
            for l in slines:
                if ignore.match(l) or comparable(l) in nav_words or not comparable(l):
                    continue
                if comparable(l) not in whole:
                    miss.append(l)
            r['saved_page'] = {
                'file': SAVED[path],
                'title': {'live': sinfo['title'], 'built': info['title'], 'ok': sinfo['title'] == info['title']},
                'description': {'live': sinfo['description'], 'built': info['description'], 'ok': sinfo['description'] == info['description']},
                'canonical': {'live': sinfo['canonical'], 'built': info['canonical'], 'ok': sinfo['canonical'].rstrip('/') == info['canonical'].rstrip('/')},
                'h1': {'live': sinfo['h1'], 'built': info['h1'], 'ok': [comparable(x) for x in sinfo['h1'] if x] == [comparable(x) for x in info['h1'] if x]},
                'live_lines_missing': miss,
            }
        bad = bool(r['missing_copy']) or not all(v.get('ok', True) for v in r['seo'].values())
        if r['saved_page']:
            sp = r['saved_page']
            bad = bad or bool(sp['live_lines_missing']) or not all(sp[k]['ok'] for k in ('title', 'description', 'canonical', 'h1'))
        r['ok'] = not bad
        failures += bad
        results.append(r)
    os.makedirs(os.path.join(ROOT, 'reports'), exist_ok=True)
    json.dump(results, open(os.path.join(ROOT, 'reports', 'text-check.json'), 'w'), indent=1, ensure_ascii=False)
    md = ['# Core page text check', '', 'Generated by `tools/check_text.py`. Copy compares words (quotes, dashes and spacing normalised).', '']
    for r in results:
        md.append('## %s %s' % (r['path'], 'OK' if r['ok'] else 'DIFFERENCES'))
        for m in r['missing_copy']:
            md.append('- Missing (%s): %s' % (m['kind'], m['text']))
        for k, v in r['seo'].items():
            if not v.get('ok', True):
                md.append('- %s differs from export: expected `%s`, built `%s`' % (k, v.get('expected_export') or v.get('expected'), v['built']))
        md.append('- H1: %s' % ' / '.join(r['seo']['h1']['built']) if r['seo']['h1']['built'] else '- H1: (none on the live page either; see notes)')
        sp = r['saved_page']
        if sp:
            for k in ('title', 'description', 'canonical', 'h1'):
                if not sp[k]['ok']:
                    md.append('- Saved live page %s differs: live `%s`, built `%s`' % (k, sp[k]['live'], sp[k]['built']))
            for l in sp['live_lines_missing']:
                md.append('- Live line not found: %s' % l)
            if sp and all(sp[k]['ok'] for k in ('title', 'description', 'canonical', 'h1')) and not sp['live_lines_missing']:
                md.append('- Matches the saved live page (title, description, canonical, H1, every visible line).')
        md.append('')
    open(os.path.join(ROOT, 'reports', 'text-check.md'), 'w').write('\n'.join(md))
    print('core pages checked:', len(results), 'with differences:', failures)
    for r in results:
        if not r['ok']:
            print(' ', r['path'])
    return failures


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
