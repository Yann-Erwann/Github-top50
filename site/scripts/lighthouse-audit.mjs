import { spawn } from "node:child_process";
import { mkdir, readdir, readFile, rm } from "node:fs/promises";
import { existsSync, statSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT_DIR = dirname(fileURLToPath(import.meta.url));
const SITE_DIR = join(ROOT_DIR, "..");
const DIST_DIR = join(SITE_DIR, "dist");
const REPORT_DIR = join(SITE_DIR, ".lighthouseci");
const PORT = process.env.LHCI_PORT || "4321";
const ORIGIN = `http://127.0.0.1:${PORT}`;
const BASE_PATH = normalizeBasePath(process.env.PUBLIC_BASE_PATH || "/Github-top50");
const CATEGORIES = ["performance", "accessibility", "best-practices", "seo"];
const CHROME_FLAGS = "--headless=new --no-sandbox --disable-dev-shm-usage";
const PROFILES = [
  { id: "mobile", flags: [] },
  { id: "desktop", flags: ["--preset=desktop"] }
];

function normalizeBasePath(value) {
  if (!value || value === "/") {
    return "";
  }

  const withLeadingSlash = value.startsWith("/") ? value : `/${value}`;
  return withLeadingSlash.endsWith("/")
    ? withLeadingSlash.slice(0, -1)
    : withLeadingSlash;
}

async function walkHtmlFiles(directory) {
  const entries = await readdir(directory);
  const files = [];

  for (const entry of entries) {
    const entryPath = join(directory, entry);
    const stats = statSync(entryPath);

    if (stats.isDirectory()) {
      files.push(...(await walkHtmlFiles(entryPath)));
      continue;
    }

    if (entry === "index.html") {
      files.push(entryPath);
    }
  }

  return files;
}

function routeFromHtmlFile(filePath) {
  const routePath = relative(DIST_DIR, filePath)
    .split(sep)
    .slice(0, -1)
    .filter(Boolean)
    .join("/");

  return routePath ? `/${routePath}/` : "/";
}

async function discoverUrls() {
  if (!existsSync(DIST_DIR)) {
    throw new Error("Build the Astro site before running Lighthouse: npm run build");
  }

  const routes = (await walkHtmlFiles(DIST_DIR))
    .map(routeFromHtmlFile)
    .sort((left, right) => {
      if (left === "/") return -1;
      if (right === "/") return 1;
      return left.localeCompare(right);
    });

  return routes.map((route) => `${ORIGIN}${BASE_PATH}${route}`);
}

function startPreviewServer() {
  const server = spawn(
    "npm",
    ["run", "preview", "--", "--host", "127.0.0.1", "--port", PORT],
    {
      cwd: SITE_DIR,
      shell: process.platform === "win32",
      stdio: ["ignore", "pipe", "pipe"]
    }
  );

  server.stdout.on("data", (chunk) => process.stdout.write(chunk));
  server.stderr.on("data", (chunk) => process.stderr.write(chunk));

  return server;
}

async function waitForUrl(url, timeoutMs = 30000) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url);

      if (response.ok) {
        return;
      }
    } catch {
      // The preview server is still starting.
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  throw new Error(`Timed out waiting for Astro preview at ${url}`);
}

function reportNameForUrl(url, profile) {
  const { pathname } = new URL(url);
  const withoutBase = BASE_PATH && pathname.startsWith(BASE_PATH)
    ? pathname.slice(BASE_PATH.length)
    : pathname;
  const normalized = withoutBase.replace(/^\/|\/$/g, "").replaceAll("/", "-");

  return `${profile}-${normalized || "index"}`;
}

async function runLighthouse(url, profile) {
  const outputPath = join(REPORT_DIR, `${reportNameForUrl(url, profile.id)}.json`);
  const lighthouseCli = join(SITE_DIR, "node_modules", "lighthouse", "cli", "index.js");

  await new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [
        lighthouseCli,
        url,
        "--quiet",
        ...profile.flags,
        `--only-categories=${CATEGORIES.join(",")}`,
        "--output=json",
        `--output-path=${outputPath}`,
        `--chrome-flags=${CHROME_FLAGS}`
      ],
      {
        cwd: SITE_DIR,
        stdio: "inherit"
      }
    );

    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }

      reject(new Error(`Lighthouse failed for ${url} with exit code ${code}`));
    });
  });

  return JSON.parse(await readFile(outputPath, "utf8"));
}

function assertPerfectScores(results) {
  const failures = [];

  for (const { url, profile, lhr } of results) {
    for (const category of CATEGORIES) {
      const score = lhr.categories[category]?.score;

      if (score !== 1) {
        failures.push({ url, profile, category, score });
      }
    }
  }

  if (failures.length === 0) {
    console.log("All Lighthouse categories are at 100 for every built page.");
    return;
  }

  console.error("Lighthouse score gate failed:");
  for (const failure of failures) {
    console.error(
      `- ${failure.url} (${failure.profile}): ${failure.category}=${Math.round(
        (failure.score ?? 0) * 100
      )}`
    );
  }

  throw new Error("Every audited Lighthouse category must score 100.");
}

const urls = await discoverUrls();
await rm(REPORT_DIR, { recursive: true, force: true });
await mkdir(REPORT_DIR, { recursive: true });

console.log(`Auditing ${urls.length} built Astro page(s) with ${PROFILES.length} Lighthouse profile(s):`);
for (const url of urls) {
  console.log(`- ${url}`);
}

const server = startPreviewServer();

try {
  await waitForUrl(urls[0]);

  const results = [];
  for (const profile of PROFILES) {
    for (const url of urls) {
      console.log(`Running ${profile.id} Lighthouse on ${url}`);
      results.push({ url, profile: profile.id, lhr: await runLighthouse(url, profile) });
    }
  }

  for (const { url, profile, lhr } of results) {
    const scores = CATEGORIES.map(
      (category) => `${category}=${Math.round(lhr.categories[category].score * 100)}`
    ).join(" ");
    console.log(`${url} (${profile}) ${scores}`);
  }

  assertPerfectScores(results);
} finally {
  server.kill("SIGTERM");
}
