async function loadJobs() {
  try {
    const response = await fetch("jobs.json");
    const data = await response.json();

    const jobs = data.today || [];
    const history = data.history || {};
    const results = data.results || {};

    console.log("Jobs loaded:", jobs.length);
    console.log("Scraper results:", results);

    const container = document.getElementById("jobs-container");
    container.innerHTML = "";

    jobs.forEach(job => {
      const tile = document.createElement("div");
      tile.className = "job-tile";
      tile.innerHTML = `
        <h3><a href="${job.link}" target="_blank">${job.title}</a></h3>
        <p>${job.company}</p>
        <p><strong>Source:</strong> ${job.source}</p>
      `;
      container.appendChild(tile);
    });

    // Update last updated timestamp (local AZ time)
    const updatedEl = document.getElementById("last-updated");
    const now = new Date();
    updatedEl.textContent = "Updated: " + now.toLocaleString("en-US", { timeZone: "America/Phoenix" });

    // Fill scraper status
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
  } catch (err) {
    console.error("Error loading jobs.json", err);
  }
}

// Light/Dark theme toggle
document.getElementById("theme-toggle").addEventListener("click", () => {
  document.body.classList.toggle("dark");
  document.querySelector("header").classList.toggle("dark");
});

// Load jobs on page load
loadJobs();
