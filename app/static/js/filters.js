function updateSummary(details) {
  const summary = details.querySelector(".multi-select-summary");
  if (!summary) return;
  const defaultLabel = details.dataset.defaultLabel || "All";
  const checkboxes = [...details.querySelectorAll('input[type="checkbox"]')];
  const checked = checkboxes.filter((input) => input.checked).length;
  if (checked === 0) {
    summary.textContent = "None selected";
  } else if (checked === checkboxes.length) {
    summary.textContent = defaultLabel;
  } else {
    summary.textContent = `${checked} selected`;
  }
}

function wireMultiSelect(details) {
  const checkboxes = [...details.querySelectorAll('input[type="checkbox"]')];
  const searchInput = details.querySelector("[data-filter-input]");
  const optionLabels = [...details.querySelectorAll("[data-filter-option]")];

  for (const checkbox of checkboxes) {
    checkbox.addEventListener("change", () => updateSummary(details));
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const term = searchInput.value.toLowerCase();
      for (const label of optionLabels) {
        const text = label.textContent.toLowerCase();
        if (!label.closest("[data-selected-options]")) {
          label.style.display = term !== "" && !text.includes(term) ? "none" : "";
        }
      }
    });
    details.addEventListener("toggle", () => {
      if (details.open) {
        searchInput.focus();
        searchInput.select();
      }
    });
  }

  updateSummary(details);
}

for (const details of document.querySelectorAll("[data-multi-select]")) {
  wireMultiSelect(details);
}

document.addEventListener("click", (event) => {
  for (const details of document.querySelectorAll("[data-multi-select]")) {
    if (!details.open) {
      continue;
    }
    if (!details.contains(event.target)) {
      details.open = false;
    }
  }
  for (const details of document.querySelectorAll("[data-home-team-picker]")) {
    if (!details.open) {
      continue;
    }
    if (!details.contains(event.target)) {
      details.open = false;
    }
  }
});

