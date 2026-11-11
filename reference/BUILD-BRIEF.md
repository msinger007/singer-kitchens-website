# Singer Kitchens rebuild: build brief for Claude Code

Rebuild www.singerkitchens.com (WordPress/Elementor on SiteGround) as a static Eleventy site on GitHub + Netlify, following the `swm-site-launch` skill. Content and URLs move over exactly; the design gets the approved refresh below.

- Site Plan: https://claude.ai/artifact/XtCrVpgxchrk4kaxHDqhcQ
- Design canvas (showrooms page, home bands, mobile): https://claude.ai/artifact/2EE4UFzebdkwYJSSp5hUYG
- Home page direction: `reference/singer-kitchens-home-mockup-v2.jpg` and `reference/home-mockup-v2.html` in this kit. Striped boxes are photo spots.

## Source files

Download both yourself into `source/` (add `source/` to `.gitignore`; never commit them). They're in the client's link-shared Drive folder: https://drive.google.com/drive/folders/1dQBZsprA1dvOaRaCrw6cXL1tfJskq9Kp

- `singerkitchens.WordPress.2026-11-10.xml` (14 MB), file ID `1IbCe_yS7bOZjzT2IgVZS090hItXrhgDf`: full WordPress export (pages, posts, Yoast meta, Elementor data).
- `uploads-20261110T214525Z-1-001.zip` (888 MB), file ID `1nHbtDB2TAN1R1wAyK-CauK5fpQnYbbOu`: the wp-content/uploads folder. The `-1-001` suffix means it may be part 1 of a split download. Report any image a core page uses that isn't in it.

Use `gdown` (`pip install gdown`, then `gdown <file ID>`), which handles Drive's large-file confirmation page. If the download fails, stop and tell the user. SWM keeps backup copies of both in its own Singer Kitchens folder.

Also in this kit, `reference/saved-pages/`: browser-saved copies of the live Home, Kitchen Remodeling, Showrooms, Financing and Request Consultation pages, and `reference/logo/singer-since-1928.png`.

SiteGround's bot check blocks automated fetches of the live site. Don't try to scrape it; everything needed is in the files above.

## Reading the export

- Most pages are built in Elementor. Their real content is in the `_elementor_data` post meta (JSON), not `post_content`, which is often stale. Parse `_elementor_data` and check the result against the saved pages.
- SEO titles and descriptions are in `_yoast_wpseo_title` and `_yoast_wpseo_metadesc`. Empty values fall back to Yoast templates (e.g. `%%title%% %%sep%% %%sitename%%`). Resolve them and check against the saved pages, which show the live output.
- Only published items (`wp:status` = publish) go on the site.

## The preservation rule

