import type { APIRoute } from "astro";
import { getSiteData } from "../data/site-data";
import { joinBasePath, SEO_ROUTES } from "../utils/seo";

export const prerender = true;

function escapeXml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

export const GET: APIRoute = async ({ site }) => {
  const siteUrl = site ?? new URL("https://yann-erwann.github.io");
  const data = await getSiteData();
  const lastmod = new Date(data.snapshot.capturedAt).toISOString().slice(0, 10);
  const urls = SEO_ROUTES.map((route) => {
    const location = new URL(joinBasePath(import.meta.env.BASE_URL, route.path), siteUrl);

    return [
      "  <url>",
      `    <loc>${escapeXml(location.toString())}</loc>`,
      `    <lastmod>${lastmod}</lastmod>`,
      `    <changefreq>${route.changefreq}</changefreq>`,
      `    <priority>${route.priority}</priority>`,
      "  </url>"
    ].join("\n");
  }).join("\n");

  return new Response(
    [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      urls,
      "</urlset>"
    ].join("\n"),
    {
      headers: {
        "Content-Type": "application/xml; charset=utf-8"
      }
    }
  );
};