function isoToday() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function isoDaysAgo(daysAgo) {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  now.setDate(now.getDate() - daysAgo);
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseIsoDay(value) {
  if (!value) {
    return null;
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }
  const [, year, month, day] = match;
  return Date.UTC(Number(year), Number(month) - 1, Number(day));
}

function wireGameGroupToggles() {
  for (const button of document.querySelectorAll("[data-game-group-toggle]")) {
    const group = button.closest("[data-game-group]");
    if (!group) {
      continue;
    }
    const label = group.querySelector("h3")?.textContent.trim() || "this date";
    const syncToggle = () => {
      const isCollapsed = group.dataset.collapsed === "true";
      button.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
      button.setAttribute(
        "aria-label",
        `${isCollapsed ? "Expand" : "Collapse"} ${label}`
      );
      button.title = `${isCollapsed ? "Expand" : "Collapse"} ${label}`;
    };

    button.addEventListener("click", () => {
      group.dataset.collapsed = group.dataset.collapsed === "true" ? "false" : "true";
      syncToggle();
    });
    button.addEventListener("pointerup", () => button.blur());
    syncToggle();
  }
}

wireGameGroupToggles();

function updateScheduleUrl(form, selectedDivisions, selectedTeams, view, order) {
  const url = new URL(window.location.href);
  url.searchParams.delete("division");
  url.searchParams.delete("team");
  const divisionCheckboxes = [
    ...form.querySelectorAll('input[name="division"][type="checkbox"]'),
  ];
  const teamCheckboxes = [...form.querySelectorAll('input[name="team"][type="checkbox"]')];
  if (
    selectedDivisions.size > 0 &&
    selectedDivisions.size < divisionCheckboxes.length
  ) {
    for (const division of selectedDivisions) {
      url.searchParams.append("division", division);
    }
  }
  if (selectedTeams.size > 0 && selectedTeams.size < teamCheckboxes.length) {
    for (const team of selectedTeams) {
      url.searchParams.append("team", team);
    }
  }
  url.searchParams.set("view", view);
  url.searchParams.set("order", order);
  window.history.replaceState(null, "", url);
}

function wireLiveSchedule(form) {
  const rows = [...document.querySelectorAll("[data-game-row]")];
  const groups = [...document.querySelectorAll("[data-game-group]")];
  const emptyState = document.querySelector("[data-empty-state]");
  const viewSelect = form.querySelector('select[name="view"]');
  const orderSelect = form.querySelector('select[name="order"]');
  const divisionCheckboxes = [
    ...form.querySelectorAll('input[name="division"][type="checkbox"]'),
  ];
  const teamCheckboxes = [...form.querySelectorAll('input[name="team"][type="checkbox"]')];
  const teamOptions = [
    ...form.querySelectorAll('.multi-select-teams [data-filter-option]'),
  ];
  const teamSearchInput = form.querySelector('.multi-select-teams [data-filter-input]');
  const teamSelectedSection = form.querySelector(".multi-select-teams [data-selected-section]");
  const teamSelectedOptions = form.querySelector(".multi-select-teams [data-selected-options]");
  const teamAvailableOptions = form.querySelector(".multi-select-teams [data-available-options]");
  const divisionDetails = form.querySelector(".multi-select-divisions");
  const teamDetails = form.querySelector(".multi-select-teams");

  if (divisionCheckboxes.every((input) => !input.checked)) {
    for (const input of divisionCheckboxes) {
      input.checked = true;
    }
  }
  if (teamCheckboxes.every((input) => !input.checked)) {
    for (const input of teamCheckboxes) {
      input.checked = true;
    }
  }
  for (const details of form.querySelectorAll("[data-multi-select]")) {
    updateSummary(details);
  }
  for (const [index, group] of groups.entries()) {
    group.dataset.originalIndex = String(index);
    const groupRows = [...group.querySelectorAll("[data-game-row]")];
    for (const [rowIndex, row] of groupRows.entries()) {
      row.dataset.originalIndex = String(rowIndex);
    }
  }

  function selectionState(allCheckboxes, selectedValues) {
    if (selectedValues.size === 0) {
      return "empty";
    }
    if (selectedValues.size === allCheckboxes.length) {
      return "all";
    }
    return "partial";
  }

  function syncTeamOptions() {
    const selectedDivisions = new Set(
      divisionCheckboxes.filter((input) => input.checked).map((input) => input.value)
    );
    const divisionState = selectionState(
      divisionCheckboxes,
      selectedDivisions
    );
    const searchTerm = teamSearchInput
      ? teamSearchInput.value.toLowerCase()
      : "";

    for (const option of teamOptions) {
      const optionDivisionId = option.dataset.divisionId || "";
      const checkbox = option.querySelector('input[type="checkbox"]');
      const divisionVisible =
        divisionState === "all"
          ? true
          : divisionState === "empty"
            ? false
            : selectedDivisions.has(optionDivisionId);
      if (checkbox && !divisionVisible) {
        checkbox.checked = false;
      }
      const isSelected = Boolean(checkbox && checkbox.checked);
      const searchVisible =
        searchTerm === "" ||
        option.textContent.toLowerCase().includes(searchTerm);

      if (isSelected && teamSelectedOptions) {
        teamSelectedOptions.appendChild(option);
        option.style.display = "";
        continue;
      }

      if (teamAvailableOptions) {
        teamAvailableOptions.appendChild(option);
      }
      option.style.display = divisionVisible && searchVisible ? "" : "none";
    }

    if (teamSelectedSection && teamSelectedOptions) {
      teamSelectedSection.hidden = teamSelectedOptions.children.length === 0;
    }
  }

  function applyBulkAction(details, action) {
    if (!details) {
      return;
    }

    const checkboxes = [...details.querySelectorAll('input[type="checkbox"]')];
    const searchInput = details.querySelector("[data-filter-input]");
    const optionLabels = [...details.querySelectorAll("[data-filter-option]")];

    if (action === "reset") {
      if (searchInput) {
        searchInput.value = "";
      }
      for (const checkbox of checkboxes) {
        checkbox.checked = true;
      }
      for (const label of optionLabels) {
        label.style.display = "";
      }
      return;
    }

    const checked = action === "all";
    const visibleOptions = optionLabels.filter((label) => label.style.display !== "none");
    const targetCheckboxes =
      visibleOptions.length > 0
        ? visibleOptions
            .map((label) => label.querySelector('input[type="checkbox"]'))
            .filter(Boolean)
        : checkboxes;
    for (const checkbox of targetCheckboxes) {
      checkbox.checked = checked;
    }
  }

  function applyScheduleFilters() {
    const selectedDivisions = new Set(
      [...form.querySelectorAll('input[name="division"]:checked')].map((input) => input.value)
    );
    const selectedTeams = new Set(
      [...form.querySelectorAll('input[name="team"]:checked')].map((input) => input.value)
    );
    const view = viewSelect ? viewSelect.value : "upcoming";
    const order = orderSelect ? orderSelect.value : "oldest";
    const today = form.dataset.todayIso || isoToday();
    const lastThreeStart = isoDaysAgo(2);
    const todayDay = parseIsoDay(today);
    const lastThreeStartDay = todayDay === null ? parseIsoDay(lastThreeStart) : todayDay - (2 * 24 * 60 * 60 * 1000);
    let visibleRows = 0;
    const divisionState = selectionState(divisionCheckboxes, selectedDivisions);
    const teamState = selectionState(teamCheckboxes, selectedTeams);

    for (const row of rows) {
      const divisionId = row.dataset.divisionId || "";
      const homeTeamId = row.dataset.homeTeamId || "";
      const awayTeamId = row.dataset.awayTeamId || "";
      const gameDate = row.dataset.gameDate || "";
      const gameDay = parseIsoDay(gameDate);

      const divisionMatch = selectedDivisions.has(divisionId);
      const teamMatch =
        (selectedTeams.has(homeTeamId) || selectedTeams.has(awayTeamId));

      let viewMatch = true;
      if (view === "upcoming") {
        viewMatch = gameDay === null || (todayDay !== null && gameDay >= todayDay);
      } else if (view === "last-3") {
        viewMatch =
          gameDay !== null &&
          lastThreeStartDay !== null &&
          todayDay !== null &&
          gameDay >= lastThreeStartDay &&
          gameDay <= todayDay;
      } else if (view === "to-date") {
        viewMatch = gameDay === null || (todayDay !== null && gameDay <= todayDay);
      }

      let selectionMatch = false;
      if (divisionState === "empty" || teamState === "empty") {
        selectionMatch = false;
      } else if (divisionState === "all" && teamState === "all") {
        selectionMatch = true;
      } else {
        const partialMatches = [];
        if (divisionState === "partial") {
          partialMatches.push(divisionMatch);
        }
        if (teamState === "partial") {
          partialMatches.push(teamMatch);
        }

        if (partialMatches.length > 0) {
          selectionMatch = partialMatches.every(Boolean);
        } else {
          selectionMatch = false;
        }
      }

      const visible = selectionMatch && viewMatch;
      row.style.display = visible ? "" : "none";
      if (visible) {
        visibleRows += 1;
      }
    }

    for (const group of groups) {
      const table = group.querySelector(".game-table");
      const groupRows = [...group.querySelectorAll("[data-game-row]")];
      const orderedRows = [...groupRows].sort((a, b) => {
        const aIndex = Number(a.dataset.originalIndex || "0");
        const bIndex = Number(b.dataset.originalIndex || "0");
        return order === "newest" ? bIndex - aIndex : aIndex - bIndex;
      });
      for (const row of orderedRows) {
        table?.appendChild(row);
      }

      const anyVisible = [...group.querySelectorAll("[data-game-row]")].some(
        (row) => row.style.display !== "none"
      );
      group.style.display = anyVisible ? "" : "none";
    }

    const orderedGroups = [...groups].sort((a, b) => {
      const aDate = a.dataset.groupDate || "";
      const bDate = b.dataset.groupDate || "";
      const aIndex = Number(a.dataset.originalIndex || "0");
      const bIndex = Number(b.dataset.originalIndex || "0");

      if (aDate === bDate) {
        return order === "newest" ? bIndex - aIndex : aIndex - bIndex;
      }
      if (!aDate) {
        return 1;
      }
      if (!bDate) {
        return -1;
      }
      return order === "newest"
        ? bDate.localeCompare(aDate)
        : aDate.localeCompare(bDate);
    });
    for (const group of orderedGroups) {
      group.parentNode?.appendChild(group);
    }

    if (emptyState) {
      emptyState.hidden = visibleRows !== 0;
    }

    updateScheduleUrl(form, selectedDivisions, selectedTeams, view, order);
  }

  form.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement)) {
      return;
    }
    syncTeamOptions();
    for (const details of form.querySelectorAll("[data-multi-select]")) {
      updateSummary(details);
    }
    applyScheduleFilters();
  });

  for (const input of form.querySelectorAll('input[type="checkbox"]')) {
    input.addEventListener("change", () => {
      syncTeamOptions();
      for (const details of form.querySelectorAll("[data-multi-select]")) {
        updateSummary(details);
      }
      applyScheduleFilters();
    });
  }
  if (viewSelect) {
    viewSelect.addEventListener("change", applyScheduleFilters);
  }
  if (orderSelect) {
    orderSelect.addEventListener("change", applyScheduleFilters);
  }
  if (teamSearchInput) {
    teamSearchInput.addEventListener("input", () => {
      syncTeamOptions();
      for (const details of form.querySelectorAll("[data-multi-select]")) {
        updateSummary(details);
      }
      applyScheduleFilters();
    });
  }
  for (const button of form.querySelectorAll("[data-filter-actions] [data-action]")) {
    button.addEventListener("click", () => {
      const target = button.closest("[data-filter-actions]")?.dataset.filterActions;
      applyBulkAction(
        target === "division" ? divisionDetails : target === "team" ? teamDetails : null,
        button.dataset.action
      );
      syncTeamOptions();
      for (const details of form.querySelectorAll("[data-multi-select]")) {
        updateSummary(details);
      }
      applyScheduleFilters();
    });
  }
  syncTeamOptions();
  applyScheduleFilters();
}

