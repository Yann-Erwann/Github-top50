(() => {
  const storageKey = "github-top50-period";
  const toneClasses = [
    "movement-up",
    "movement-down",
    "movement-steady",
    "movement-new"
  ];
  const compactNumberFormatter = new Intl.NumberFormat("fr-FR", {
    notation: "compact",
    maximumFractionDigits: 1
  });
  const integerFormatter = new Intl.NumberFormat("fr-FR");

  const enabledButtons = () =>
    Array.from(document.querySelectorAll("[data-period-button]:not(:disabled)"));

  const parseStoredNumber = (value) => {
    if (typeof value !== "string" || value.length === 0) {
      return null;
    }

    const parsed = Number(value);

    return Number.isFinite(parsed) ? Math.trunc(parsed) : null;
  };

  const normalizeNumber = (value) =>
    typeof value === "number" && Number.isFinite(value)
      ? Math.trunc(value)
      : null;

  const parsePeriodValues = (row, key) => {
    try {
      const values = JSON.parse(row.dataset[key] || "{}");

      return values && typeof values === "object" ? values : {};
    } catch {
      return {};
    }
  };

  const periodValue = (row, key, periodId) => {
    const values = parsePeriodValues(row, key);

    return Object.prototype.hasOwnProperty.call(values, periodId)
      ? normalizeNumber(values[periodId])
      : null;
  };

  const formatStarsGained = (value) => {
    if (value === null) {
      return {
        label: "Non suivi",
        tone: "new"
      };
    }

    if (value > 0) {
      return {
        label: `+${compactNumberFormatter.format(value)}`,
        tone: "up"
      };
    }

    if (value < 0) {
      return {
        label: compactNumberFormatter.format(value),
        tone: "down"
      };
    }

    return {
      label: "0",
      tone: "steady"
    };
  };

  const validPeriodIds = () =>
    new Set(
      enabledButtons()
        .map((button) => button.dataset.periodId)
        .filter(Boolean)
    );

  const periodContext = (periodId) => {
    const button = enabledButtons().find(
      (candidate) => candidate.dataset.periodId === periodId
    );

    return {
      label: button?.dataset.periodLabel || periodId,
      baselineLabel: button?.dataset.baselineLabel || "Historique indisponible"
    };
  };

  const readStoredPeriod = () => {
    try {
      return window.localStorage.getItem(storageKey);
    } catch {
      return null;
    }
  };

  const storePeriod = (periodId) => {
    try {
      window.localStorage.setItem(storageKey, periodId);
    } catch {
      // Storage can be disabled without affecting the selector itself.
    }
  };

  const initialPeriod = () => {
    const validIds = validPeriodIds();
    const params = new URLSearchParams(window.location.search);
    const queryPeriod = params.get("periode");

    if (queryPeriod && validIds.has(queryPeriod)) {
      return {
        periodId: queryPeriod,
        persist: true
      };
    }

    const storedPeriod = readStoredPeriod();

    if (storedPeriod && validIds.has(storedPeriod)) {
      return {
        periodId: storedPeriod,
        persist: false
      };
    }

    const defaultPeriod = document.querySelector("[data-period-filter]")?.dataset
      .defaultPeriod;

    if (defaultPeriod && validIds.has(defaultPeriod)) {
      return {
        periodId: defaultPeriod,
        persist: false
      };
    }

    return {
      periodId: enabledButtons()[0]?.dataset.periodId || null,
      persist: false
    };
  };

  const updateUrl = (periodId) => {
    const url = new URL(window.location.href);
    url.searchParams.set("periode", periodId);
    window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  };

  const updateLists = (periodId) => {
    const context = periodContext(periodId);

    document.querySelectorAll("[data-repo-list]").forEach((list) => {
      const maxItems = parseStoredNumber(list.dataset.maxItems);
      const rows = Array.from(list.querySelectorAll(":scope > [data-repo-row]"))
        .map((row) => ({
          currentRank: parseStoredNumber(row.dataset.currentRank),
          periodRank: periodValue(row, "periodRankings", periodId),
          starsGained: periodValue(row, "periodStarsGained", periodId),
          row
        }))
        .sort((left, right) => {
          if (left.periodRank === null) {
            return right.periodRank === null
              ? (left.currentRank || 0) - (right.currentRank || 0)
              : 1;
          }

          return right.periodRank === null
            ? -1
            : left.periodRank - right.periodRank;
        });

      rows.forEach(({ periodRank, starsGained, row }, index) => {
        const rank = row.querySelector("[data-period-rank]");
        const pill = row.querySelector("[data-stars-gained]");
        const formattedStars = formatStarsGained(starsGained);

        list.appendChild(row);
        row.hidden = maxItems !== null && index >= maxItems;

        if (rank) {
          rank.textContent =
            periodRank === null ? "#—" : `#${integerFormatter.format(periodRank)}`;
        }

        if (pill) {
          toneClasses.forEach((className) => pill.classList.remove(className));
          pill.classList.add(`movement-${formattedStars.tone}`);
          pill.textContent = formattedStars.label;
          pill.setAttribute(
            "aria-label",
            starsGained === null
              ? "Étoiles gagnées: historique non suivi"
              : `Étoiles gagnées: ${integerFormatter.format(starsGained)}`
          );
        }
      });

      list.setAttribute(
        "aria-label",
        `Classement par étoiles gagnées sur ${context.label}`
      );
    });
  };

  const updatePeriodContext = (periodId) => {
    const context = periodContext(periodId);

    document.querySelectorAll("[data-period-status]").forEach((status) => {
      status.textContent =
        `Classement par étoiles gagnées · ${context.label} · ${context.baselineLabel}`;
    });

    document.querySelectorAll("[data-period-rank-heading]").forEach((heading) => {
      heading.textContent = `Rank · ${context.label}`;
    });

    document
      .querySelectorAll("[data-period-column-heading]")
      .forEach((heading) => {
        heading.textContent = `Gagnés · ${context.label}`;
      });
  };

  const applyPeriod = (periodId, options = {}) => {
    if (!periodId || !validPeriodIds().has(periodId)) {
      return;
    }

    document.querySelectorAll("[data-period-button]").forEach((button) => {
      const selected = button.dataset.periodId === periodId;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-checked", String(selected));
    });

    updateLists(periodId);
    updatePeriodContext(periodId);

    if (options.persist) {
      storePeriod(periodId);
    }

    if (options.updateUrl) {
      updateUrl(periodId);
    }
  };

  const bindButtons = () => {
    document.querySelectorAll("[data-period-button]").forEach((button) => {
      button.addEventListener("click", () => {
        applyPeriod(button.dataset.periodId, {
          persist: true,
          updateUrl: true
        });
      });
    });
  };

  const bindKeyboard = () => {
    document.querySelectorAll("[data-period-filter]").forEach((filter) => {
      filter.addEventListener("keydown", (event) => {
        const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];

        if (!keys.includes(event.key)) {
          return;
        }

        const buttons = Array.from(
          filter.querySelectorAll("[data-period-button]:not(:disabled)")
        );
        const currentIndex = buttons.indexOf(document.activeElement);

        if (currentIndex === -1 || buttons.length === 0) {
          return;
        }

        event.preventDefault();

        const nextIndex =
          event.key === "Home"
            ? 0
            : event.key === "End"
              ? buttons.length - 1
              : event.key === "ArrowRight"
                ? (currentIndex + 1) % buttons.length
                : (currentIndex - 1 + buttons.length) % buttons.length;
        const nextButton = buttons[nextIndex];

        nextButton.focus();
        nextButton.click();
      });
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    const initial = initialPeriod();

    bindButtons();
    bindKeyboard();

    if (initial.periodId) {
      applyPeriod(initial.periodId, {
        persist: initial.persist,
        updateUrl: false
      });
    }
  });
})();
