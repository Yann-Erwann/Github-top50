(() => {
  const form = document.querySelector("[data-top-form]");
  const list = document.querySelector("#top-repositories");

  if (!form || !list) {
    return;
  }

  const items = Array.from(list.querySelectorAll("[data-repo-item]"));
  const count = document.querySelector("[data-top-count]");
  const empty = document.querySelector("[data-top-empty]");
  const movementWeight = { up: 0, new: 1, steady: 2, down: 3 };

  const sortItems = (collection, value) => {
    const sorted = [...collection];

    sorted.sort((left, right) => {
      if (value === "stars") {
        return Number(right.dataset.stars) - Number(left.dataset.stars);
      }

      if (value === "movement") {
        return (
          movementWeight[left.dataset.movement] - movementWeight[right.dataset.movement] ||
          Number(left.dataset.rank) - Number(right.dataset.rank)
        );
      }

      if (value === "name") {
        return (left.dataset.name || "").localeCompare(right.dataset.name || "", "fr");
      }

      return Number(left.dataset.rank) - Number(right.dataset.rank);
    });

    return sorted;
  };

  const getFormValue = (name, fallback = "") => {
    const field = form.querySelector(`[name='${name}']`);
    return field ? String(field.value || fallback) : fallback;
  };

  const update = () => {
    const search = getFormValue("search").toLowerCase().trim();
    const language = getFormValue("language");
    const movement = getFormValue("movement");
    const sort = getFormValue("sort", "rank");

    const visible = items.filter((item) => {
      const matchesSearch = !search || String(item.dataset.search || "").includes(search);
      const matchesLanguage = !language || item.dataset.language === language;
      const matchesMovement = !movement || item.dataset.movement === movement;
      const matches = matchesSearch && matchesLanguage && matchesMovement;

      item.hidden = !matches;
      return matches;
    });

    sortItems(visible, sort).forEach((item) => list.appendChild(item));

    if (count) {
      count.textContent =
        `${visible.length} résultat${visible.length > 1 ? "s" : ""} sur ${items.length}`;
    }

    if (empty) {
      empty.hidden = visible.length > 0;
    }
  };

  form.addEventListener("input", update);
  form.addEventListener("change", update);
  update();
})();