Core pages keep their copy word for word, plus SEO title, meta description, H1, canonical and URL. Only the design around them changes. New sections may be added to a core page; existing words are never edited, including known typos (they're flagged to Nancy separately).

Core pages: Home, plus every page in the menu:

- About: /about/, /our-process/, /as-seen-on/, /employment/, /pro-partners/
- Services: /remodeling/, /small-kitchen-remodeling/, /kitchens/, /kitchen-cabinets/, /quick-refresh/, /bathrooms/, /closets/, /portfolio/
- Products: /cabinets/, /countertops/, /storage-solutions/
- Learn: /blog/, /videos/, /kitchen-renovation-roi/, /top-kitchen-design-trends/, /kitchen-design-checklist/, /kitchen-design-secrets/, /cabinet-repainting-vs-remodeling/, /kitchen-remodeling-faqs/
- Top level: /showrooms/, /reviews/, /financing/, /request-consultation/

Confirm the exact slugs from the export and the live menu; use the export's slugs where they differ.

Everything else (blog posts, portfolio project pages, service-area pages, Northshore/Southshore pages) moves over as-is in this build. Cleanup decisions come later, once Andre approves the cleanup sheet with Search Console data.

For any brand detail (phone, hours, names, addresses), the live site is the source of truth.

## Design direction (approved basis: home mockup v2)

- **Colors:** white background, warm off-white `#F7F4F0` on alternating sections, charcoal `#262626` for text, dark bands and buttons, and logo red `#CF1924` as the accent. No grey text anywhere; white on dark, dark on light.
- **Red is used sparingly:** header Let's Talk Kitchens button, Step 1 marker, step numbers, small labels, trust-line dots and the closing call-to-action band.
- **Type:** bold Arial/Helvetica headlines (Singer's stated preference), Arial body.
- **Logo:** `reference/logo/singer-since-1928.png`, trimmed, in the header and on a white chip in the footer.
- **Hero:** one full-width photo with a white copy card. No sliders or rotating carousels anywhere; carousels become static photo grids.
- **Header:** sticky; logo, menu, main phone (504) 539-4605, and a red Let's Talk Kitchens button.
- **Mobile:** fixed bottom bar with two buttons, Call and Let's Talk Kitchens.
- **Trust:** one strip of badges plus Google reviews. Replace the Trustindex WordPress widget with a lightweight Google reviews block.
- **Footer:** two showroom columns, shared hours, main phone, key links.

### Menu (no URL changes)

| Item | Dropdown |
| --- | --- |
| Kitchens | Kitchen Remodeling, Quick Refresh, Small Kitchen Remodeling, Kitchen Design (/kitchens/), Design Portfolio |
| Cabinets & Countertops | Kitchen Cabinets, Countertops, Storage Solutions, Closets, Bathrooms |
| Our Process | (direct link) |
| Showrooms | (direct link) |
| Financing | (direct link) |
| Learn | Kitchen Stories, Videos, Kitchen Renovation ROI, Kitchen Design Trends, Kitchen Design Checklist, Kitchen Design Secrets, Cabinet Painting vs. Remodeling, FAQs |
| About | About, Reviews, As Seen On, Careers, Pro Partners |
| Button | Let's Talk Kitchens, linking to /request-consultation/ |

Every Let's Talk Kitchens button links to /request-consultation/. On the live home page the hero button goes to /showrooms; change only the link, not the words.

## The Four-Step Singer Kitchens Process (approved copy, word for word)

> **Step 1: Let's Talk Kitchens — Phone Call**
> Every kitchen starts with a conversation.
> Tell us what you're thinking about changing, what matters most, and what kind of timeline you have in mind.
> We can begin discussing financing options during this first call and answer questions about cabinet availability.
> If you need to move quickly, let us know. You may have more options than you think.
>
> **Step 2: Visit the Showroom**
> See and touch real cabinets, materials, finishes, and layouts.
> Talk with a designer about your ideas, explore the possibilities, and continue discussing pricing and financing options.
> You don't need to have everything figured out before you visit.
>
> **Step 3: In-Home Measurement**
> Accurate measurements help us understand your space and develop realistic design options and a custom quote.
> We'll also discuss the practical details that could affect your project timeline.
>
> **Step 4: Design Consultation, Quote & Presentation**
> Meet with your designer to review the proposed design, custom pricing options, available financing, installation considerations, and next steps.
> Our goal is to help you make informed decisions about your kitchen with a clear understanding of your options.

Where it goes:

- **/our-process/:** all four steps in full, added at the top as a numbered timeline (Step 1 is the lead step, with the button and phone). The page's existing copy stays below, word for word.
- **Service pages** (/remodeling/, /small-kitchen-remodeling/, /kitchens/, /kitchen-cabinets/, /cabinets/, /countertops/, /quick-refresh/, /storage-solutions/, /closets/): a compact four-step strip above the final call to action, linking to /our-process/.
- **/request-consultation/:** a "what happens next" strip below the form, with Step 1 highlighted.
- **/showrooms/:** a Step 2 band.
- **Home:** the four-step band between "Let's Talk About Your Kitchen" and the three project cards, as in mockup v2. Andre hasn't finally approved it on the home page, so build it as one removable section.

## Two showrooms (from the live /showrooms/ page)

| | New Orleans | Mandeville |
| --- | --- | --- |
| Address | 231 N. Carrollton Ave. (at Bienville, across from Brocato's), New Orleans, LA 70119 | 316 Girod St. (Old Mandeville), Mandeville, LA 70448 |
| Phone | (504) 486-0067 | (985) 778-2978 |
| Hours | Mon-Fri 10am-5pm, Sat 10am-2pm by Appointment | Same |

Both are open by appointment. Main number: (504) 539-4605.

- **/showrooms/:** keep its copy word for word. Add a two-card showroom chooser at the top, a full section per showroom (gallery, address, phone, hours, Get Directions, Let's Talk Kitchens), anchors `#new-orleans` and `#mandeville`, and a two-pin map. See the design canvas.
- **Home:** a two-showroom band before the service-area block.
- **Schema:** one LocalBusiness (HomeAndConstructionBusiness) entry per showroom, each with its own address, phone and hours, linked to the parent organization.

## Must keep working

- GoHighLevel forms on /request-consultation/ and /pro-partners/, with the same form IDs (submissions trigger Nancy's SMS).
- Kitchen Design Checklist planning tool (/kitchen-design-checklist/). Find out how it's built from the export and saved pages. If it's a WordPress plugin, it needs a replacement before launch; Meta lead ads point to it. Report what you find before building a replacement.
- Tracking: GTM, GA4, Meta Pixel, and the Google, Bing and Pinterest verification meta tags, all copied from the saved pages' head. Flag any GA4 loaded both directly and through GTM.
- YouTube embeds on /videos/.
- Portfolio galleries, complete.

## Images

From the uploads zip, use the original (non-resized) file for each image a page uses. Convert to WebP (heroes max 1600px wide, others 1200px), with width/height set, lazy-loading below the fold, and `fetchpriority="high"` on the hero. Write descriptive alt text that doesn't use the word "custom".

## Redirects (netlify.toml)

- /home → /
- /kitchen-design/ → whichever of /kitchens/ or /kitchen-design/ the export shows is the real page (report which)
- WordPress-only paths: /category/*, /tag/*, /author/*, date archives, /feed/, attachment pages → /blog/ or the parent post
- Keep /blog/2/, /blog/3/ pagination paths working

## Cleanup sheet (deliver, don't act on)

Produce `cleanup-sheet.csv` listing every published page and post from the export: URL, type, title, publish and modified dates, word count, core (yes/no), and empty columns for 12-month clicks, impressions and top query, plus a suggested decision (keep / improve / merge / retire / noindex) with a one-line reason. Nothing is removed in this build.

## Verify before showing

1. `npm run build` passes.
2. Automated text comparison of every core page against the saved pages and the export: body copy, title, meta description, H1. Report any difference.
3. Playwright screenshots of every page at 1280px and 390px: no horizontal scroll, no broken images.
4. Put the home page and core pages on the design canvas as full-page artboards for Andre's review.

## Don't

- Edit any core-page wording, or invent facts. Use bracketed placeholders and list them.
- Touch DNS, cancel SiteGround, or launch. Andre does those steps.
- Remove or redirect any blog post or service-area page in this build.

## Still open (don't block on these)

- Search Console for singerkitchens.com is not connected in Windsor; the cleanup sheet's traffic columns stay empty until it is.
- Whether Singer will edit the site themselves. Build with editable data files (`src/_data/*.json`, Markdown posts) so either way works.
- Real showroom photos and a line from Nancy or Holly on what's on display at each showroom.
- White background (v2) vs Singer's stone look: building white per the current direction.
