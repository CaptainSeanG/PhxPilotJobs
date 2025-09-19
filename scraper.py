import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re
from urllib.parse import urlencode, quote_plus

# ---------- Config ----------
HISTORY_FILE = "jobs_history.json"
OUTPUT_HTML  = "index.html"
DAYS_TO_KEEP = 30

# Broad keyword set for aircraft/ops
KEYWORDS = [
    "caravan", "pc-12", "pc12", "pilatus", "cessna 208", "skycourier", "sky courier",
    "baron", "navajo"
]

# Tagging rules powering the filter chips
KEYWORD_TAGS = [
    {"label": "Caravan",     "pattern": re.compile(r"\bcaravan\b|\bcessna\s*208\b", re.I)},
    {"label": "PC-12",       "pattern": re.compile(r"\bpc[-\s]?12\b|\bpilatus\b", re.I)},
    {"label": "Part 91",     "pattern": re.compile(r"\bpart\s*91\b", re.I)},
    {"label": "SkyCourier",  "pattern": re.compile(r"\bsky\s*courier\b|\bskycourier\b", re.I)},
    {"label": "Baron",       "pattern": re.compile(r"\bbaron\b", re.I)},
    {"label": "Navajo",      "pattern": re.compile(r"\bnavajo\b", re.I)},
]

