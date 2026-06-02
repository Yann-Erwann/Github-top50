import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

export interface RepositoryEntry {
  id?: number;
  rank: number;
  previousRank: number | null;
  movements: Record<string, number | null>;
  periodRankings: Record<string, number | null>;
  periodStarsGained: Record<string, number | null>;
  fullName: string;
  htmlUrl: string;
  stargazersCount: number;
  language: string | null;
  description: string | null;
}

export interface SnapshotInfo {
  capturedAt: string;
  label: string | null;
  source: string | null;
}

export interface PeriodOption {
  id: string;
  label: string;
  days: number | null;
  months: number | null;
  available: boolean;
  baselineCapturedAt: string | null;
}

export interface GlobalData {
  title: string;
  subtitle: string;
  items: RepositoryEntry[];
  highlights: RepositoryEntry[];
}

export interface CategoryEntry {
  tag: string;
  title: string;
  query: string | null;
  description: string | null;
  accent: string | null;
  items: RepositoryEntry[];
}

export interface HostingRecommendation {
  stack: string;
  hosting: string;
  url: string;
  notes: string;
  fit: string | null;
}

export interface LanguageStat {
  name: string;
  repositoryCount: number;
}

export interface StatsSummary {
  totalStars: number;
  repositoryCount: number;
  categoryCount: number;
  hostingCount: number;
  topLanguage: LanguageStat;
  languages: LanguageStat[];
}

export interface SiteData {
  snapshot: SnapshotInfo;
  periods: PeriodOption[];
  global: GlobalData;
  categories: CategoryEntry[];
  hosting: HostingRecommendation[];
  stats: StatsSummary;
}

export function sortRepositoriesByPeriod(
  items: RepositoryEntry[],
  periodId: string | null
): RepositoryEntry[] {
  return [...items].sort((left, right) => {
    const leftRank = periodId ? left.periodRankings[periodId] : null;
    const rightRank = periodId ? right.periodRankings[periodId] : null;

    if (leftRank === null || leftRank === undefined) {
      return rightRank === null || rightRank === undefined
        ? left.rank - right.rank
        : 1;
    }

    return rightRank === null || rightRank === undefined
      ? -1
      : leftRank - rightRank;
  });
}

const DATA_FILE = resolve(process.cwd(), "public/data/site-data.json");
const GITHUB_HOSTS = ["github.com"];
const HOSTING_DOC_HOSTS = ["render.com", "vercel.com"];

let cachedSiteData: Promise<SiteData> | undefined;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toString(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim().length > 0 ? value : fallback;
}

function toNullableString(value: unknown): string | null {
  const normalized = toString(value);
  return normalized.length > 0 ? normalized : null;
}

function isAllowedHost(host: string, allowedHosts: string[]): boolean {
  return allowedHosts.some(
    (allowedHost) => host === allowedHost || host.endsWith(`.${allowedHost}`)
  );
}

function toSafeHttpsUrl(
  value: unknown,
  allowedHosts: string[],
  fallback = "#"
): string {
  const candidate = toString(value, fallback);

  try {
    const url = new URL(candidate);

    if (url.protocol !== "https:" || !isAllowedHost(url.hostname, allowedHosts)) {
      return fallback;
    }

    return url.toString();
  } catch {
    return fallback;
  }
}

function toNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function toInteger(value: unknown, fallback = 0): number {
  return Math.trunc(toNumber(value, fallback));
}

function toNullableInteger(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value)
    ? Math.trunc(value)
    : null;
}

function normalizeNullableIntegerRecord(
  value: unknown
): Record<string, number | null> {
  if (!isRecord(value)) {
    return {};
  }

  const normalized: Record<string, number | null> = {};

  for (const [periodId, rawValue] of Object.entries(value)) {
    if (periodId.length === 0) {
      continue;
    }

    normalized[periodId] =
      rawValue === null ? null : toNullableInteger(rawValue);
  }

  return normalized;
}

