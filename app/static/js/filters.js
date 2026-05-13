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

  for (const button of details.querySelectorAll("[data-action]")) {
    button.addEventListener("click", () => {
      const action = button.dataset.action;
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
        updateSummary(details);
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
      updateSummary(details);
    });
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
});

function isoToday() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function updateScheduleUrl(form, selectedDivisions, selectedTeams, view) {
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
  window.history.replaceState(null, "", url);
}

function wireLiveSchedule(form) {
  const rows = [...document.querySelectorAll("[data-game-row]")];
  const groups = [...document.querySelectorAll("[data-game-group]")];
  const emptyState = document.querySelector("[data-empty-state]");
  const viewSelect = form.querySelector('select[name="view"]');
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

  function applyScheduleFilters() {
    const selectedDivisions = new Set(
      [...form.querySelectorAll('input[name="division"]:checked')].map((input) => input.value)
    );
    const selectedTeams = new Set(
      [...form.querySelectorAll('input[name="team"]:checked')].map((input) => input.value)
    );
    const view = viewSelect ? viewSelect.value : "upcoming";
    const today = isoToday();
    let visibleRows = 0;
    const divisionState = selectionState(divisionCheckboxes, selectedDivisions);
    const teamState = selectionState(teamCheckboxes, selectedTeams);

    for (const row of rows) {
      const divisionId = row.dataset.divisionId || "";
      const homeTeamId = row.dataset.homeTeamId || "";
      const awayTeamId = row.dataset.awayTeamId || "";
      const gameDate = row.dataset.gameDate || "";

      const divisionMatch = selectedDivisions.has(divisionId);
      const teamMatch =
        (selectedTeams.has(homeTeamId) || selectedTeams.has(awayTeamId));

      let viewMatch = true;
      if (view === "upcoming") {
        viewMatch = gameDate === "" || gameDate >= today;
      } else if (view === "to-date") {
        viewMatch = gameDate === "" || gameDate <= today;
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
      const anyVisible = [...group.querySelectorAll("[data-game-row]")].some(
        (row) => row.style.display !== "none"
      );
      group.style.display = anyVisible ? "" : "none";
    }

    if (emptyState) {
      emptyState.hidden = visibleRows !== 0;
    }

    updateScheduleUrl(form, selectedDivisions, selectedTeams, view);
  }

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
  if (teamSearchInput) {
    teamSearchInput.addEventListener("input", () => {
      syncTeamOptions();
      for (const details of form.querySelectorAll("[data-multi-select]")) {
        updateSummary(details);
      }
      applyScheduleFilters();
    });
  }
  for (const button of form.querySelectorAll("[data-action]")) {
    button.addEventListener("click", () => {
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
