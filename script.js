let jobs = [];
let activeFilters = new Set();

async function loadJobs() {
  try {
    const res = await fetch("jobs.json");
    if (!res.ok) throw new Error("Failed to fetch jobs.json");
    const data = await res.json();
    console.log("Loaded jobs:", data);

    jobs = data.today || [];
    let lastUpdated = null;

    // Fallback to history if today is empty
    if (jobs.length === 0 && data.history) {
      const dates = Object.keys(data.history).sort().reverse();
      if (dates.length > 0) {
        const latest = dates[0];
        jobs = data.history[latest] || [];
        lastUpdated = latest + " (history)";
      }
    }

    // Show Arizona local time if today’s jobs exist
    if (!lastUpdated) {
      const now = new Date();
      const options = { timeZone: "America/Phoenix", hour12: false };
      const azTime = new Intl.DateTimeFormat("en-US", {
        ...options,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      }).format(now);

      lastUpdated = azTime + " (Arizona Time)";
    }

    document.getElementById("last-updated").innerText =
      "Last updated: " + lastUpdated;
    renderJobs();
  } catch (err) {
    console.error("Error loading jobs:", err);
    document.getElementById("jobs-container").innerHTML =
      "<p>Could not load jobs.</p>";
  }
}

function renderJobs() {
  const container = document.getElementById("jobs-container");
  const summary = document.getElementById("filter-summary");
  const search = document.getElementById("search").value.toLowerCase();
  container.innerHTML = "";

  // Update filter summary
  if (activeFilters.size > 0) {
    summary.innerText = "Active filters: " + [...activeFilters].join(", ");
  } else {
    summary.innerText = "No filters active";
  }

  const filtered = jobs.filter((j) => {
    const matchesFilters =
      activeFilters.size === 0 ||
      [...activeFilters].some(
        (tag) =>
          (j.tags && j.tags.includes(tag)) ||
          (tag === "Ameriflight" && j.company === "Ameriflight")
      );

    const matchesSearch =
      j.title.toLowerCase().includes(search) ||
      j.company.toLowerCase().includes(search);

    return matchesFilters && matchesSearch;
  });

  if (filtered.length === 0) {
    container.innerHTML = "<p>No jobs found.</p>";
    return;
  }

  filtered.forEach((j) => {
    const div = document.createElement("div");
    div.className = "job-card";
    div.innerHTML = `
      <h3><a href="${j.link}" target="_blank">${j.title}</a></h3>
      <p><strong>Company:</strong> ${j.company}</p>
      <p><strong>Source:</strong> ${j.source}</p>
      <p><strong>Tags:</strong> ${j.tags ? j.tags.join(", ") : "None"}</p>
    `;
    container.appendChild(div);
  });
}

function toggleFilter(tag) {
  const button = [...document.querySelectorAll(".controls button")].find(
    (btn) => btn.textContent === tag
  );

  if (activeFilters.has(tag)) {
    activeFilters.delete(tag);
    if (button) button.classList.remove("active");
  } else {
    activeFilters.add(tag);
    if (button) {
      button.classList.add("active");
      button.setAttribute("data-tag", tag);
    }
  }

  renderJobs();
}

function clearFilters() {
  activeFilters.clear();
  document
    .querySelectorAll(".controls button")
    .forEach((btn) => btn.classList.remove("active"));
  renderJobs();
}

loadJobs();
