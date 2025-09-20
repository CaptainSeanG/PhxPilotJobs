let jobs = [];
let activeFilters = new Set();

async function loadJobs() {
  const response = await fetch("jobs.json");
  const data = await response.json();

  // Fallback: use today first, otherwise latest history entry
  if (data.today && data.today.length > 0) {
    jobs = data.today;
  } else if (data.history) {
    const dates = Object.keys(data.history).sort().reverse();
    if (dates.length > 0) {
      jobs = data.history[dates[0]];
    }
  }

  // Show last updated (Arizona time)
  const lastUpdated = document.getElementById("last-updated");
  const arizonaTime = new Date().toLocaleString("en-US", {
    timeZone: "America/Phoenix",
    dateStyle: "full",
    timeStyle: "short",
  });
  lastUpdated.textContent = "Last updated: " + arizonaTime;

  renderJobs();
  if (data.results) {
    renderStatus(data.results);
  }
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

// Filter toggling + status rendering stay the same...