function normalizeRepository(
  value: unknown,
  fallbackRank: number
): RepositoryEntry {
  const record = isRecord(value) ? value : {};

  return {
    id: typeof record.id === "number" ? record.id : undefined,
    rank: toInteger(record.rank, fallbackRank),
    previousRank:
      typeof record.previousRank === "number"
        ? Math.trunc(record.previousRank)
        : typeof record.previous_rank === "number"
          ? Math.trunc(record.previous_rank)
          : null,
    movements: normalizeNullableIntegerRecord(record.movements),
    periodRankings: normalizeNullableIntegerRecord(
      record.periodRankings ?? record.period_rankings
    ),
    periodStarsGained: normalizeNullableIntegerRecord(
      record.periodStarsGained ?? record.period_stars_gained
    ),
    fullName: toString(
      record.fullName ?? record.full_name,
      `unknown/repository-${fallbackRank}`
    ),
    htmlUrl: toSafeHttpsUrl(record.htmlUrl ?? record.html_url, GITHUB_HOSTS),
    stargazersCount: toInteger(
      record.stargazersCount ?? record.stargazers_count
    ),
    language: toNullableString(record.language),
    description: toNullableString(record.description)
  };
}

function normalizeRepositoryList(value: unknown): RepositoryEntry[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((item, index) => normalizeRepository(item, index + 1));
}

function normalizeCategory(
  value: unknown,
  index: number,
  fallbackTag = `CAT-${index + 1}`
): CategoryEntry {
  const record = isRecord(value) ? value : {};
  const tag = toString(record.tag, fallbackTag);

  return {
    tag,
    title: toString(record.title, tag),
    query: toNullableString(record.query),
    description: toNullableString(record.description),
    accent: toNullableString(record.accent),
    items: normalizeRepositoryList(record.items)
  };
}

function normalizeCategories(value: unknown): CategoryEntry[] {
  if (Array.isArray(value)) {
    return value.map((item, index) => normalizeCategory(item, index));
  }

  if (!isRecord(value)) {
    return [];
  }

  return Object.entries(value).map(([tag, section], index) => {
    const record = isRecord(section) ? section : {};

    return normalizeCategory(
      {
        tag,
        ...record
      },
      index,
      tag
    );
  });
}

function normalizePeriod(value: unknown, index: number): PeriodOption {
  const record = isRecord(value) ? value : {};
  const baselineCapturedAt = toNullableString(
    record.baselineCapturedAt ?? record.baseline_captured_at
  );

  return {
    id: toString(record.id, `period-${index + 1}`),
    label: toString(record.label, `Période ${index + 1}`),
    days: toNullableInteger(record.days),
    months: toNullableInteger(record.months),
    available:
      typeof record.available === "boolean"
        ? record.available
        : baselineCapturedAt !== null,
    baselineCapturedAt
  };
}

function normalizePeriods(value: unknown): PeriodOption[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((item, index) => normalizePeriod(item, index));
}

function normalizeHosting(value: unknown): HostingRecommendation[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map((item, index) => {
    const record = isRecord(item) ? item : {};

    return {
      stack: toString(record.stack, `Stack ${index + 1}`),
      hosting: toString(record.hosting, "GitHub Pages"),
      url: toSafeHttpsUrl(record.url, HOSTING_DOC_HOSTS),
      notes: toString(record.notes, "Aucune recommandation disponible."),
      fit: toNullableString(record.fit)
    };
  });
}

function buildLanguageStats(items: RepositoryEntry[]): LanguageStat[] {
  const counts = new Map<string, number>();

  for (const item of items) {
    const language = item.language ?? "Mixed";
    counts.set(language, (counts.get(language) ?? 0) + 1);
  }

  return [...counts.entries()]
    .map(([name, repositoryCount]) => ({
      name,
      repositoryCount
    }))
    .sort(
      (left, right) =>
        right.repositoryCount - left.repositoryCount ||
        left.name.localeCompare(right.name)
    )
    .slice(0, 6);
}

