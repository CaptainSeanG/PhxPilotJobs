import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
<<<<<<< HEAD
import re
=======
>>>>>>> 80b157e665428642c20487e7704cb91b96c48415

# ---------- Config ----------
HISTORY_FILE = "jobs_history.json"
OUTPUT_HTML = "index.html"
<<<<<<< HEAD
DAYS_TO_KEEP = 30

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115 Safari/537.36"}

# List of job sites to scrape (basic selectors; sites may change layouts)
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
        "selectors": {"job": "article.job_result, article.job_content", "title": "a.job_link, a", "company": "a.t_org_link, div.job_name a"}
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
        "selectors": {"job": "div.job-item, tr", "title": "h3 a, a", "company": "span.company, td:nth-child(2)"}
    },
    {
        "name": "JSfirm",
        "url": "https://www.jsfirm.com/pilot/phoenix-az",
        "parser": "html.parser",
        "selectors": {"job": "div.search-result, li.job-result", "title": "a", "company": "div.company, span.company"}
    },
    {
        "name": "Climbto350",
        "url": "https://www.climbto350.com/jobs?keyword=pilot&location=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {"job": "div.job, li.job", "title": "a", "company": "div.company, span.company"}
    }
]

KEYWORD_TAGS = [
    {"label": "Caravan", "pattern": re.compile(r"\bcaravan\b|\bcessna\s*208\b", re.I)},
    {"label": "PC-12", "pattern": re.compile(r"\bpc[-\s]?12\b|\bpilatus\b", re.I)},
    {"label": "Part 91", "pattern": re.compile(r"\bpart\s*91\b", re.I)},
]

def make_absolute(base_url, href):
    if not href:
        return base_url
    if href.startswith("http://") or href.startswith("https://"):
        return href
    parts = base_url.split("/")
    origin = parts[0] + "//" + parts[2]
    if href.startswith("/"):
        return origin + href
    return base_url.rstrip("/") + "/" + href

