let jobsData = [];

function loadJobs() {
  fetch("jobs.json")
    .then(response => response.json())
    .then(data => {
      jobsData = data.today && data.today.length
        ? data.today
        : data.history[Object.keys(data.history).pop()];

      renderJobs(jobsData);
    })
    .catch(err => console.error("Error loading jobs:", err));
}

function renderJobs(jobs) {
  const container = document.getElementById("jobs");
  container.innerHTML = "";

  if (!jobs || jobs.length === 0) {
    container.innerHTML = "<p>No jobs available.</p>";
    return;
  }

  jobs.forEach(job => {
    const card = document.createElement("div");
    card.className = "job-card p-4 rounded-xl shadow-md bg-white dark:bg-gray-800";
    card.innerHTML = `
      <h3 class="font-bold text-lg mb-2">
        <a href="${job.link}" target="_blank" class="text-blue-600 dark:text-blue-400 hover:underline">
          ${job.title}
        </a>
      </h3>
      <p class="text-sm text-gray-700 dark:text-gray-300">${job.company || ""}</p>
      <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">Source: ${job.source}</p>
      <div class="flex flex-wrap gap-2">
        ${job.tags.map(tag => `<span class="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-xs rounded">${tag}</span>`).join("")}
      </div>
    `;
    container.appendChild(card);
  });
}

document.addEventListener("DOMContentLoaded", loadJobs);
