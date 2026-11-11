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
  eleventyConfig.addFilter("startsWith", (s, p) => String(s || "").startsWith(p));
  eleventyConfig.addFilter("year", () => String(new Date().getFullYear()));

  return {
    dir: { input: "src", output: "_site", includes: "_includes", data: "_data" },
    templateFormats: ["njk", "md", "11ty.js"],
    markdownTemplateEngine: false,
    htmlTemplateEngine: "njk",
  };
}
