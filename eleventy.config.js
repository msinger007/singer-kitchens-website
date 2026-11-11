import fs from "node:fs";

const images = JSON.parse(fs.readFileSync("src/_data/generated/images.json", "utf8"));

function escapeHtml(s) {
  return String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

export default function (eleventyConfig) {
  eleventyConfig.addPassthroughCopy({ "src/images": "images" });
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  eleventyConfig.addPassthroughCopy({ "src/wp-content": "wp-content" });
  eleventyConfig.addPassthroughCopy({ "src/embedded-tools": "embedded-tools" });
  eleventyConfig.addPassthroughCopy({ "src/favicon.ico": "favicon.ico" });
  eleventyConfig.addPassthroughCopy({ "src/robots.txt": "robots.txt" });

  eleventyConfig.addCollection("posts", (api) =>
    api.getFilteredByGlob("src/posts/*.md").sort((a, b) => b.date - a.date)
  );
  eleventyConfig.addCollection("sitemapPages", (api) =>
    api.getAll().filter((p) => p.url && !p.data.noindex && !p.data.sitemapExclude && !String(p.url).endsWith(".xml") && !String(p.url).endsWith(".txt"))
  );

  // {{ "2023/02/IMG_0260.jpg" | img("alt override", "hero") | safe }}
  eleventyConfig.addFilter("img", (file, alt, mode, cls) => {
    const im = images[file];
    if (!im) throw new Error("Image not in manifest (run tools/convert_wp.py): " + file);
    const a = [`src="${im.src}"`, `alt="${escapeHtml(alt || im.alt)}"`, `width="${im.w}"`, `height="${im.h}"`];
    if (mode === "hero") a.push('fetchpriority="high"');
    else a.push('loading="lazy"', 'decoding="async"');
    if (cls) a.push(`class="${cls}"`);
    return `<img ${a.join(" ")}>`;
  });
  eleventyConfig.addFilter("imgSrc", (file) => (images[file] || {}).src || "");
  eleventyConfig.addFilter("json", (v) => JSON.stringify(v));
  eleventyConfig.addFilter("absUrl", (path, base) => new URL(path || "/", base).href);
  eleventyConfig.addFilter("isoDate", (d) => new Date(d).toISOString());
  eleventyConfig.addFilter("niceDate", (d) =>
    new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" })
  );
  // Page speed (see README "Page speed"):
  // 1. Inline the stylesheet so it does not block the first paint.
  const cssPath = "src/assets/css/site.css";
  const inlineCss = () => fs.readFileSync(cssPath, "utf8").replace(/\/\*[\s\S]*?\*\//g, "").replace(/\s*\n\s*/g, "\n").trim();
  eleventyConfig.addShortcode("inlineCss", inlineCss);
  // 2. YouTube embeds become a click-to-play thumbnail (no player, scripts or cookies until a visitor presses play).
  // 3. On Netlify, large images get an 800px version for phones from Netlify's image service (local builds are unchanged).
  const onNetlify = !!process.env.NETLIFY;
  eleventyConfig.addTransform("speed", function (content) {
    if (!(this.page.outputPath || "").endsWith(".html")) return content;
    content = content.replace(
      /(<div class="video[^"]*">)<iframe src="https:\/\/www\.youtube\.com\/embed\/([\w-]{11})([^"]*)" title="([^"]*)"[^>]*><\/iframe>/g,
      (m, open, id, params, title) =>
        `${open}<a class="yt" href="https://www.youtube.com/watch?v=${id}" data-yt="${id}" data-params="${params}" target="_blank" rel="noopener">` +
        `<img src="https://i.ytimg.com/vi/${id}/hqdefault.jpg" alt="" width="480" height="360" loading="lazy" decoding="async">` +
        `<span class="yt-play" aria-hidden="true"></span><span class="sr">Play video: ${title}</span></a>`
    );
    if (onNetlify) {
      content = content.replace(/<img src="(\/images\/[^"]+\.webp)"([^>]*?) width="(\d+)"/g, (m, src, mid, w) => {
        if (+w <= 900 || /srcset=/.test(mid)) return m;
        const small = `/.netlify/images?url=${encodeURIComponent(src)}&amp;w=800`;
        return `<img src="${src}" srcset="${small} 800w, ${src} ${w}w" sizes="(max-width: 800px) 100vw, 1200px"${mid} width="${w}"`;
      });
    }
    return content;
  });
  eleventyConfig.addFilter("startsWith", (s, p) => String(s || "").startsWith(p));
  eleventyConfig.addFilter("year", () => String(new Date().getFullYear()));

  return {
    dir: { input: "src", output: "_site", includes: "_includes", data: "_data" },
    templateFormats: ["njk", "md", "11ty.js"],
    markdownTemplateEngine: false,
    htmlTemplateEngine: "njk",
  };
}