for (const form of document.querySelectorAll("[data-live-schedule]")) {
  wireLiveSchedule(form);
}

function sortableValue(row, columnIndex, type) {
  const cell = row.cells[columnIndex];
  const text = cell ? cell.textContent.trim() : "";
  if (text === "" || text === "-") {
    return { missing: true, value: null };
  }
  if (type === "text") {
    return { missing: false, value: text.toLowerCase() };
  }
  if (type === "record") {
    const parts = text.split("-").map((part) => Number.parseFloat(part));
    if (parts.some((part) => Number.isNaN(part))) {
      return { missing: true, value: null };
    }
    return { missing: false, value: parts };
  }
  const number = Number.parseFloat(text.replace(/,/g, ""));
  return Number.isNaN(number)
    ? { missing: true, value: null }
    : { missing: false, value: number };
}

function compareSortableValues(a, b, direction) {
  if (a.missing || b.missing) {
    if (a.missing && b.missing) {
      return 0;
    }
    return a.missing ? 1 : -1;
  }
  if (Array.isArray(a.value) && Array.isArray(b.value)) {
    for (let index = 0; index < Math.max(a.value.length, b.value.length); index += 1) {
      const left = a.value[index] ?? 0;
      const right = b.value[index] ?? 0;
      if (left !== right) {
        return direction === "asc" ? left - right : right - left;
      }
    }
    return 0;
  }
  if (typeof a.value === "number" && typeof b.value === "number") {
    return direction === "asc" ? a.value - b.value : b.value - a.value;
  }
  const result = String(a.value).localeCompare(String(b.value), undefined, {
    numeric: true,
    sensitivity: "base",
  });
  return direction === "asc" ? result : -result;
}

