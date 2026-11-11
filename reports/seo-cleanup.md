# Pre-launch SEO cleanup (November 2026)

Scan of every page on the new site for broken links, duplicate titles and descriptions, heading problems,
outdated content and WordPress leftovers. Re-run any time with:

```bash
npm run build && python3 tools/seo_scan.py --external
```

Raw results: `reports/seo-scan.json`. Core-page copy is unchanged; `tools/check_text.py` still passes.

## Fixed

**Kitchens vs Kitchen Design**
- /kitchen-design/ is the kitchen design page (title "Kitchen Design New Orleans, Mandeville & Covington").
  The menu and footer "Kitchen Design" links now go to it.
- /kitchens/ now targets kitchen renovation: new SEO title "Kitchen Renovation in New Orleans & Mandeville |
  Singer Kitchens" and a new meta description. Its words and H1 are unchanged. Recorded in
  `tools/approved-seo-changes.json` so the copy check expects it.
- /remodeling/ keeps "Kitchen Remodeling New Orleans, Mandeville & Covington".

**Old WordPress pages retired (301 redirects in netlify.toml)**

| Page | Why | Now goes to |
| --- | --- | --- |
| /slider-page-test/ | Test page with "lorem ipsum" placeholder text | / |
| /kitchen-accessory-giveaway/ | Offer ended May 31, 2023 | /request-consultation/ |
| /contact/ | Empty page (two words) | /request-consultation/ |
| /happy-customers/ | Only a video that is also on /reviews/ | /reviews/ |
| /hardware/ | Three words, no content | /kitchen-cabinets/ |
| /installation/ | Thin page covered by Our Process | /our-process/ |

**Hidden from Google, still live** (ad, email and QR-code landing pages, so campaigns keep working):
/constant-contact/, /constant-contact-lp/, /finance_application_qr_code/, /kitchen-cabinets-latest/,
/kitchen-cabinets-lp/, /kitchen-remodel-lp/, /leads/, /professional-kitchen-cabinets-from-singer-kitchens/,
/hurricane-ida-damage/. This also removed every duplicate title and description on the site.

**Links**
- 56 internal links that went through a redirect now point straight at the page
  (48 of them were "contact us" links to the empty /contact/ page).
- A link wrapped in a Google tracking redirect (/kitchen-design/) unwrapped.
- A malformed Google Maps link on /service-area/ fixed.
- Dead external links removed, words kept: NARI survey PDF, House of Nadine (domain no longer exists),
  the lifetime warranty PDF (not in the WordPress uploads; see "Needs a decision").
- The dead Sharp microwave page now links to sharpusa.com; http:// links switched to https://, including
  Facebook and Instagram in the header; pinterest.ph changed to pinterest.com.

**Titles, descriptions, headings**
- The WordPress title ending " | Singer Kitchens | Kitchen Remodeling New Orleans" shortened to
  " | Singer Kitchens" on non-core pages and posts, and dropped where the title was already too long for Google.
  Core page titles are unchanged. "SInger Kitchens" typo fixed on /appliances/.