function normalizeStats(
  value: unknown,
  global: GlobalData,
  categories: CategoryEntry[],
  hosting: HostingRecommendation[]
): StatsSummary {
  const record = isRecord(value) ? value : {};
  const computedLanguages = buildLanguageStats(global.items);
  const rawLanguages = Array.isArray(record.languages)
    ? record.languages
        .map((item) => {
          const language = isRecord(item) ? item : {};

          return {
            name: toString(language.name, "Mixed"),
            repositoryCount: toInteger(
              language.repositoryCount ?? language.repository_count
            )
          };
        })
        .filter((item) => item.repositoryCount > 0)
    : computedLanguages;
  const topLanguageRecord = isRecord(record.topLanguage)
    ? record.topLanguage
    : isRecord(record.top_language)
      ? record.top_language
      : null;
  const fallbackTopLanguage =
    rawLanguages.find((item) => item.name !== "Mixed") ??
    rawLanguages[0] ?? {
      name: "Mixed",
      repositoryCount: 0
    };

  return {
    totalStars: toInteger(
      record.totalStars ?? record.total_stars,
      global.items.reduce((sum, item) => sum + item.stargazersCount, 0)
    ),
    repositoryCount: toInteger(
      record.repositoryCount ?? record.repository_count,
      global.items.length
    ),
    categoryCount: toInteger(
      record.categoryCount ?? record.category_count,
      categories.length
    ),
    hostingCount: toInteger(
      record.hostingCount ?? record.hosting_count,
      hosting.length
    ),
    topLanguage: topLanguageRecord
      ? {
          name: toString(topLanguageRecord.name, fallbackTopLanguage.name),
          repositoryCount: toInteger(
            topLanguageRecord.repositoryCount ??
              topLanguageRecord.repository_count,
            fallbackTopLanguage.repositoryCount
          )
        }
      : fallbackTopLanguage,
    languages: rawLanguages.length > 0 ? rawLanguages : computedLanguages
  };
}

function normalizeSiteData(payload: unknown): SiteData {
  const root = isRecord(payload) ? payload : {};
  const snapshotRecord = isRecord(root.snapshot) ? root.snapshot : root;
  const globalRecord = isRecord(root.global) ? root.global : {};
  const globalItems = normalizeRepositoryList(globalRecord.items);
  const highlights = Array.isArray(globalRecord.highlights)
    ? normalizeRepositoryList(globalRecord.highlights)
    : globalItems.slice(0, 3);
  const categories = normalizeCategories(root.categories);
  const hosting = normalizeHosting(root.hosting);
  const periods = normalizePeriods(root.periods);
  const global: GlobalData = {
    title: toString(globalRecord.title, "Global signal"),
    subtitle: toString(
      globalRecord.subtitle,
      "Veille éditoriale des repositories les plus suivis, pensée pour les builders, les équipes plateforme et le recrutement technique."
    ),
    items: globalItems,
    highlights
  };

  return {
    snapshot: {
      capturedAt: toString(
        snapshotRecord.capturedAt ?? snapshotRecord.captured_at,
        new Date().toISOString()
      ),
      label: toNullableString(snapshotRecord.label),
      source: toNullableString(snapshotRecord.source)
    },
    periods,
    global,
    categories,
    hosting,
    stats: normalizeStats(root.stats, global, categories, hosting)
  };
}

export async function getSiteData(): Promise<SiteData> {
  if (!cachedSiteData) {
    cachedSiteData = readFile(DATA_FILE, "utf8")
      .then((content) => normalizeSiteData(JSON.parse(content)))
      .catch((error) => {
        throw new Error(
          `Unable to load site/public/data/site-data.json: ${String(error)}`
        );
      });
  }

  return cachedSiteData;
}