function initialSortDirection(button) {
  const columnIndex = Number(button.dataset.sortColumn || "0");
  const type = button.dataset.sortType || "text";
  return type === "text" || columnIndex === 0 ? "asc" : "desc";
}

function nextSortDirection(button) {
  const currentDirection = button.dataset.sortDirection || "off";
  const initialDirection = initialSortDirection(button);
  if (currentDirection === "off") {
    return initialDirection;
  }
  return currentDirection === initialDirection
    ? initialDirection === "asc"
      ? "desc"
      : "asc"
    : "off";
}

function wireSortableTable(table) {
  const body = table.tBodies[0];
  if (!body) {
    return;
  }
  const rows = [...body.rows];
  const buttons = [...table.querySelectorAll("[data-sort-column]")];

  for (const [index, row] of rows.entries()) {
    row.dataset.sortOriginalIndex = String(index);
  }

  function syncSortButtons(activeButton, direction) {
    for (const button of buttons) {
      const header = button.closest("th");
      const isActive = button === activeButton && direction !== "off";
      button.dataset.sortDirection = isActive ? direction : "off";
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
      if (header) {
        header.setAttribute(
          "aria-sort",
          isActive ? (direction === "asc" ? "ascending" : "descending") : "none"
        );
      }
    }
  }

  for (const button of buttons) {
    button.dataset.sortDirection = "off";
    button.setAttribute("aria-pressed", "false");
    button.closest("th")?.setAttribute("aria-sort", "none");
    button.addEventListener("click", () => {
      const direction = nextSortDirection(button);
      syncSortButtons(button, direction);

      const orderedRows =
        direction === "off"
          ? [...rows].sort(
              (a, b) =>
                Number(a.dataset.sortOriginalIndex || "0") -
                Number(b.dataset.sortOriginalIndex || "0")
            )
          : [...rows].sort((a, b) => {
              const columnIndex = Number(button.dataset.sortColumn || "0");
              const type = button.dataset.sortType || "text";
              const result = compareSortableValues(
                sortableValue(a, columnIndex, type),
                sortableValue(b, columnIndex, type),
                direction
              );
              if (result !== 0) {
                return result;
              }
              return (
                Number(a.dataset.sortOriginalIndex || "0") -
                Number(b.dataset.sortOriginalIndex || "0")
              );
            });

      for (const row of orderedRows) {
        body.appendChild(row);
      }
    });
  }
}

