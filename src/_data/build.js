import fs from "node:fs";

// Keep search engines off every copy of the site except the real one.
// On Netlify, URL is the site's primary address: https://singer-kitchens-website1.netlify.app until
// www.singerkitchens.com is set as the primary domain, which turns indexing on with no other change.
// Deploy previews and branch deploys are always noindex. Local builds (not on Netlify) are left alone.
const site = JSON.parse(fs.readFileSync(new URL("./site.json", import.meta.url), "utf8"));
const onNetlify = !!process.env.NETLIFY;
let primaryHost = "";
try { primaryHost = new URL(process.env.URL || "").hostname; } catch (e) {}
const noindexSite = onNetlify && (process.env.CONTEXT !== "production" || primaryHost !== new URL(site.url).hostname);

export default { version: Date.now().toString(36), noindexSite };