# ---------- ScraperAPI routing ----------
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def fetch_url(url, **kwargs):
    """
    Wrapper around requests.get that routes through ScraperAPI (if key present)
    to avoid 403 / JS walls on CI runners.
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

# ---------- Sites & query builders ----------
def indeed_url(q):         return f"https://www.indeed.com/jobs?q={quote_plus(q)}"
def zip_url(q):            return f"https://www.ziprecruiter.com/candidate/search?search={quote_plus(q)}"
def glassdoor_url(q):      return f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={quote_plus(q)}"
def pilotsglobal_url(q):   return f"https://pilotsglobal.com/jobs?keyword={quote_plus(q)}"
def jsfirm_url(q):         return f"https://www.jsfirm.com/jobs/search?keywords={quote_plus(q)}"
def climbto350_url(q):     return f"https://www.climbto350.com/jobs?keyword={quote_plus(q)}"

SITES = [
    {
        "name": "ZipRecruiter",
        "url_fn": zip_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "article.job_result, article.job_content",
            "title":   "a[aria-label], a.job_link, a[href*='/jobs/']",
            "company": "a.t_org_link, div.job_name a, div.job_name span"
        }
    },
    {
        "name": "PilotsGlobal",
        "url_fn": pilotsglobal_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "div.search-result, div.job-item, article",
            "title":   "a[href*='/job/']",
            "company": "div.company, span.company, a[href*='/company/']"
        }
    },
    {
        "name": "Indeed",
        "url_fn": indeed_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "div.job_seen_beacon, div.cardOutline, div.slider_container",
            "title":   "h2 a, a.jcs-JobTitle",
            "company": "span.companyName, span[data-testid='company-name']"
        }
    },
    {
        "name": "JSfirm",
        "url_fn": jsfirm_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "li.job-result, div.search-result",
            "title":   "a",
            "company": "span.company, div.company"
        }
    },
    {
        "name": "Climbto350",
        "url_fn": climbto350_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "li.job, div.job",
            "title":   "a",
            "company": "span.company, div.company"
        }
    },
    {
        "name": "Glassdoor",
        "url_fn": glassdoor_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "li.react-job-listing, li#MainCol div.jobCard",
            "title":   "a.jobLink, a.jobTitle",
            "company": "div.jobHeader a, div.jobInfoItem.jobEmpolyerName"
        }
    },
]

# ---------- Utilities ----------
def make_absolute(base_url, href):
    if not href:
        return base_url
    if href.startswith(("http://", "https://")):
        return href
    parts = base_url.split("/")
    origin = parts[0] + "//" + parts[2]
    if href.startswith("/"):
        return origin + href
    return base_url.rstrip("/") + "/" + href

def tag_job(title, company):
    tags = []
    blob = f"{title} {company}"
    for kt in KEYWORD_TAGS:
        if kt["pattern"].search(blob):
            tags.append(kt["label"])
    return tags

# ---------- Scraping ----------
def scrape_site_for_query(site, q):
    jobs = []
    url = site["url_fn"](q)
    try:
        resp = fetch_url(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, site["parser"])
        for card in soup.select(site["selectors"]["job"]):
            title_tag   = card.select_one(site["selectors"]["title"])
            company_tag = card.select_one(site["selectors"]["company"])
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href  = title_tag.get("href")
            link  = make_absolute(url, href)
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"
            if title:
                jobs.append({
                    "title": title,
                    "company": company,
                    "link": link,
                    "source": site["name"],
                    "tags": tag_job(title, company),
                    "_q": q,      # which keyword matched the search URL
                    "_url": url,  # which URL we used
                })
    except Exception as e:
        print(f"Error scraping {site['name']} ({q}): {e}")
    return jobs

def scrape_all_sites():
    all_jobs = []
    counts = {}  # per-site totals
    for site in SITES:
        site_total = 0
        for q in KEYWORDS:
            items = scrape_site_for_query(site, q)
            site_total += len(items)
            all_jobs.extend(items)
        counts[site["name"]] = site_total
        print(f"Scraped {site_total} jobs from {site['name']} across {len(KEYWORDS)} queries")
    # Deduplicate by (title, company, link) in case multiple queries hit same job
    dedup = {}
    for j in all_jobs:
        key = (j["title"].lower(), j["company"].lower(), j["link"])
        if key not in dedup:
            dedup[key] = j
        else:
            # merge tags
            prev = dedup[key]
            prev["tags"] = sorted(set(prev.get("tags", []) + j.get("tags", [])))
    return list(dedup.values()), counts

# ---------- History ----------
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

# ---------- HTML ----------
def generate_html(today_jobs, history, counts):
    now_str = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    html = """
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>Pilot Jobs – Aircraft Keywords</title>
      <style>
        :root { --bg:#0b1320; --card:#121a2b; --text:#e6eefc; --muted:#9ab0d1; --accent:#4da3ff; --accent2:#2ecc71; --link:#a9cbff; }
        [data-theme='light'] { --bg:#f5f7fb; --card:#ffffff; --text:#0b1320; --muted:#445974; --accent:#0b65d4; --accent2:#1a9e4d; --link:#0b65d4; }
        *{box-sizing:border-box}
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 0; background: var(--bg); color: var(--text); }
        .wrap { max-width: 960px; margin: 0 auto; padding: 24px; }
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
        .kw { font-size: 12px; color: var(--muted); margin-left: 8px; }
      </style>
    </head>
    <body>
      <div class="wrap" id="app" data-theme="dark">
        <div class="card">
          <h1>Low-Time Pilot Jobs — Keyword Focus</h1>
    """
    html += f"<p class='sub'>Updated {now_str}</p>"

    # Controls
    html += """
          <div class="controls">
            <input type="text" id="jobSearch" onkeyup="filterAll()" placeholder="Search (e.g., company, title, location)">
            <div class="toolbar">
              <button onclick="filterSource('all')" class="active" id="btnAll">All</button>
    """
    # dynamically add source buttons based on counts
    for name in counts.keys():
        html += f"<button onclick=\"filterSource('{name}')\">{name}</button>"
    html += """
              <button class="secondary" onclick="toggleTheme()" id="themeBtn">Light mode</button>
            </div>
            <div class="toolbar">
              <button onclick="toggleTag('Caravan')" id="tagCaravan">Caravan</button>
              <button onclick="toggleTag('PC-12')" id="tagPC12">PC-12</button>
              <button onclick="toggleTag('Part 91')" id="tagPart91">Part 91</button>
              <button onclick="toggleTag('SkyCourier')" id="tagSkyCourier">SkyCourier</button>
              <button onclick="toggleTag('Baron')" id="tagBaron">Baron</button>
              <button onclick="toggleTag('Navajo')" id="tagNavajo">Navajo</button>
            </div>
          </div>
          <p class="sub">Now searching *any location* for jobs mentioning: Caravan, PC-12/PC12, Pilatus, Cessna 208, SkyCourier, Baron, Navajo.</p>
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
                f"<span class='sourceTag'>({job['source']})</span>{tag_html}"
                f"</li>"
            )
    else:
        html += "<li>No new jobs found today.</li>"
    html += "</ul></div>"

    # History
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
                f"<span class='sourceTag'>({job['source']})</span>{tag_html}"
                f"</li>"
            )
        html += "</ul>"
    html += "</div>"

    # JS
    html += """
      </div>
      <script>
        // Theme toggle with persistence
        const app = document.getElementById('app');
        const themeBtn = document.getElementById('themeBtn');
        function applyTheme(t){ app.setAttribute('data-theme', t); themeBtn.textContent = (t==='dark'?'Light mode':'Dark mode'); localStorage.setItem('ppj-theme', t); }
        (function(){ const saved = localStorage.getItem('ppj-theme') || 'dark'; applyTheme(saved); })();
        function toggleTheme(){ const t = app.getAttribute('data-theme')==='dark'?'light':'dark'; applyTheme(t); }

        // Filters
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
          const idMap = { "Caravan":"tagCaravan", "PC-12":"tagPC12", "Part 91":"tagPart91", "SkyCourier":"tagSkyCourier", "Baron":"tagBaron", "Navajo":"tagNavajo" };
          const btn = document.getElementById(idMap[tag]);
          if(activeTags.has(tag)){ activeTags.delete(tag); btn.classList.remove('active'); }
          else { activeTags.add(tag); btn.classList.add('active'); }
          filterAll();
        }
        function filterAll() {
          const q = (document.getElementById('jobSearch').value || '').toLowerCase();
          const activeSrcBtn = document.querySelector('.toolbar button.active#btnAll, .toolbar button.active:not(#tagCaravan):not(#tagPC12):not(#tagPart91):not(#tagSkyCourier):not(#tagBaron):not(#tagNavajo)');
          const src = activeSrcBtn ? (activeSrcBtn.textContent === 'All' ? 'all' : activeSrcBtn.textContent) : 'all';
          document.querySelectorAll('li.job-item').forEach(li => {
            const text = li.textContent.toLowerCase();
            const liSrc = li.dataset.source;
            const tags = (li.dataset.tags || '').split('|').filter(Boolean);
            const byText   = !q || text.includes(q);
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

# ---------- Main ----------
def main():
    today_key = datetime.date.today().isoformat()
    history = load_history()

    jobs, counts = scrape_all_sites()

    # Replace today's jobs, keep prior days
    history[today_key] = jobs

    # Keep last 30 days only
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
