import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re
from urllib.parse import urlencode, quote_plus, urlsplit, urlunsplit

# ---------- Config ----------
HISTORY_FILE = "jobs_history.json"
OUTPUT_HTML  = "index.html"
OUTPUT_JSON  = "jobs_today.json"      # today's deduped jobs
OUTPUT_DIAG  = "scrape_report.json"   # detailed scrape report
DAYS_TO_KEEP = 30

# Broadened keywords: include general "pilot" sweep (AZ-limited via URL or post-filter)
KEYWORDS = [
    "pilot",  # broad sweep to catch titles like "Commercial Pilot"
    "caravan", "pc-12", "pc12", "pilatus",
    "cessna 208", "sky courier", "skycourier",
    "baron", "navajo"
]

# Tagging rules for quick filters
KEYWORD_TAGS = [
    {"label": "Caravan",     "pattern": re.compile(r"\bcaravan\b|\bcessna\s*208\b", re.I)},
    {"label": "PC-12",       "pattern": re.compile(r"\bpc[-\s]?12\b|\bpilatus\b", re.I)},
    {"label": "Part 91",     "pattern": re.compile(r"\bpart\s*91\b", re.I)},
    {"label": "SkyCourier",  "pattern": re.compile(r"\bsky\s*courier\b|\bskycourier\b", re.I)},
    {"label": "Baron",       "pattern": re.compile(r"\bbaron\b", re.I)},
    {"label": "Navajo",      "pattern": re.compile(r"\bnavajo\b", re.I)},
]

# Arizona terms (used for secondary location filter)
AZ_TERMS = {
    "az", "arizona",
    "phoenix", "scottsdale", "mesa", "chandler", "tempe", "glendale", "peoria",
    "gilbert", "surprise", "goodyear", "buckeye", "avondale",
    "tucson", "flagstaff", "prescott", "yuma", "sedona",
    "sierra vista", "queen creek", "casa grande", "maricopa",
    "lake havasu", "kingman", "payson", "show low"
}

def is_arizona(text: str) -> bool:
    """True if text mentions Arizona ('AZ', 'Arizona', or a known AZ city)."""
    t = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    if " arizona " in t or re.search(r"\baz\b", t):
        return True
    for city in AZ_TERMS:
        if f" {city} " in t:
            return True
    return False

