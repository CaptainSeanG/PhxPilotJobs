import requests
from bs4 import BeautifulSoup
import datetime
import json
import os

# ---------- Config ----------
HISTORY_FILE = "jobs_history.json"
OUTPUT_HTML = "index.html"

# List of job sites to scrape
SITES = [
    {
        "name": "Indeed",
        "url": "https://www.indeed.com/jobs?q=pilot&l=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {"job": "div.job_seen_beacon", "title": "h2 a", "company": "span.companyName"}
    },
    {
        "name": "ZipRecruiter",
        "url": "https://www.ziprecruiter.com/candidate/search?search=pilot&location=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {"job": "article.job_result", "title": "a.job_link", "company": "a.t_org_link"}
    },
    {
        "name": "Glassdoor",
        "url": "https://www.glassdoor.com/Job/phoenix-pilot-jobs-SRCH_IL.0,7_IC1133904_KO8,13.htm",
        "parser": "html.parser",
        "selectors": {"job": "li.react-job-listing", "title": "a.jobLink", "company": "div.jobHeader a"}
    },
    {
        "name": "PilotCareerCenter",
        "url": "https://www.pilotcareercenter.com/Pilot-Job-Search?keyword=Phoenix&location=Arizona",
        "parser": "html.parser",
        "selectors": {"job": "div.job-item", "title": "h3 a", "company": "span.company"}
    }
]

# ---------- Scraper Functions ----------
def scrape_site(site):
    jobs = []
    try:
        resp = requests.get(site["url"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, site["parser"])
        for job in soup.select(site["selectors"]["job"]):
            title_tag = job.select_one(site["selectors"]["title"])
            company_tag = job.select_one(site["selectors"]["company"])
            if title_tag:
                title = title_tag.get_text(strip=True)
                link = title_tag.get("href")
                if link and not link.startswith("http"):
                    link = site["url"].split("/")[0] + "//" + site["url"].split("/")[2] + link
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                jobs.append({"title": title, "company": company, "link": link or site["url"], "source": site["name"]})
    except Exception as e:
        print(f"Error scraping {site['name']}: {e}")
    return jobs

def scrape_all_sites():
    all_jobs = []
    for site in SITES:
        jobs = scrape_site(site)
        print(f"Scraped {len(jobs)} jobs from {site['name']}")
        all_jobs.extend(jobs)
    return all_jobs

# ---------- History Handling ----------
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

# ---------- HTML Generation ----------
def generate_html(today_jobs, history):
    today = datetime.date.today().strftime("%B %d, %Y")
    html = """
    <html>
    <head>
      <title>Phoenix Pilot Jobs</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #2c3e50; }
        input[type='text'] {
          padding: 8px;
          width: 300px;
          margin-bottom: 20px;
          font-size: 16px;
        }
        button {
          padding: 6px 12px;
          margin: 4px;
          border: none;
          border-radius: 5px;
          cursor: pointer;
          background-color: #3498db;
          color: white;
          font-size: 14px;
        }
        button.active {
          background-color: #2ecc71;
        }
        li { margin-bottom: 6px; }
        .hidden { display: none; }
      </style>
    </head>
    <body>
    """
    html += f"<h1>Phoenix Low-Time Pilot Jobs</h1><p>Updated {today}</p>"

    # Search + filter controls
    html += """
    <input type="text" id="jobSearch" onkeyup="filterJobs()" placeholder="Search for jobs...">
    <div>
      <button onclick="filterSource('all')" class="active">All</button>
      <button onclick="filterSource('Indeed')">Indeed</button>
      <button onclick="filterSource('ZipRecruiter')">ZipRecruiter</button>
      <button onclick="filterSource('Glassdoor')">Glassdoor</button>
      <button onclick="filterSource('PilotCareerCenter')">PilotCareerCenter</button>
    </div>
    <script>
    function filterJobs() {
      let input = document.getElementById('jobSearch').value.toLowerCase();
      let items = document.querySelectorAll('li.job-item');
      items.forEach(li => {
        let text = li.textContent.toLowerCase();
        let matches = text.includes(input);
        li.style.display = matches ? '' : 'none';
      });
    }

    function filterSource(source) {
      let buttons = document.querySelectorAll('button');
      buttons.forEach(btn => btn.classList.remove('active'));
      event.target.classList.add('active');

      let items = document.querySelectorAll('li.job-item');
      items.forEach(li => {
        if (source === 'all' || li.dataset.source === source) {
          li.style.display = '';
        } else {
          li.style.display = 'none';
        }
      });
    }
    </script>
    """

    # Today's jobs
    html += "<h2>Today’s Jobs</h2><ul>"
    if today_jobs:
        for job in today_jobs:
            html += f"<li class='job-item' data-source='{job['source']}'><a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} ({job['source']})</li>"
    else:
        html += "<li>No new jobs found today.</li>"
    html += "</ul>"

    # History
    html += "<h2>Job History (Last 30 Days)</h2>"
    for day, jobs in sorted(history.items(), reverse=True):
        html += f"<h3>{day}</h3><ul>"
        for job in jobs:
            html += f"<li class='job-item' data-source='{job['source']}'><a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} ({job['source']})</li>"
        html += "</ul>"

    html += "</body></html>"
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

# ---------- Main ----------
def main():
    today = datetime.date.today().strftime("%Y-%m-%d")
    history = load_history()
    jobs = scrape_all_sites()

    # Save today’s jobs
    history[today] = jobs

    # Keep only last 30 days
    cutoff = datetime.date.today() - datetime.timedelta(days=30)
    history = {d: j for d, j in history.items() if datetime.date.fromisoformat(d) >= cutoff}

    save_history(history)
    generate_html(jobs, history)

if __name__ == "__main__":
    main()
