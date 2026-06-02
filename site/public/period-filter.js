(() => {
  const storageKey = "github-top50-period";
  const toneClasses = [
    "movement-up",
    "movement-down",
    "movement-steady",
    "movement-new"
  ];

  const enabledButtons = () =>
    Array.from(document.querySelectorAll("[data-period-button]:not(:disabled)"));

  const parseStoredRank = (value) => {
    if (typeof value !== "string" || value.length === 0) {
      return null;
    }

    const parsed = Number(value);

    return Number.isFinite(parsed) ? Math.trunc(parsed) : null;
  };

  const normalizeRank = (value) =>
    typeof value === "number" && Number.isFinite(value)
      ? Math.trunc(value)
      : null;

  const parseMovements = (pill) => {
    try {
      const movements = JSON.parse(pill.dataset.movements || "{}");

      return movements && typeof movements === "object" ? movements : {};
    } catch {
      return {};
    }
  };

  const formatMovement = (rank, previousRank) => {
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
  };

  const validPeriodIds = () =>
    new Set(
      enabledButtons()
        .map((button) => button.dataset.periodId)
        .filter(Boolean)
    );

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

  const updatePills = (periodId) => {
    document.querySelectorAll("[data-movement-pill]").forEach((pill) => {
      const rank = parseStoredRank(pill.dataset.rank);

      if (rank === null) {
        return;
      }

      const movements = parseMovements(pill);
      const hasPeriodRank = Object.prototype.hasOwnProperty.call(movements, periodId);
      const previousRank = hasPeriodRank
        ? normalizeRank(movements[periodId])
        : parseStoredRank(pill.dataset.previousRank);
      const movement = formatMovement(rank, previousRank);

      toneClasses.forEach((className) => pill.classList.remove(className));
      pill.classList.add(`movement-${movement.tone}`);
      pill.textContent = movement.label;
      pill.setAttribute("aria-label", `Mouvement: ${movement.label}`);
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

    updatePills(periodId);

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
