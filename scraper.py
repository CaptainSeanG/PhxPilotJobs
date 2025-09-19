import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re
from urllib.parse import urlencode

# ---------- Config ----------
HISTORY_FILE = "jobs_history.json"
OUTPUT_HTML  = "index.html"
DAYS_TO_KEEP = 30

# Read ScraperAPI key from environment (set in GitHub Secrets)
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def fetch_url(url, **kwargs):
    """
    Wrapper around requests.get that routes through ScraperAPI if a key is present,
    avoiding 403/JS-walled pages on GitHub Actions.
    """
    headers = kwargs.pop("headers", {})
    headers.setdefault(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    headers.setdefault("Accept-Language", "en-US,en;q=0.9")
    timeout = kwargs.pop("timeout", 25)

    if SCRAPER_API_KEY:
        proxy_url = "http://api.scraperapi.com/"
        params = {
            "api_key": SCRAPER_API_KEY,
            "url": url,
            "render": "true",
            "country_code": "us",
            "keep_headers": "true",
        }
        proxied = proxy_url + "?" + urlencode(params)
        return requests.get(proxied, headers=headers, timeout=timeout, **kwargs)
    else:
        return requests.get(url, headers=headers, timeout=timeout, **kwargs)

# Sites to scrape (best-effort HTML selectors; sites may change layouts)
SITES = [
    {
        "name": "ZipRecruiter",
        "url": "https://www.ziprecruiter.com/candidate/search?search=pilot&location=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {
            "job":    "article.job_result, article.job_content",
            "title":  "a[aria-label], a.job_link, a[href*='/jobs/']",
            "company":"a.t_org_link, div.job_name a, div.job_name span"
        }
    },
    {
        "name": "PilotsGlobal",
        "url": "https://pilotsglobal.com/jobs?keyword=pilot&location=phoenix",
        "parser": "html.parser",
        "selectors": {
            "job":    "div.search-result, div.job-item, article",
            "title":  "a[href*='/job/']",
            "company":"div.company, span.company, a[href*='/company/']"
        }
    },
    # The following are kept as best-effort scrapes; many are JS/anti-bot heavy:
    {
        "name": "Indeed",
        "url": "https://www.indeed.com/jobs?q=pilot&l=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {
            "job":    "div.job_seen_beacon, div.cardOutline, div.slider_container",
            "title":  "h2 a, a.jcs-JobTitle",
            "company":"span.companyName, span[data-testid='company-name']"
        }
    },
    {
        "name": "JSfirm",
        "url": "https://www.jsfirm.com/pilot/phoenix-az",
        "parser": "html.parser",
        "selectors": {
            "job":    "li.job-result, div.search-result",
            "title":  "a",
            "company":"span.company, div.company"
        }
    },
    {
        "name": "Climbto350",
        "url": "https://www.climbto350.com/jobs?keyword=pilot&location=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {
            "job":    "li.job, div.job",
            "title":  "a",
            "company":"span.company, div.company"
        }
    },
    {
        "name": "Glassdoor",
        "url": "https://www.glassdoor.com/Job/phoenix-pilot-jobs-SRCH_IL.0,7_IC1133904_KO8,13.htm",
        "parser": "html.parser",
        "selectors": {
            "job":    "li.react-job-listing",
            "title":  "a.jobLink",
            "company":"div.jobHeader a"
        }
    },
]

# Tagging rules for fast filter buttons
KEYWORD_TAGS = [
    {"label": "Caravan", "pattern": re.compile(r"\bcaravan\b|\bcessna\s*208\b", re.I)},
    {"label": "PC-12",   "pattern": re.compile(r"\bpc[-\s]?12\b|\bpilatus\b", re.I)},
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
        resp = fetch_url(site["url"])
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, site["parser"])
        for job in soup.select(site["selectors"]["job"]):
            title_tag   = job.select_one(site["selectors"]["title"])
            company_tag = job.select_one(site["selectors"]["company"])
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href  = title_tag.get("href")
            link  = make_absolute(site["url"], href)
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"
            if title:
                # Tagging
                tags = []
                blob = f"{title} {company}"
                for kt in KEYWORD_TAGS:
                    if kt["pattern"].search(blob):
                        tags.append(kt["label"])
                jobs.append({
                    "title": title,
                    "company": company,
                    "link": link,
                    "source": site["name"],
                    "tags": tags
                })
    except Exception as e:
        print(f"Error scraping {site['name']}: {e}")
    return jobs