for (const table of document.querySelectorAll("[data-sortable-table]")) {
  wireSortableTable(table);
}

function wireRosterToggle(toggle) {
  const panel = toggle.closest(".panel");
  if (!panel) {
    return;
  }
  const blocks = [...panel.querySelectorAll("[data-roster-block]")];

  function applyRosterFilter() {
    const onlyActive = toggle.checked;
    for (const block of blocks) {
      const rows = [...block.querySelectorAll("[data-roster-row]")];
      let visibleRows = 0;
      for (const row of rows) {
        const gp = Number(row.dataset.gp || "0");
        const visible = !onlyActive || gp > 0;
        row.style.display = visible ? "" : "none";
        if (visible) {
          visibleRows += 1;
        }
      }
      block.style.display = visibleRows > 0 ? "" : "none";
    }
  }

  toggle.addEventListener("change", applyRosterFilter);
  applyRosterFilter();
}

for (const toggle of document.querySelectorAll("[data-roster-toggle]")) {
  wireRosterToggle(toggle);
}

function wireHomeTeamPicker(details) {
  const input = details.querySelector("[data-home-team-input]");
  const options = [...details.querySelectorAll("[data-home-team-option]")];
  if (!input) {
    return;
  }

  function applyFilter() {
    const term = input.value.toLowerCase();
    for (const option of options) {
      const visible = term === "" || option.textContent.toLowerCase().includes(term);
      option.style.display = visible ? "" : "none";
    }
  }

  input.addEventListener("input", applyFilter);
  details.addEventListener("toggle", () => {
    if (details.open) {
      input.focus();
      input.select();
    }
  });
  for (const option of options) {
    option.addEventListener("click", () => {
      details.open = false;
    });
  }
  applyFilter();
}