def scrape_site(site):
    jobs = []
    try:
        resp = requests.get(site["url"], timeout=20, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, site["parser"])
        for job in soup.select(site["selectors"]["job"]):
            title_tag = job.select_one(site["selectors"]["title"])
            company_tag = job.select_one(site["selectors"]["company"])
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get("href")
            link = make_absolute(site["url"], href)
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"
            if title:
                tags = []
                text_blob = f"{title} {company}"
                for kt in KEYWORD_TAGS:
                    if kt["pattern"].search(text_blob):
                        tags.append(kt["label"])
                jobs.append({"title": title, "company": company, "link": link, "source": site["name"], "tags": tags})
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

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def generate_html(today_jobs, history):
    now_str = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    html = """
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>Phoenix Pilot Jobs</title>
      <style>
        :root {
          --bg:#0b1320; --card:#121a2b; --text:#e6eefc; --muted:#9ab0d1; --accent:#4da3ff; --accent2:#2ecc71; --link:#a9cbff;
        }
        [data-theme='light'] {
          --bg:#f5f7fb; --card:#ffffff; --text:#0b1320; --muted:#445974; --accent:#0b65d4; --accent2:#1a9e4d; --link:#0b65d4;
        }
        *{box-sizing:border-box}
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 0; background: var(--bg); color: var(--text); }
        .wrap { max-width: 920px; margin: 0 auto; padding: 24px; }
        .card { background: var(--card); border-radius: 14px; box-shadow: 0 6px 18px rgba(0,0,0,0.15); padding: 18px 20px; margin-bottom: 18px; }
        h1 { margin: 6px 0 8px; font-size: 28px; }
        .sub { color: var(--muted); margin: 0 0 18px; }
        .controls { display:flex; flex-wrap:wrap; gap:8px; margin: 12px 0 16px; align-items:center; }
        input[type='text'] {
          padding: 10px 12px; flex: 1 1 260px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.1); background: transparent; color: var(--text); outline: none;
        }
        button {
          padding: 8px 12px; border: 0; border-radius: 10px; background: var(--accent); color: #fff; cursor: pointer;
        }
        button.secondary { background: #6b7280; }
        button.active { background: var(--accent2); }
        ul { list-style: none; padding: 0; margin: 8px 0; }
        li { margin: 6px 0; padding: 10px 12px; background: color-mix(in srgb, var(--card) 94%, var(--text) 6%); border-radius: 10px; }
        a { color: var(--link); text-decoration: none; }
        a:hover { text-decoration: underline; }
        h2 { margin: 14px 0 6px; font-size: 20px; }
        h3 { margin: 12px 0 6px; font-size: 16px; color: var(--muted); }
        .sourceTag { font-size: 12px; color: var(--muted); margin-left: 6px; }
        .tag { font-size: 12px; padding:2px 6px; border-radius:8px; margin-left:6px; background: color-mix(in srgb, var(--accent) 30%, transparent); color:#fff; }
        .toolbar { display:flex; gap:8px; flex-wrap:wrap; }
      </style>
    </head>
    <body>
      <div class="wrap" id="app" data-theme="dark">
        <div class="card">
          <h1>Phoenix Low‑Time Pilot Jobs</h1>
          <p class="sub">Updated """ + now_str + """</p>
          <div class="controls">
            <input type="text" id="jobSearch" onkeyup="filterAll()" placeholder="Search (e.g., Caravan, PC‑12, cargo, Part 91)">
            <div class="toolbar">
              <button onclick="filterSource('all')" class="active" id="btnAll">All</button>
              <button onclick="filterSource('Indeed')">Indeed</button>
              <button onclick="filterSource('ZipRecruiter')">ZipRecruiter</button>
              <button onclick="filterSource('Glassdoor')">Glassdoor</button>
              <button onclick="filterSource('PilotCareerCenter')">PilotCareerCenter</button>
              <button onclick="filterSource('JSfirm')">JSfirm</button>
              <button onclick="filterSource('Climbto350')">Climbto350</button>
              <button class="secondary" onclick="toggleTheme()" id="themeBtn">Light mode</button>
            </div>
            <div class="toolbar">
              <button onclick="toggleTag('Caravan')" id="tagCaravan">Caravan</button>
              <button onclick="toggleTag('PC-12')" id="tagPC12">PC‑12</button>
              <button onclick="toggleTag('Part 91')" id="tagPart91">Part 91</button>
            </div>
          </div>
          <p class="sub">Type in the search box to filter by text. Use the top row to filter by source. Use the second row to filter by <em>aircraft/ops tags</em>.</p>
        </div>
    """

    # Today's jobs
    html += """
        <div class="card">
          <h2>Today’s Jobs</h2>
          <ul id="todayList">
    """
    if today_jobs:
        for job in today_jobs:
            tag_span = "".join([f"<span class='tag'>{t}</span>" for t in (job.get("tags") or [])])
            html += f"<li class='job-item' data-source='{job['source']}' data-tags='{'|'.join(job.get('tags', []))}'><a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} <span class='sourceTag'>({job['source']})</span>{tag_span}</li>"
    else:
        html += "<li>No new jobs found today.</li>"
    html += """
          </ul>
        </div>
    """

    # History with counts
    html += """
        <div class="card">
          <h2>Job History (Last 30 Days)</h2>
    """
    for day, jobs in sorted(history.items(), reverse=True):
        count = len(jobs)
        html += f"<h3>{day} — {count} job{'s' if count != 1 else ''}</h3><ul>"
        for job in jobs:
            tag_span = "".join([f"<span class='tag'>{t}</span>" for t in (job.get('tags') or [])])
            html += f"<li class='job-item' data-source='{job['source']}' data-tags='{'|'.join(job.get('tags', []))}'><a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} <span class='sourceTag'>({job['source']})</span>{tag_span}</li>"
        html += "</ul>"
    html += """
        </div>
      </div>

      <script>
        // Theme toggle with localStorage
        const app = document.getElementById('app');
        const themeBtn = document.getElementById('themeBtn');
        function applyTheme(t){ app.setAttribute('data-theme', t); themeBtn.textContent = (t==='dark'?'Light mode':'Dark mode'); localStorage.setItem('ppj-theme', t); }
        (function(){ const saved = localStorage.getItem('ppj-theme') || 'dark'; applyTheme(saved); })();
        function toggleTheme(){ const t = app.getAttribute('data-theme')==='dark'?'light':'dark'; applyTheme(t); }

        // Active source filter
        function filterSource(source) {
          const buttons = Array.from(document.querySelectorAll('.toolbar button')).filter(b=>!b.classList.contains('secondary'));
          buttons.forEach(btn => { if(btn.id!=='tagCaravan' && btn.id!=='tagPC12' && btn.id!=='tagPart91') btn.classList.remove('active'); });
          const match = buttons.find(b => b.textContent === source || (source==='all' && b.id==='btnAll'));
          if (match) match.classList.add('active');
          filterAll();
        }

        // Tag filters
        const activeTags = new Set();
        function toggleTag(tag){
          const id = tag==='Caravan'?'tagCaravan':(tag==='PC-12'?'tagPC12':'tagPart91');
          const btn = document.getElementById(id);
          if(activeTags.has(tag)){ activeTags.delete(tag); btn.classList.remove('active'); }
          else { activeTags.add(tag); btn.classList.add('active'); }
          filterAll();
        }

        function filterAll() {
          const q = (document.getElementById('jobSearch').value || '').toLowerCase();
          const activeBtn = document.querySelector('.toolbar button.active#btnAll, .toolbar button.active:not(#tagCaravan):not(#tagPC12):not(#tagPart91)');
          const source = activeBtn ? (activeBtn.textContent==='All'?'all':activeBtn.textContent) : 'all';

          const items = document.querySelectorAll('li.job-item');
          items.forEach(li => {
            const text = li.textContent.toLowerCase();
            const liSource = li.dataset.source;
            const tags = (li.dataset.tags || '').split('|').filter(Boolean);

            const byText = !q or text.includes(q);
            const bySource = (source==='all') or (liSource===source);

            let byTags = true;
            if(activeTags.size>0){
              byTags = [...activeTags].every(t => tags.includes(t));
            }

            li.style.display = (byText && bySource && byTags) ? '' : 'none';
          });
        }
      </script>
    </body>
    </html>
    """
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

