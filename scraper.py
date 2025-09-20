let jobsData = [];
let activeFilters = new Set();
let searchQuery = "";

// Load jobs.json and render jobs + scraper status
function loadJobs() {
  fetch("jobs.json")
    .then(response => response.json())
    .then(data => {
      // Use today's jobs, or fallback to latest history if today is empty
      const historyKeys = Object.keys(data.history || {});
      const latestHistory = historyKeys.length
        ? data.history[historyKeys[historyKeys.length - 1]]
        : [];
      jobsData = data.today && data.today.length ? data.today : latestHistory;

      console.log("Jobs loaded:", jobsData.length);
      console.log("Scraper results:", data.results);

      renderJobs();
      renderScraperStatus(data.results);
      updateLastUpdated();
    })
    .catch(err => console.error("Error loading jobs:", err));
}

// Render job tiles based on active filters and search
function renderJobs() {
  const container = document.getElementById("jobs");
  container.innerHTML = "";

  let filteredJobs = jobsData.filter(job => {
    let matchFilter =
      activeFilters.size === 0 ||
      job.tags.some(tag => activeFilters.has(tag));
    let matchSearch =
      !searchQuery ||
      job.title.toLowerCase().includes(searchQuery) ||
      (job.company && job.company.toLowerCase().includes(searchQuery));
    return matchFilter && matchSearch;
  });

  if (filteredJobs.length === 0) {
    container.innerHTML = "<p>No jobs match your filters.</p>";
    return;
  }

  filteredJobs.forEach(job => {
    const card = document.createElement("div");
    card.className =
      "job-card p-4 rounded-xl shadow-md bg-white dark:bg-gray-800";
    card.innerHTML = `
      <h3 class="font-bold text-lg mb-2">
        <a href="${job.link}" target="_blank" class="text-blue-600 dark:text-blue-400 hover:underline">
          ${job.title}
        </a>
      </h3>
      <p class="text-sm text-gray-700 dark:text-gray-300">${job.company || ""}</p>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">Source: ${
        job.source
      }</p>
      <div class="flex flex-wrap gap-2">
        ${job.tags
          .map(
            tag =>
              `<span class="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-xs rounded">${tag}</span>`
          )
          .join("")}
      </div>
    `;
    container.appendChild(card);
  });
}

// Toggle a filter button
function toggleFilter(tag) {
  const btn = document.querySelector(`button[data-tag="${tag}"]`);
  if (activeFilters.has(tag)) {
    activeFilters.delete(tag);
    btn.classList.remove("bg-blue-500", "text-white");
  } else {
    activeFilters.add(tag);
    btn.classList.add("bg-blue-500", "text-white");
  }
  renderJobs();
  updateActiveFiltersDisplay();
}

// Clear all filters
function clearFilters() {
  activeFilters.clear();
  document
    .querySelectorAll("#controls button[data-tag]")
    .forEach(btn => btn.classList.remove("bg-blue-500", "text-white"));
  document.getElementById("search").value = "";
  searchQuery = "";
  renderJobs();
  updateActiveFiltersDisplay();
}

// Show active filters and search in summary
function updateActiveFiltersDisplay() {
  const summary = document.getElementById("active-filters");
  const filters = Array.from(activeFilters).join(", ");
  const search = searchQuery ? `Search: "${searchQuery}"` : "";
  summary.textContent =
    (filters ? `Filters: ${filters}` : "") +
    (filters && search ? " | " : "") +
    search;
}

// Render scraper status table
function renderScraperStatus(results) {
  const statusDiv = document.getElementById("scraper-status");
  if (!results) {
    statusDiv.innerHTML = "<p>No scraper status available.</p>";
    return;
  }

  let html =
    '<h2 class="text-lg font-bold mt-6 mb-2">Scraper Status</h2><table class="w-full text-sm border">';
  html +=
    "<tr><th class='border px-2'>Source</th><th class='border px-2'>Status</th></tr>";

  for (const [source, info] of Object.entries(results)) {
    const statusIcon =
      info.status === "success" && info.count > 0
        ? "✅ (" + info.count + ")"
        : info.status === "success"
        ? "❌ (" + info.count + ")"
        : "❌";
    html += `<tr><td class='border px-2'>${source}</td><td class='border px-2'>${statusIcon}</td></tr>`;
  }

  html += "</table>";
  statusDiv.innerHTML = html;
}

// Update last updated date
function updateLastUpdated() {
  const now = new Date();
  const options = {
    timeZone: "America/Phoenix",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  };
  const formatted = new Intl.DateTimeFormat("en-US", options).format(now);
  document.getElementById("last-updated").textContent = `Updated: ${formatted}`;
}

// Search input handler
function onSearchInput(e) {
  searchQuery = e.target.value.toLowerCase();
  renderJobs();
  updateActiveFiltersDisplay();
}

// Initialize page
document.addEventListener("DOMContentLoaded", () => {
  loadJobs();
  document
    .getElementById("search")
    .addEventListener("input", onSearchInput);
});
