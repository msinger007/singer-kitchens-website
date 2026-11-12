# Singer Kitchens website

The www.singerkitchens.com rebuild: a static Eleventy site, stored here and hosted on Netlify.
It replaces the WordPress/Elementor site on SiteGround. Content and URLs moved over as they were;
the design stays close to the live site (photo-led pages, centred home hero over the kitchen, red
buttons), with a few clean-ups: no sliders, a sticky header, the four-step process and two-showroom bands.
/kitchen-design/ is its own published page (it is not redirected to /kitchens/).

## Where things live

| What | File |
| --- | --- |
| Phone, email, tracking IDs, GoHighLevel form IDs | `src/_data/site.json` |
| Menu and footer links | `src/_data/nav.json` |
| The two showrooms (address, phone, hours, photos, map pins) | `src/_data/showrooms.json` |
| The Four-Step Singer Kitchens Process (approved copy) | `src/_data/process.json` |
| Google reviews block (Featurable widget; reviews update automatically from Google) | `src/_includes/partials/google-reviews.njk` |
| Service-area list above the footer | `src/_data/serviceAreas.json` |
| Image alt text written by hand | `src/_data/alt-overrides.json` |
| Home page | `src/index.njk` |
| Showrooms page | `src/showrooms.njk` |
| Every other page | `src/pages/*.njk` (one file per page, `permalink` = the old URL) |
| Blog posts (Kitchen Stories) | `src/posts/*.md` |
| Header, footer, process bands, reviews | `src/_includes/partials/` |
| Styles | `src/assets/css/site.css` |
| Redirects and Netlify settings | `netlify.toml` (generated, see below) |

## Making a change

- **Copy on a page:** open the page's file in `src/pages/` (or `src/index.njk` / `src/showrooms.njk`)
  and edit the words between the tags. Core pages (home and every menu page) are word-for-word
  copies of the live site, so check with Nancy before changing their wording.
- **Phone, hours, address:** `src/_data/site.json` and `src/_data/showrooms.json`. The header, footer,
  showroom cards, map and structured data all read from these.
- **A new blog post:** copy any file in `src/posts/`, change the front matter (title, description,
  date, permalink, image) and write the post below it in Markdown.
- **Reviews:** shown by the Featurable widget, which pulls them from the Google Business Profile automatically. Nothing to update here; manage the widget in your Featurable account.
- **Remove the four-step band from the home page:** delete the single
  `{% include "partials/process-band.njk" %}` line in `src/index.njk` (it is marked REMOVABLE).

Netlify publishes from the `claude/upbeat-newton-y1ikse` branch (the repository's default branch; there is no `main`).
Merge a pull request into it, or commit to it directly, and Netlify rebuilds and publishes in about a minute.

## Building it yourself

```bash
npm install
```

```bash
npm run build
```

The site is written to `_site/`. `npm start` serves it at http://localhost:8080 with live reload.

## Regenerating from the WordPress export (one-time migration tools)

The WordPress export and the uploads folder are not in the repo. To regenerate, put
`singerkitchens.WordPress.2026-11-10.xml` and the unzipped `uploads/` folder in `source/`, then:

```bash
python3 tools/repair_uploads.py source/uploads
```

```bash
python3 tools/convert_wp.py
```

```bash
python3 tools/make_netlify_toml.py
```

```bash
npm run build && python3 tools/check_text.py && python3 tools/check_links.py
```

`repair_uploads.py` fixes the Drive download, which turned every line-feed byte in the binary
files into CR+LF (about 2,600 images would not open). Re-running `convert_wp.py` overwrites
`src/pages/` and `src/posts/`, so do it only before anyone edits those files by hand.

## Page speed

- **Tracking loads after the page.** Google Tag Manager (GA4, Google Ads and call tracking inside it),
  the Meta Pixel and the GoHighLevel chat widget start on the visitor's first scroll, tap, click or
  keypress, or 3 seconds after the page loads. Pixel events made before then are queued, not lost. The
  code is in `src/_includes/layouts/base.njk`. A visitor who leaves within about 3 seconds without
  touching the page is not counted.
- **YouTube videos** show a thumbnail and load the privacy-mode player only when someone presses play
  (the "speed" transform in `eleventy.config.js`, plus a click handler in `src/assets/js/site.js`).
- **The stylesheet is inlined** into each page, so edit `src/assets/css/site.css` as usual.
- **Phone-sized images:** on Netlify builds, images wider than 900px get an 800px version from
  Netlify's image service (`/.netlify/images`). Local builds don't add these, so the checks run as before.

## Checks

- `tools/check_text.py`: compares every core page with the WordPress export and with the
  browser-saved live pages in `reference/saved-pages/` (body copy, title, meta description, H1,
  canonical). Results: `reports/text-check.md`.
- `tools/check_links.py`: every local link and image in `_site` resolves.
- `tools/seo_scan.py` (add `--external` to test outside links too): broken and redirected links, duplicate or
  missing titles and descriptions, H1s, dated content. Results: `reports/seo-scan.json`; the November 2026
  cleanup and the open decisions are in `reports/seo-cleanup.md`.
- `tools/screenshot_all.cjs`: Playwright screenshots of every page at 1280px and 390px, checking
  for sideways scrolling and broken images. Results: `reports/screenshot-check.json`.
- `cleanup-sheet.csv`: every published page and post with a suggested keep / improve / merge /
  retire / noindex decision. Nothing has been removed; traffic columns are empty until Search
  Console is connected.

## Launch steps (Andre)

1. Netlify → Add new site → Import an existing project → GitHub → this repo → Deploy.
2. Check the `*.netlify.app` preview on a phone and a laptop.
3. Before touching DNS, confirm whether SiteGround also handles info@singerkitchens.com email or
   other DNS records.
4. Netlify → Domain management → add www.singerkitchens.com, then update DNS.
5. Submit a test on /request-consultation/ and /pro-partners/ and confirm Nancy's SMS arrives;
   check GTM, GA4 and the Meta Pixel in real time; spot-check old URLs redirect.
6. Keep the WordPress site and a full backup for about two weeks while watching Search Console
   (Pages → Not found), then retire SiteGround.
