let jobs = [];
let activeFilters = new Set();
let scraperResults = {};

async function loadJobs() {
  const response = await fetch("jobs.json");
  const data = await response.json();

  // Set jobs: today first, fallback to latest history
  if (data.today && data.today.length > 0) {
    jobs = data.today;
  } else if (data.history) {
    const dates = Object.keys(data.history).sort().reverse();
    if (dates.length > 0) {
      jobs = data.history[dates[0]];
    }
  }

  // Always grab results if present
  scraperResults = data.results || {};

  // Show last updated (Arizona time)
  const lastUpdated = document.getElementById("last-updated");
  const arizonaTime = new Date().toLocaleString("en-US", {
    timeZone: "America/Phoenix",
    dateStyle: "full",
    timeStyle: "short",
  });
  lastUpdated.textContent = "Last updated: " + arizonaTime;

  renderJobs();
  renderStatus(scraperResults);
}

function renderJobs() {
  const container = document.getElementById("jobs-container");
  container.innerHTML = "";

  const searchValue = document.getElementById("search").value.toLowerCase();

  let filteredJobs = jobs.filter(job => {
    const matchesSearch =
      job.title.toLowerCase().includes(searchValue) ||
      job.company.toLowerCase().includes(searchValue);
    const matchesFilter =
      activeFilters.size === 0 ||
      job.tags.some(tag => activeFilters.has(tag));
    return matchesSearch && matchesFilter;
  });

  filteredJobs.forEach(job => {
    const div = document.createElement("div");
    div.className = "job-card";
    div.innerHTML = `
      <h3><a href="${job.link}" target="_blank">${job.title}</a></h3>
      <p><strong>${job.company}</strong></p>
      <p><em>${job.source}</em></p>
      <p>${job.tags.join(", ")}</p>
    `;
    container.appendChild(div);
  });

  renderFilterSummary(searchValue);
}

function toggleFilter(tag) {
  const button = document.querySelector(`button[data-tag="${tag}"]`);
  if (activeFilters.has(tag)) {
    activeFilters.delete(tag);
    button.classList.remove("active");
  } else {
    activeFilters.add(tag);
    button.classList.add("active");
  }
  renderJobs();
}

function clearFilters() {
  activeFilters.clear();
  document.querySelectorAll(".controls button").forEach(btn => {
    btn.classList.remove("active");
  });
  renderJobs();
}

function renderFilterSummary(searchValue) {
  const summary = document.getElementById("filter-summary");
  let text = "";

  if (activeFilters.size > 0) {
    text += "Active filters: " + Array.from(activeFilters).join(", ");
  }
  if (searchValue) {
    if (text) text += " | ";
    text += `Search: "${searchValue}"`;
  }
  if (!text) {
    text = "No filters active";
  }
  summary.textContent = text;
}

function renderStatus(results) {
  const tbody = document.querySelector("#status-table tbody");
  tbody.innerHTML = "";

  if (!results || Object.keys(results).length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="2" style="text-align:center; padding:8px;">
      No scraper status available
    </td>`;
    tbody.appendChild(tr);
    return;
  }

  for (const [source, info] of Object.entries(results)) {
    const statusIcon = info.status === "success" ? "✅" : "❌";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="padding:8px; border:1px solid #ddd;">${source}</td>
      <td style="padding:8px; border:1px solid #ddd; text-align:center;">
        ${statusIcon} (${info.count})
      </td>
    `;
    tbody.appendChild(tr);
  }
}

window.onload = loadJobs;
