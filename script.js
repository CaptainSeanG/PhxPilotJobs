let jobs = [];
let currentTag = "All";

async function loadJobs() {
  try {
    const res = await fetch("jobs.json");
    if (!res.ok) throw new Error("Failed to fetch jobs.json");
    const data = await res.json();
    console.log("Loaded jobs:", data);

    jobs = data.today || [];
    let lastUpdated = null;

    if (jobs.length === 0 && data.history) {
      const dates = Object.keys(data.history).sort().reverse();
      if (dates.length > 0) {
        const latest = dates[0];
        jobs = data.history[latest] || [];
        lastUpdated = latest + " (history)";
        console.log("Using fallback jobs from history date:", latest);
      }
    }

    if (!lastUpdated) {
      const now = new Date();
      lastUpdated = now.toISOString().replace("T", " ").substring(0, 16) + " UTC";
    }

    document.getElementById("last-updated").innerText = "Last updated: " + lastUpdated;
    renderJobs();
  } catch (err) {
    console.error("Error loading jobs:", err);
    document.getElementById("jobs-container").innerHTML = "<p>Could not load jobs.</p>";
  }
}

function renderJobs() {
  const container = document.getElementById("jobs-container");
  const search = document.getElementById("search").value.toLowerCase();
  container.innerHTML = "";

  const filtered = jobs.filter(j => {
    const matchesTag =
      currentTag === "All" ||
      (j.tags && j.tags.includes(currentTag)) ||
      (currentTag === "Ameriflight" && j.company === "Ameriflight");
    const matchesSearch =
      j.title.toLowerCase().includes(search) || j.company.toLowerCase().includes(search);
    return matchesTag && matchesSearch;
  });

  if (filtered.length === 0) {
    container.innerHTML = "<p>No jobs found.</p>";
    return;
  }

  filtered.forEach(j => {
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

function filterTag(tag) {
  currentTag = tag;
  renderJobs();
}

loadJobs();