def main():
    today_key = datetime.date.today().isoformat()
    # Load & scrape
    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = {}

    jobs = []
    for site in SITES:
        try:
            resp = requests.get(site["url"], timeout=20, headers=HEADERS)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, site["parser"])
            for job in soup.select(site["selectors"]["job"]):
                title_tag = job.select_one(site["selectors"]["title"])
                company_tag = job.select_one(site["selectors"]["company"])
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                href = title_tag.get("href")
                link = make_absolute(site["url"], href)
                company = company_tag.get_text(strip=True) if company_tag else "Unknown"
                if title:
                    tags = []
                    text_blob = f"{title} {company}"
                    for kt in KEYWORD_TAGS:
                        if kt["pattern"].search(text_blob):
                            tags.append(kt["label"])
                    jobs.append({"title": title, "company": company, "link": link, "source": site["name"], "tags": tags})
        except Exception as e:
            print(f"Error scraping {site['name']}: {e}")

    # Save/trim history
    history[today_key] = jobs
    cutoff = datetime.date.today() - datetime.timedelta(days=DAYS_TO_KEEP)
    trimmed = {}
    for day, entries in history.items():
        try:
            if datetime.date.fromisoformat(day) >= cutoff:
                trimmed[day] = entries
        except Exception:
            pass
    history = trimmed

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

=======

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
>>>>>>> 80b157e665428642c20487e7704cb91b96c48415
    generate_html(jobs, history)

if __name__ == "__main__":
    main()
