(() => {
  const storageKey = "github-top50-theme";

  const isTheme = (value) => value === "light" || value === "dark";

  const getInitialTheme = () => {
    const stored = window.localStorage.getItem(storageKey);

    if (isTheme(stored)) {
      return stored;
    }

    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  };

  const applyTheme = (theme) => {
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(theme === "dark"));
      button.textContent = theme === "dark" ? "Mode clair" : "Mode sombre";
    });
  };

  const bindThemeToggle = () => {
    applyTheme(document.documentElement.dataset.theme || getInitialTheme());

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextTheme =
          document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        window.localStorage.setItem(storageKey, nextTheme);
        applyTheme(nextTheme);
      });
    });
  };

  applyTheme(getInitialTheme());

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindThemeToggle, { once: true });
  } else {
    bindThemeToggle();
  }
})();
