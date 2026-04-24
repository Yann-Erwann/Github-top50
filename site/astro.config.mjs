import { defineConfig } from "astro/config";

const site = process.env.PUBLIC_SITE_URL || "https://yann-erwann.github.io";
const base = process.env.PUBLIC_BASE_PATH || "/Github-top50";

export default defineConfig({
  site,
  base,
  output: "static",
  trailingSlash: "always",
  build: {
    format: "directory"
  }
});
