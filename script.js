let jobs = [];
let history = {};
let currentTag = "All";
let darkMode = false;
let viewingHistory = false;

async function loadJobs() {
  try {
    const res = await fetch("jobs.json");
    const data = await res.json();
    jobs = data.today;
    history = data.history;

    // Populate history dropdown
    const select = document.getElementById("historySelect");
    Object.keys(history).sort().reverse().forEach(date => {
      const option = document.createElement("option");
      option.value = date;
      option.textContent = date;
      select.appendChild(option);
    });

    renderJobs();
  } catch (e) {
    document.getElementById("jobs").innerHTML = "<p>Could not load jobs.</p>";
  }
}

function renderJobs() {
  const search = document.getElementById("search").value.toLowerCase();
  const container = document.getElementById("jobs");
  container.innerHTML = "";

  const filtered = jobs.filter(j => {
    const matchesTag = currentTag === "All" || (j.tags && j.tags.includes(currentTag));
    const matchesSearch = j.title.toLowerCase().includes(search) || j.company.toLowerCase().includes(search);
    return matchesTag && matchesSearch;
  });

  if (filtered.length === 0) {
    container.innerHTML = "<p>No jobs found.</p>";
    return;
  }

  filtered.forEach(j => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <h3><a href="${j.link}" target="_blank">${j.title}</a></h3>
      <p><strong>Company:</strong> ${j.company}</p>
      <p><strong>Source:</strong> ${j.source}</p>
      <p><strong>Tags:</strong> ${j.tags ? j.tags.join(", ") : "None"}</p>
    `;
    container.appendChild(card);
  });
}

function filterTag(tag) {
  currentTag = tag;
  renderJobs();
}

function toggleTheme() {
  darkMode = !darkMode;
  document.body.classList.toggle("dark", darkMode);
}

function selectHistoryDate() {
  const date = document.getElementById("historySelect").value;
  if (date && history[date]) {
    jobs = history[date];
    viewingHistory = true;
  } else {
    jobs = history.today || jobs;
    viewingHistory = false;
  }
  renderJobs();
}

function resetToToday() {
  document.getElementById("historySelect").value = "";
  jobs = history.today || jobs;
  viewingHistory = false;
  renderJobs();
}

loadJobs();
