export const SITE_NAME = "GitHub Top 50";
export const SITE_LOCALE = "fr_FR";
export const SITE_LANGUAGE = "fr-FR";
export const SITE_TWITTER_CARD = "summary_large_image";
export const SITE_DEFAULT_TITLE = "Top 50 GitHub Stars 2026";
export const SITE_DEFAULT_DESCRIPTION =
  "Classement actualise des repositories GitHub les plus suivis, avec categories techniques, signaux open source et recommandations d'hebergement.";
export const SITE_DEFAULT_IMAGE = "og-image.svg";

export interface SeoRoute {
  path: string;
  label: string;
  changefreq: "daily" | "weekly" | "monthly";
  priority: string;
}

export const SEO_ROUTES: SeoRoute[] = [
  {
    path: "/",
    label: "Vue d'ensemble",
    changefreq: "daily",
    priority: "1.0"
  },
  {
    path: "/top/",
    label: "Top stars",
    changefreq: "daily",
    priority: "0.9"
  },
  {
    path: "/categories/",
    label: "Categories",
    changefreq: "weekly",
    priority: "0.8"
  },
  {
    path: "/hosting/",
    label: "Hebergements",
    changefreq: "monthly",
    priority: "0.7"
  }
];

export function joinBasePath(basePath: string, pathname: string): string {
  const base = basePath.endsWith("/") ? basePath : `${basePath}/`;
  const path = pathname.replace(/^\/+/, "");

  return `${base}${path}`;
}
