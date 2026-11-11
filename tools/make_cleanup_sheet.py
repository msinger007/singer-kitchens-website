#!/usr/bin/env python3
"""Write cleanup-sheet.csv: one row per published page, post and service-area page, with a suggested
decision. Traffic columns stay empty until Search Console data is available. Nothing is acted on."""
import csv, os, re, sys, html
sys.path.insert(0, os.path.dirname(__file__))
import convert_wp as C

ROOT = C.ROOT
rows = []
NOINDEX_RE = re.compile(r'thank-you|thank_you|calendar')
LP_RE = re.compile(r'(-lp/|/lp-|constant-contact|kitchen-cabinets-latest|professional-kitchen-cabinets-from|finance_application_qr_code|/leads/)')
RETIRE_PAGES = {'/slider-page-test/': 'Test page left over from the WordPress build',
                '/special-offers/': 'Offer page; check whether the offer is current',
                '/kitchen-accessory-giveaway/': 'Expired giveaway promotion (check dates with Nancy)',
                '/kitchen-accessory-giveaway/the-guide-thank-you/': 'Thank-you page for the expired giveaway',
                '/hurricane-ida-damage/': '2021 hurricane event page; time-bound',
                '/hurricane-ida-damage/thank-you/': 'Thank-you page for the 2021 hurricane page'}
MERGE_PAGES = {'/kitchen-design/': ('/kitchens/', 'Duplicate Kitchen Design page; already 301s to /kitchens/ in this build per the brief. Its copy differs from /kitchens/ (review before launch)'),
               '/contact/': ('/request-consultation/', 'Old contact page; the consultation form replaces it'),
               '/happy-customers/': ('/reviews/', 'Overlaps the Reviews page'),
               '/hardware/': ('/kitchen-cabinets/', 'Nearly empty page'),
               '/installation/': ('/our-process/', 'Thin page covered by Our Process'),
               '/service-area/': ('/showrooms/', 'Generic service-area hub with no area of its own')}
IMPROVE_PAGES = {'/appliances/': 'Older product page; refresh brand list and photos',
                 '/purestyle/': 'Single-brand page from 2018; check the brand is still carried',
                 '/diamond-cabinets/': 'Brand page; check current line and photos',
                 '/mantra-cabinets/': 'Brand page; check current line and photos',
                 '/mobility-challenged/': 'Useful niche page; thin, add detail and internal links',
                 '/interactive-kitchen-design-checklist/': 'Hosts the interactive planning tool; keep, add title/description',
                 '/northshore-kitchen-remodeling/': 'Local landing page with June impressions; keep and improve',
                 '/southshore-kitchen-remodeling/': 'Local landing page with June impressions; keep and improve'}


def words(path):
    f = os.path.join(ROOT, '_site', path.strip('/'), 'index.html') if path != '/' else os.path.join(ROOT, '_site', 'index.html')
    if not os.path.exists(f):
        return 0
    h = open(f, encoding='utf-8').read()
    m = re.search(r'<main id="main">(.*)</main>', h, re.S)
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', m.group(1) if m else '', flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return len(re.findall(r"[A-Za-z0-9’']+", t))


for it in sorted(C.PUBLISHED, key=lambda i: (i['type'], C.PATH_OF[i['id']])):
    path = C.PATH_OF[it['id']]
    title = html.unescape(it['title'])
    wc = words(path)
    core = path in C.CORE_PATHS
    t = it['type']
    if core:
        dec, why = 'keep', 'Core page: copy, title, meta, H1 and URL preserved'
    elif NOINDEX_RE.search(path) or C.seo_for(it)['noindex']:
        dec, why = 'noindex', 'Form confirmation / booking page; stays reachable, kept out of Google'
    elif path in RETIRE_PAGES:
        dec, why = 'retire', RETIRE_PAGES[path] + ' (301 to closest page once data confirms)'
    elif path in MERGE_PAGES:
        dec, why = 'merge', 'Into %s: %s' % MERGE_PAGES[path]
    elif LP_RE.search(path):
        dec, why = 'noindex', 'Ad or email landing page; keep live for campaigns, keep out of search results'
    elif path in IMPROVE_PAGES:
        dec, why = 'improve', IMPROVE_PAGES[path]
    elif t == 'service-area':
        dec, why = 'keep', 'Service-area page, likely earning local traffic; keep and improve with data'
    elif path.startswith('/portfolio/'):
        dec, why = ('keep', 'Portfolio project gallery') if wc > 15 else ('improve', 'Gallery with no description')
    elif path in ('/privacy-policy/', '/accessibility-statement/'):
        dec, why = 'keep', 'Legal page'
    elif t == 'post':
        tl = title.lower()
        year = re.search(r'\b(20[12]\d)\b', title)
        if re.search(r'bath', tl):
            dec, why = 'keep', 'Bathroom post: keep if it earns clicks, otherwise retire (no new effort per plan)'
        elif year:
            dec, why = 'improve', 'Carries a year (%s) in the title; evergreen pieces should not' % year.group(1)
        elif wc < 250:
            dec, why = 'improve', 'Thin post (%d words); expand or merge with a related story' % wc
        elif 'custom' in tl:
            dec, why = 'improve', 'Title uses "custom" (brand rule)'
        else:
            dec, why = 'keep', 'On-brand post; keep unless Search Console shows no impressions'
    else:
        dec, why = ('improve', 'Thin page (%d words)' % wc) if wc < 150 else ('keep', 'Supporting page')
    rows.append({'url': C.W.SITE + path, 'type': t, 'title': title, 'published': it['date'][:10], 'modified': it['modified'][:10],
                 'word_count': wc, 'core': 'yes' if core else 'no', 'clicks_12m': '', 'impressions_12m': '', 'top_query': '',
                 'suggested_decision': dec, 'reason': why})
with open(os.path.join(ROOT, 'cleanup-sheet.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
from collections import Counter
print(len(rows), 'rows', Counter(r['suggested_decision'] for r in rows), Counter(r['type'] for r in rows))