# ---------- ScraperAPI routing ----------
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def fetch_url(url, **kwargs):
    """requests.get wrapper that uses ScraperAPI (if key present) to avoid 403/JS walls."""
    headers = kwargs.pop("headers", {})
    headers.setdefault(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    headers.setdefault("Accept-Language", "en-US,en;q=0.9")
    timeout = kwargs.pop("timeout", 30)

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

# ---------- Site URL builders (Arizona-scoped) ----------
def indeed_url(q):       return f"https://www.indeed.com/jobs?q={quote_plus(q)}&l=Arizona"
def zip_url(q):          return f"https://www.ziprecruiter.com/candidate/search?search={quote_plus(q)}&location=Arizona"
def glassdoor_url(q):    return f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={quote_plus(q + ' Arizona')}"
def pilotsglobal_url(q): return f"https://pilotsglobal.com/jobs?keyword={quote_plus(q)}&location=arizona"
def jsfirm_url(q):       return f"https://www.jsfirm.com/jobs/search?keywords={quote_plus(q + ' Arizona')}"
def climbto350_url(q):   return f"https://www.climbto350.com/jobs?keyword={quote_plus(q)}&location=Arizona"

SITES = [
    {
        "name": "ZipRecruiter",
        "url_fn": zip_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "article.job_result, article.job_content",
            "title":   "a[aria-label], a.job_link, a[href*='/jobs/']",
            "company": "a.t_org_link, div.job_name a, div.job_name span",
            "location":"div.location, span.location, div.job_location, span.job_location"
        }
    },
    {
        "name": "PilotsGlobal",
        "url_fn": pilotsglobal_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "div.search-result, div.job-item, article",
            "title":   "a[href*='/job/']",
            "company": "div.company, span.company, a[href*='/company/']",
            "location":"div.location, span.location, div.job-location"
        }
    },
    {
        "name": "Indeed",
        "url_fn": indeed_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "div.job_seen_beacon, div.cardOutline, div.slider_container",
            "title":   "h2 a, a.jcs-JobTitle",
            "company": "span.companyName, span[data-testid='company-name']",
            "location":"div.companyLocation, span.companyLocation"
        }
    },
    {
        "name": "JSfirm",
        "url_fn": jsfirm_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "li.job-result, div.search-result",
            "title":   "a",
            "company": "span.company, div.company",
            "location":"span.location, div.location"
        }
    },
    {
        "name": "Climbto350",
        "url_fn": climbto350_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "li.job, div.job",
            "title":   "a",
            "company": "span.company, div.company",
            "location":"span.location, div.location"
        }
    },
    {
        # Loosened selectors for Glassdoor list variants
        "name": "Glassdoor",
        "url_fn": glassdoor_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "li.react-job-listing, li#MainCol div.jobCard, div.JobCard_jobCardContainer__*, article.job-card",
            "title":   "a.jobLink, a.jobTitle, a[data-test='job-link']",
            "company": "div.jobHeader a, div.jobInfoItem.jobEmpolyerName, span[data-test='employerName'], a.EmployerProfile",
            "location":"span.pr-xxsm, span.css-56kyx5, div.location, span[data-test='emp-location']"
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

def norm_text(s):
    """Normalize title/company for de-dup (lowercase, strip punctuation/extra spaces)."""
    s = (s or "").lower()
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"[^\w\s&]", " ", s)
    s = re.sub(r"\b(inc|llc|l\.l\.c|co|corp|corporation|company)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def norm_link(url):
    """Normalize link to scheme-less host+path (drop query/fragment) for de-dup."""
    try:
        parts = urlsplit(url)
        path = parts.path or "/"
        cleaned = urlunsplit(("", parts.netloc.lower(), path, "", ""))
        return cleaned
    except Exception:
        return url

def tag_job(title, company):
    tags = []
    blob = f"{title} {company}"
    for kt in KEYWORD_TAGS:
        if kt["pattern"].search(blob):
            tags.append(kt["label"])
    return tags

# ---------- Scraping (with diagnostics) ----------
def scrape_site_for_query(site, q):
    jobs = []
    url = site["url_fn"](q)
    diag = {"query": q, "url": url, "status": None, "items": 0, "error": None, "blocked_hint": False}
    try:
        resp = fetch_url(url)
        diag["status"] = getattr(resp, "status_code", None)
        resp.raise_for_status()
        html_lower = resp.text.lower()
        # crude “blocked”/captcha heuristic
        if "captcha" in html_lower or "are you a human" in html_lower or "enable javascript" in html_lower:
            diag["blocked_hint"] = True

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

            # Try location fields; fall back to entire card text
            loc_text = ""
            for loc_sel in site["selectors"].get("location", "").split(","):
                sel = loc_sel.strip()
                if not sel:
                    continue
                loc_tag = card.select_one(sel)
                if loc_tag:
                    loc_text = loc_tag.get_text(" ", strip=True)
                    break
            card_text = card.get_text(" ", strip=True)

            # AZ filter: require location or card text to indicate Arizona
            if not (is_arizona(loc_text) or is_arizona(card_text)):
                continue

            # Tags from title/company
            tags = tag_job(title, company)
            # If this is the broad "pilot" query and no aircraft tags matched, mark as General
            if q.strip().lower() == "pilot" and not tags:
                tags = ["General"]

            jobs.append({
                "title": title,
                "company": company,
                "link": link,
                "source": site["name"],
                "tags": tags,
                "_loc": loc_text
            })
        diag["items"] = len(jobs)
    except Exception as e:
        diag["error"] = str(e)
        print(f"Error scraping {site['name']} ({q}): {e}")
    return jobs, diag

def scrape_all_sites():
    all_jobs = []
    counts = {}    # per-site totals (after AZ filter)
    diag_all = {}  # per-site detailed diagnostics

    for site in SITES:
        site_total = 0
        site_diags = []
        for q in KEYWORDS:
            items, diag = scrape_site_for_query(site, q)
            site_total += len(items)
            all_jobs.extend(items)
            site_diags.append(diag)
        counts[site["name"]] = site_total
        diag_all[site["name"]] = {
            "total": site_total,
            "queries": site_diags
        }
        print(f"Scraped {site_total} AZ-filtered jobs from {site['name']} across {len(KEYWORDS)} queries")

    # --- Strong de-duplication & clustering across sources ---
    clusters = {}  # key: (norm_title, norm_company) -> merged job
    for j in all_jobs:
        nt = norm_text(j["title"])
        nc = norm_text(j["company"])
        key = (nt, nc)

        link_key = norm_link(j["link"])

        if key not in clusters:
            clusters[key] = {
                "title": j["title"],
                "company": j["company"],
                "link": j["link"],
                "link_keys": {link_key},
                "source": j["source"],   # primary display source
                "sources": [j["source"]],
                "tags": sorted(set(j.get("tags", []))),
                "_loc": j.get("_loc", "")
            }
        else:
            c = clusters[key]
            # Prefer a more canonical link if shorter path
            if link_key not in c["link_keys"]:
                c["link_keys"].add(link_key)
                if len(j["link"]) < len(c["link"]):
                    c["link"] = j["link"]
                    c["source"] = j["source"]
            if j["source"] not in c["sources"]:
                c["sources"].append(j["source"])
            c["tags"] = sorted(set(c["tags"] + j.get("tags", [])))
            if not c.get("_loc") and j.get("_loc"):
                c["_loc"] = j["_loc"]

    merged_jobs = []
    for c in clusters.values():
        merged_jobs.append({
            "title": c["title"],
            "company": c["company"],
            "link": c["link"],
            "source": c["source"],
            "sources": c["sources"],
            "tags": c["tags"],
            "_loc": c.get("_loc", "")
        })

    merged_jobs.sort(key=lambda x: (x["company"].lower(), x["title"].lower()))
    return merged_jobs, counts, diag_all

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
      <title>AZ Pilot Jobs — Aircraft Keywords</title>
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
        .sources { font-size: 12px; color: var(--muted); margin-left: 8px; }
        .loc { font-size: 12px; color: var(--muted); margin-left: 8px; }
        .links { margin-top: 8px; }
        .links a { margin-right: 10px; }
      </style>
    </head>
    <body>
      <div class="wrap" id="app" data-theme="dark">
        <div class="card">
          <h1>Arizona Pilot Jobs — Keyword Focus</h1>
    """
    html += f"<p class='sub'>Updated {now_str}</p>"

    # Controls
    html += """
          <div class="controls">
            <input type="text" id="jobSearch" onkeyup="filterAll()" placeholder="Search (e.g., company, title)">
            <div class="toolbar">
              <button onclick="filterSource('all')" class="active" id="btnAll">All</button>
    """
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
              <button onclick="toggleTag('General')" id="tagGeneral">General</button>
            </div>
            <div class="links">
              <a href="jobs_today.json" target="_blank">Download jobs_today.json</a>
              <a href="jobs_history.json" target="_blank">View jobs_history.json</a>
              <a href="scrape_report.json" target="_blank">View scrape_report.json</a>
            </div>
          </div>
          <p class="sub">AZ-only: using site location parameters plus a secondary Arizona text filter. Duplicates across sites are merged.</p>
    """
    # Debug counts
    html += "<div class='debug'><strong>Per-source counts this run:</strong> "
    html += " • ".join([f"{name}: {count}" for name, count in counts.items()])
    html += "</div></div>"

    # Diagnostics hint card
    html += """
      <div class="card">
        <details open>
          <summary><strong>Diagnostics</strong></summary>
          <p class="sub">If some sources show 0, open <em>scrape_report.json</em> to see per-query URLs, status codes, errors, and captcha hints.</p>
        </details>
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
            tags = job.get("tags") or []
            tag_html = "".join([f"<span class='tag'>{t}</span>" for t in tags])
            sources = job.get("sources", [job.get("source")])
            sources_text = ", ".join(sources)
            loc_text = job.get("_loc", "")
            loc_html = f"<span class='loc'>• {loc_text}</span>" if loc_text else ""
            html += (
                f"<li class='job-item' data-source='{job['source']}' data-tags='{'|'.join(tags)}'>"
                f"<a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} "
                f"<span class='sourceTag'>({job['source']})</span>"
                f"<span class='sources'>Found on: {sources_text}</span>{loc_html}"
                f"{tag_html}</li>"
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
            sources = job.get("sources", [job.get("source")])
            sources_text = ", ".join(sources)
            loc_text = job.get("_loc", "")
            loc_html = f"<span class='loc'>• {loc_text}</span>" if loc_text else ""
            html += (
                f"<li class='job-item' data-source='{job['source']}' data-tags='{'|'.join(tags)}'>"
                f"<a href='{job['link']}' target='_blank'>{job['title']}</a> — {job['company']} "
                f"<span class='sourceTag'>({job['source']})</span>"
                f"<span class='sources'>Found on: {sources_text}</span>{loc_html}"
                f"{tag_html}</li>"
            )
        html += "</ul>"
    html += "</div>"

    # Client-side filters + theme toggle
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
          const idMap = {
            "Caravan":"tagCaravan", "PC-12":"tagPC12", "Part 91":"tagPart91",
            "SkyCourier":"tagSkyCourier", "Baron":"tagBaron", "Navajo":"tagNavajo",
            "General":"tagGeneral"
          };
          const btn = document.getElementById(idMap[tag]);
          if(activeTags.has(tag)){ activeTags.delete(tag); btn.classList.remove('active'); }
          else { activeTags.add(tag); btn.classList.add('active'); }
          filterAll();
        }
        function filterAll() {
          const q = (document.getElementById('jobSearch').value || '').toLowerCase();
          const activeSrcBtn = document.querySelector('.toolbar button.active#btnAll, .toolbar button.active:not(#tagCaravan):not(#tagPC12):not(#tagPart91):not(#tagSkyCourier):not(#tagBaron):not(#tagNavajo):not(#tagGeneral)');
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

    today_jobs, counts, diag_all = scrape_all_sites()

    # Replace today's jobs, keep prior days
    history[today_key] = today_jobs

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
    generate_html(today_jobs, history, counts)

    # Save today's jobs (flat JSON)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(today_jobs, f, indent=2)

    # Save a detailed scrape report for debugging
    with open(OUTPUT_DIAG, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.datetime.now().isoformat(),
            "counts": counts,
            "sites": diag_all
        }, f, indent=2)

if __name__ == "__main__":
    main()