def scrape_all_sites():
    all_jobs = []
    counts = {}
    for site in SITES:
        items = scrape_site(site)
        counts[site["name"]] = len(items)
        print(f"Scraped {len(items)} jobs from {site['name']}")
        all_jobs.extend(items)
    return all_jobs, counts

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

def generate_html(today_jobs, history, counts):
    now_str = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    html = """
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>Phoenix Pilot Jobs</title>
      <style>
        :root { --bg:#0b1320; --card:#121a2b; --text:#e6eefc; --muted:#9ab0d1; --accent:#4da3ff; --accent2:#2ecc71; --link:#a9cbff; }
        [data-theme='light'] { --bg:#f5f7fb; --card:#ffffff; --text:#0b1320; --muted:#445974; --accent:#0b65d4; --accent2:#1a9e4d; --link:#0b65d4; }
        *{box-sizing:border-box}
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 0; background: var(--bg); color: var(--text); }
        .wrap { max-width: 920px; margin: 0 auto; padding: 24px; }
        .card { background: var(--card); border-radius: 14px; box-shadow: 0 6px 18px rgba(0,0,0,0.15); padding: 18px 20px; margin-bottom: 18px; }
        h1 { margin: 6px 0 8px; font-size: 28px; }
        .sub { color: var(--muted); margin: 0 0 18px; }
        .controls { display:flex; flex-wrap:wrap; gap:8px; margin: 12px 0 16px; align-items:center; }
        input[type='text'] { padding: 10px 12px; flex: 1 1 260px; border-radius: 10px; border: 1px solid rgba(0,0,0,0.1); background: transparent; color: var(--text); outline: none; }
        button { padding: 8px 12px; border: 0; border-radius: 10px; background: var(--accent); color: #fff; cursor: pointer; }
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
        .debug { font-size: 13px; color: var(--muted); }
      </style>
    </head>
    <body>
      <div class="wrap" id="app" data-theme="dark">
        <div class="card">
          <h1>Phoenix Low-Time Pilot Jobs</h1>
    """
    html += f"<p class='sub'>Updated {now_str}</p>"

    # Controls (search + source buttons + theme + tag filters)
    html += """
          <div class="controls">
            <input type="text" id="jobSearch" onkeyup="filterAll()" placeholder="Search (e.g., Caravan, PC-12, cargo, Part 91)">
            <div class="toolbar">
              <button onclick="filterSource('all')" class="active" id="btnAll">All</button>
              <button onclick="filterSource('ZipRecruiter')">ZipRecruiter</button>
              <button onclick="filterSource('PilotsGlobal')">PilotsGlobal</button>
              <button onclick="filterSource('Indeed')">Indeed</button>
              <button onclick="filterSource('JSfirm')">JSfirm</button>
              <button onclick="filterSource('Climbto350')">Climbto350</button>
              <button onclick="filterSource('Glassdoor')">Glassdoor</button>
              <button class="secondary" onclick="toggleTheme()" id="themeBtn">Light mode</button>
            </div>
            <div class="toolbar">
              <button onclick="toggleTag('Caravan')" id="tagCaravan">Caravan</button>
              <button onclick="toggleTag('PC-12')" id="tagPC12">PC-12</button>
              <button onclick="toggleTag('Part 91')" id="tagPart91">Part 91</button>
            </div>
          </div>
          <p class="sub">Tip: Filter by source (top row) or by tags (Caravan / PC-12 / Part 91). Search filters everything.</p>
    """

    # Debug counts
    html += "<div class='debug'><strong>Per-source counts this run:</strong> "
    html += " • ".join([f"{name}: {count}" for name, count in counts.items()])
    html += "</div></div>"

    # Today's jobs
    html += """
        <div class="card">
          <h2>Today’s Jobs</h2>
          <ul id="todayList">
    """
    if today_jobs:
        for job in today_jobs:
            tags = job.get("tags") or []
            tag_html = "".join([f"<span class='tag'>{t}</span>" for t in tags])
            html += (
              f"<li class='job-item' data-source='{job['source']}' data-tags='{'|'.join(tags)}'>"
              f"<a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} "
              f"<span class='sourceTag'>({job['source']})</span>{tag_html}</li>"
            )
    else:
        html += "<li>No new jobs found today.</li>"
    html += "</ul></div>"

    # 30-day history with day counts
    html += "<div class='card'><h2>Job History (Last 30 Days)</h2>"
    for day, jobs in sorted(history.items(), reverse=True):
        count = len(jobs)
        html += f"<h3>{day} — {count} job{'s' if count != 1 else ''}</h3><ul>"
        for job in jobs:
            tags = job.get("tags") or []
            tag_html = "".join([f"<span class='tag'>{t}</span>" for t in tags])
            html += (
              f"<li class='job-item' data-source='{job['source']}' data-tags='{'|'.join(tags)}'>"
              f"<a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} "
              f"<span class='sourceTag'>({job['source']})</span>{tag_html}</li>"
            )
        html += "</ul>"
    html += "</div>"

    # Client-side filtering + theme toggle
    html += """
      </div>
      <script>
        // Theme toggle with persistence
        const app = document.getElementById('app');
        const themeBtn = document.getElementById('themeBtn');
        function applyTheme(t){ app.setAttribute('data-theme', t); themeBtn.textContent = (t==='dark'?'Light mode':'Dark mode'); localStorage.setItem('ppj-theme', t); }
        (function(){ const saved = localStorage.getItem('ppj-theme') || 'dark'; applyTheme(saved); })();
        function toggleTheme(){ const t = app.getAttribute('data-theme')==='dark'?'light':'dark'; applyTheme(t); }

        // Source + Tag + Text filters
        const activeTags = new Set();

        function filterSource(source) {
          const srcButtons = Array.from(document.querySelectorAll('.toolbar button'))
            .filter(b => !b.classList.contains('secondary') && !b.id.startsWith('tag'));
          srcButtons.forEach(b => b.classList.remove('active'));
          const match = srcButtons.find(b => b.textContent === source || (source==='all' && b.id==='btnAll'));
          if (match) match.classList.add('active');
          filterAll();
        }

        function toggleTag(tag){
          const id = tag==='Caravan'?'tagCaravan':(tag==='PC-12'?'tagPC12':'tagPart91');
          const btn = document.getElementById(id);
          if(activeTags.has(tag)){ activeTags.delete(tag); btn.classList.remove('active'); }
          else { activeTags.add(tag); btn.classList.add('active'); }
          filterAll();
        }

        function filterAll() {
          const q = (document.getElementById('jobSearch').value || '').toLowerCase();
          const activeSrcBtn = document.querySelector('.toolbar button.active#btnAll, .toolbar button.active:not(#tagCaravan):not(#tagPC12):not(#tagPart91)');
          const src = activeSrcBtn ? (activeSrcBtn.textContent === 'All' ? 'all' : activeSrcBtn.textContent) : 'all';

          document.querySelectorAll('li.job-item').forEach(li => {
            const text = li.textContent.toLowerCase();
            const liSrc = li.dataset.source;
            const tags = (li.dataset.tags || '').split('|').filter(Boolean);

            const byText = !q || text.includes(q);
            const bySource = (src==='all') || (liSrc===src);
            let byTags = true;
            if(activeTags.size>0){ byTags = [...activeTags].every(t => tags.includes(t)); }

            li.style.display = (byText && bySource && byTags) ? '' : 'none';
          });
        }
      </script>
    </body></html>
    """
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

def main():
    today_key = datetime.date.today().isoformat()
    history = load_history()

    jobs, counts = scrape_all_sites()

    # Replace today's jobs
    history[today_key] = jobs

    # Keep last N days
    cutoff = datetime.date.today() - datetime.timedelta(days=DAYS_TO_KEEP)
    trimmed = {}
    for day, entries in history.items():
        try:
            if datetime.date.fromisoformat(day) >= cutoff:
                trimmed[day] = entries
        except Exception:
            pass
    history = trimmed

    save_history(history)
    generate_html(jobs, history, counts)

if __name__ == "__main__":
    main()