for (const details of document.querySelectorAll("[data-home-team-picker]")) {
  wireHomeTeamPicker(details);
}

function updateTeamScheduleUrl(form, view, order) {
  const url = new URL(window.location.href);
  url.searchParams.set("view", view);
  url.searchParams.set("order", order);
  window.history.replaceState(null, "", url);
}

function wireTeamSchedule(form) {
  const panel = form.closest(".panel");
  if (!panel) {
    return;
  }
  const rows = [...panel.querySelectorAll("[data-game-row]")];
  const table = panel.querySelector(".game-table-inline");
  const emptyState = panel.querySelector("[data-team-empty-state]");
  const viewSelect = form.querySelector('select[name="view"]');
  const orderSelect = form.querySelector('select[name="order"]');

  if (!table || !viewSelect || !orderSelect) {
    return;
  }

  for (const [index, row] of rows.entries()) {
    row.dataset.originalIndex = String(index);
  }

  function applyTeamScheduleFilters() {
    const view = viewSelect.value;
    const order = orderSelect.value;
    const today = form.dataset.todayIso || isoToday();
    const todayDay = parseIsoDay(today);
    const lastThreeStartDay = todayDay === null ? null : todayDay - (2 * 24 * 60 * 60 * 1000);
    let visibleRows = 0;

    for (const row of rows) {
      const gameDate = row.dataset.gameDate || "";
      const gameDay = parseIsoDay(gameDate);
      let viewMatch = true;
      if (view === "upcoming") {
        viewMatch = gameDay === null || (todayDay !== null && gameDay >= todayDay);
      } else if (view === "last-3") {
        viewMatch =
          gameDay !== null &&
          lastThreeStartDay !== null &&
          todayDay !== null &&
          gameDay >= lastThreeStartDay &&
          gameDay <= todayDay;
      } else if (view === "to-date") {
        viewMatch = gameDay === null || (todayDay !== null && gameDay <= todayDay);
      }
      row.style.display = viewMatch ? "" : "none";
      if (viewMatch) {
        visibleRows += 1;
      }
    }

    const orderedRows = [...rows].sort((a, b) => {
      const aDate = a.dataset.gameDate || "";
      const bDate = b.dataset.gameDate || "";
      const aStarts = a.dataset.gameStartsAt || "";
      const bStarts = b.dataset.gameStartsAt || "";
      const aIndex = Number(a.dataset.originalIndex || "0");
      const bIndex = Number(b.dataset.originalIndex || "0");

      const aKey = `${aDate}|${aStarts}|${aIndex}`;
      const bKey = `${bDate}|${bStarts}|${bIndex}`;
      return order === "newest" ? bKey.localeCompare(aKey) : aKey.localeCompare(bKey);
    });
    for (const row of orderedRows) {
      table.appendChild(row);
    }

    if (emptyState) {
      emptyState.hidden = visibleRows !== 0;
    }
    updateTeamScheduleUrl(form, view, order);
  }

  viewSelect.addEventListener("change", applyTeamScheduleFilters);
  orderSelect.addEventListener("change", applyTeamScheduleFilters);
  applyTeamScheduleFilters();
}

for (const form of document.querySelectorAll("[data-live-team-schedule]")) {
  wireTeamSchedule(form);
}