- Blog pages 2-9 now have "- Page N" in the title and description (they were all identical).
- Meta descriptions written for the three Lacombe service-area pages (they had none), /service-area/mandeville/
  (copied from its kitchen-design page) and /remodeling-period-kitchens/ (it had the kitchen island post's).
- One H1 per page: 49 portfolio and service-area pages had none (their first heading is now the H1, same
  words); /cabinets/, /countertops/, /reviews/ and one post had several (extras are now H2, same words).
- Two posts filed as "Uncategorized" now show "Tips".

**Showroom hours**: non-core pages said Mon-Fri 10am-6pm and/or Sat 10am-3pm. Updated to the current hours
(Mon-Fri 10am-5pm, Sat 10am-2pm) on /kitchen-design/, /northshore-kitchen-remodeling/,
/southshore-kitchen-remodeling/, /thank-you/ and the four ad landing pages.

## Needs a decision (Nancy or Andre)

1. **Old hours on core pages.** /cabinets/, /closets/, /storage-solutions/ and /kitchens/ still show
   10am-6pm and/or Sat 10am-3pm. Core copy, so not changed. Recommend updating to 10am-5pm / Sat 10am-2pm.
2. **Other phone numbers.** Some may be ad call-tracking numbers; confirm before changing:
   - (504) 608-4982 on /kitchens/ and /our-process/ (core pages)
   - (504) 900-4836 on /northshore-kitchen-remodeling/, /southshore-kitchen-remodeling/, /kitchen-remodel-lp/
   - (985) 306-9472 on /northshore-kitchen-remodeling/
   - (504) 662-1766 in two posts; (985) 805-5188 in one post
3. **/kitchens/ H1** still reads "Kitchen Design". Recommend "Kitchen Renovation" to match its new focus
   (core copy, needs OK). /kitchens/ is no longer in the menu (16 pages still link to it, including the home
   page); add a "Kitchen Renovation" menu item if you want it there.
4. **Core pages with no H1** (same as the live site): /financing/, /request-consultation/, /employment/, /blog/.
   Recommend making each page's first heading the H1 (no word changes).
5. **Lifetime warranty PDF** linked from /rain-water-damage-kitchen-restoration-new-orleans/ is not in the
   WordPress uploads. Link removed. If Singer has the PDF, add it to `src/wp-content/uploads/2018/04/`.
6. **Hurricane page** (/hurricane-ida-damage/): the URL and title say Ida, the page now talks about Hurricane
   Francine (2024). Hidden from Google for now. Either rewrite it as an evergreen storm-damage page or 301 it
   to /rain-water-damage-kitchen-restoration-new-orleans/.

## Outdated content (recommendations; decide with Search Console data)

Search Console isn't connected yet, so nothing here was removed. Posts that still get traffic should be
refreshed, not deleted.

| Post | Issue | Recommendation |
| --- | --- | --- |
| /get-kitchen-design-inspiration-by-appointment-safety-measures-included/ | July 2020 COVID safety post | 301 to /showrooms/ |
| /singer-kitchens-talks-2020-design-trends-with-st-charles-magazine/ | 2020 trends | Keep as press, or 301 to /as-seen-on/ |
| /4-kitchen-upgrades-that-answer-your-familys-2020-needs-just-in-time-for-the-holidays/ | 2020 in the title | Remove the year from the title, or 301 to /quick-refresh/ |
| /2021-design-trends-topping-everyones-wish-lists/ | 2021 trends | 301 to /top-kitchen-design-trends/ |
| /2022-kitchen-design-trends-you-wont-want-to-miss/ | 2022 trends | 301 to /top-kitchen-design-trends/ |
| /how-to-bring-nature-into-your-kitchen-with-the-top-trending-colors-of-2023/ | 2023 colors | Drop the year from the title and refresh, or 301 to /top-kitchen-design-trends/ |
| /minimalism-to-the-max-slab-doors-are-2023s-darling/ | 2023 in the title | Drop the year from the title |
| /21-storage-solutions-to-start-your-2021-off-right/ | 2021 in the title | Retitle "21 Kitchen Storage Solutions" (evergreen list) |
| /discover-the-latest-kitchen-and-bath-trends-from-kbis-2024/ | 2024 trade show | Keep as news, link to /top-kitchen-design-trends/ |
| /4-ways-to-find-the-perfect-new-orleans-kitchen-cabinets/ | Opens with "Hurricane Ida still looms" (2021) | Refresh the first paragraph |
| /creating-a-kitchen-island-paradise/, /dont-wait-start-on-your-holiday-remodel-today/ | "this year", "this summer" | Light refresh |

Client stories that mention the pandemic or Hurricane Ida as part of the story are fine as they are.

## Worth doing later

- 45 pages have very short meta descriptions (all 30 portfolio projects, /portfolio/, /reviews/,
  /kitchen-design-checklist/, the blog index, three posts). 20 pages have descriptions over 165 characters.
  Good candidates for the next content batch.
- External links the checker couldn't verify because those sites block automated requests. Check them by hand:
  amana.com, kitchenaid.com, whirlpool.com, broan.com, frigidaire.com (all on /appliances/), the BBB profiles on
  the ad landing pages, thespruce.com (/wall-beds-for-small-spaces/), jech.bmj.com
  (/accomplish-your-new-years-resolutions-in-the-kitchen/).
