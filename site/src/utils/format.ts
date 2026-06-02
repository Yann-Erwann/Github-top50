export interface MovementMeta {
  label: string;
  tone: "up" | "down" | "steady" | "new";
}

export interface PeriodStarsMeta {
  label: string;
  tone: "up" | "down" | "steady" | "new";
}

const compactNumberFormatter = new Intl.NumberFormat("fr-FR", {
  notation: "compact",
  maximumFractionDigits: 1
});

const integerFormatter = new Intl.NumberFormat("fr-FR");

const dateFormatter = new Intl.DateTimeFormat("fr-FR", {
  dateStyle: "medium"
});

export function formatCompactNumber(value: number): string {
  return compactNumberFormatter.format(value);
}

export function formatInteger(value: number): string {
  return integerFormatter.format(value);
}

export function formatSnapshotDate(value: string): string {
  const date = new Date(value);

  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date);
}

export function formatMovement(
  rank: number,
  previousRank: number | null
): MovementMeta {
  if (previousRank === null) {
    return {
      label: "Nouveau",
      tone: "new"
    };
  }

  const delta = previousRank - rank;

  if (delta > 0) {
    return {
      label: `+${delta}`,
      tone: "up"
    };
  }

  if (delta < 0) {
    return {
      label: `${delta}`,
      tone: "down"
    };
  }

  return {
    label: "Stable",
    tone: "steady"
  };
}

export function formatPeriodStars(value: number | null): PeriodStarsMeta {
  if (value === null) {
    return {
      label: "Non suivi",
      tone: "new"
    };
  }

  if (value > 0) {
    return {
      label: formatCompactNumber(value),
      tone: "up"
    };
  }

  if (value < 0) {
    return {
      label: formatCompactNumber(value),
      tone: "down"
    };
  }

  return {
    label: "0",
    tone: "steady"
  };
}
