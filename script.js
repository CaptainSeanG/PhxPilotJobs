let activeFilters = [];

async function loadJobs() {
  try {
    const response = await fetch("jobs.json");
    const data = await response.json();

    const jobs = data.today || [];
    const results = data.results || {};

    console.log("Jobs loaded:", jobs.length);
    console.log("Scraper results:", results);

    renderJobs(jobs);
    updateScraperStatus(results);

    // Update last updated timestamp (Arizona time)
    const updatedEl = document.getElementById("last-updated");
    const now = new Date();
    updatedEl.textContent = "Updated: " + now.toLocaleString("en-US", { timeZone: "America/Phoenix" });

  } catch (err) {
    console.error("Error loading jobs.json", err);
  }
}

function renderJobs(jobs) {
  const container = document.getElementById("jobs-container");
  container.innerHTML = "";

  jobs.forEach(job => {
    // Apply filters
    if (activeFilters.length > 0) {
      const jobTags = job.tags || [];
      let match = false;

      // Special filter for Low-Time
      if (activeFilters.includes("LowTime") && job.hours_required && job.hours_required <= 1100) {
        match = true;
      }

      // Regular tag matching
      if (jobTags.some(tag => activeFilters.includes(tag))) {
        match = true;
      }

      if (!match) return; // skip this job
    }

    const tile = document.createElement("div");
    tile.className = "job-tile";

    // ✅ highlight jobs with <= 1100 hours required
    let lowTimeBadge = "";
    if (job.hours_required && job.hours_required <= 1100) {
      tile.style.border = "3px solid green";
      lowTimeBadge = `<div class="low-time-badge">Low-Time Friendly</div>`;
    }

    tile.innerHTML = `
      ${lowTimeBadge}
      <h3><a href="${job.link}" target="_blank">${job.title}</a></h3>
      <p><strong>Company:</strong> ${job.company}</p>
      <p><strong>Source:</strong> ${job.source}</p>
      ${job.tags && job.tags.length > 0 ? `<p><strong>Tags:</strong> ${job.tags.join(", ")}</p>` : ""}
      ${job.hours_required ? `<p><strong>Hours Required:</strong> ${job.hours_required}</p>` : ""}
    `;

    container.appendChild(tile);
  });
}

function updateScraperStatus(results) {
  const statusTable = document.querySelector("#scraper-status tbody");
  statusTable.innerHTML = "";
  for (const [source, res] of Object.entries(results)) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${source}</td>
      <td class="${res.status === "success" ? "status-success" : "status-fail"}">
        ${res.status}
      </td>
      <td>${res.count}</td>
    `;
    statusTable.appendChild(row);
  }
}

// Filter button logic
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const filter = btn.dataset.filter;

    if (activeFilters.includes(filter)) {
      activeFilters = activeFilters.filter(f => f !== filter);
      btn.classList.remove("active");
    } else {
      activeFilters.push(filter);
      btn.classList.add("active");
    }

    loadJobs();
  });
});

// Light/Dark theme toggle
document.getElementById("theme-toggle").addEventListener("click", () => {
  document.body.classList.toggle("dark");
  document.querySelector("header").classList.toggle("dark");
});

// Load jobs on page load
loadJobs();
