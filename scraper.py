import requests
from bs4 import BeautifulSoup
import datetime, time
import json, os, re
from urllib.parse import quote_plus

# ---------- Config ----------
HISTORY_FILE = "jobs_history.json"
OUTPUT_HTML  = "index.html"
OUTPUT_JSON  = "jobs_today.json"
DAYS_TO_KEEP = 30

KEYWORDS = [
    "pilot", "caravan", "pc-12", "pc12", "pilatus",
    "cessna 208", "sky courier", "skycourier",
    "baron", "navajo"
]

KEYWORD_TAGS = [
    {"label": "Caravan",    "pattern": re.compile(r"\bcaravan\b|\bcessna\s*208\b", re.I)},
    {"label": "PC-12",      "pattern": re.compile(r"\bpc[-\s]?12\b|\bpilatus\b", re.I)},
    {"label": "Part 91",    "pattern": re.compile(r"\bpart\s*91\b", re.I)},
    {"label": "SkyCourier", "pattern": re.compile(r"\bsky\s*courier\b|\bskycourier\b", re.I)},
    {"label": "Baron",      "pattern": re.compile(r"\bbaron\b", re.I)},
    {"label": "Navajo",     "pattern": re.compile(r"\bnavajo\b", re.I)},
]

AZ_TERMS = {
    "az", "arizona",
    "phoenix", "scottsdale", "mesa", "chandler", "tempe", "glendale", "peoria",
    "gilbert", "surprise", "goodyear", "buckeye", "avondale",
    "tucson", "flagstaff", "prescott", "yuma", "sedona"
}

def is_arizona(text: str) -> bool:
    t = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    if " arizona " in t or re.search(r"\baz\b", t):
        return True
    for city in AZ_TERMS:
        if f" {city} " in t:
            return True
    return False

def fetch_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        return resp
    except Exception as e:
        print(f"Fetch failed for {url}: {e}")
        return None

def norm_text(s):
    return re.sub(r"\s+", " ", (s or "").lower().strip())

def norm_link(url):
    try:
        parts = url.split('?')[0]
        return parts
    except:
        return url

def tag_job(title, company):
    tags = []
    blob = f"{title} {company}"
    for kt in KEYWORD_TAGS:
        if kt["pattern"].search(blob):
            tags.append(kt["label"])
    return tags

# ---------- Source scrapers ----------

def scrape_indeed_rss():
    url = "https://www.indeed.com/rss?q=pilot&l=Arizona"
    jobs = []
    resp = fetch_url(url)
    if not resp or resp.status_code != 200:
        print("Indeed RSS fetch failed or non-200:", resp.status_code if resp else "no resp")
        return jobs
    soup = BeautifulSoup(resp.text, "xml")
    for item in soup.find_all("item"):
        title = item.title.text.strip()
        link  = item.link.text.strip()
        company = item.find("source").text.strip() if item.find("source") else "Unknown"
        desc = item.description.text if item.description else ""
        if not is_arizona(title + " " + desc):
            continue
        jobs.append({
            "title": title,
            "company": company,
            "link": link,
            "source": "Indeed",
            "tags": tag_job(title, company)
        })
    return jobs

def scrape_pilotsglobal():
    url = "https://pilotsglobal.com/jobs?keyword=pilot&location=arizona"
    jobs = []
    resp = fetch_url(url)
    if not resp or resp.status_code != 200:
        print("PilotsGlobal fetch failed:", resp.status_code if resp else "no resp")
        return jobs
    soup = BeautifulSoup(resp.text, "html.parser")
    for card in soup.select("div.search-result, div.job-item, article"):
        a = card.select_one("a[href*='/job/']")
        if not a:
            continue
        title = a.get_text(strip=True)
        link = a["href"]
        company_tag = card.select_one("div.company, span.company")
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"
        text = card.get_text(" ", strip=True)
        if not is_arizona(text):
            continue
        jobs.append({
            "title": title,
            "company": company,
            "link": link,
            "source": "PilotsGlobal",
            "tags": tag_job(title, company)
        })
    return jobs

def scrape_jsfirm():
    url = "https://www.jsfirm.com/jobs/search?keywords=pilot+arizona"
    jobs = []
    resp = fetch_url(url)
    if not resp or resp.status_code != 200:
        print("JSFirm fetch failed:", resp.status_code if resp else "no resp")
        return jobs
    soup = BeautifulSoup(resp.text, "html.parser")
    for card in soup.select("li.job-result, div.search-result"):
        a = card.select_one("a")
        if not a:
            continue
        title = a.get_text(strip=True)
        link = a["href"]
        company_tag = card.select_one("span.company, div.company")
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"
        text = card.get_text(" ", strip=True)
        if not is_arizona(text):
            continue
        jobs.append({
            "title": title,
            "company": company,
            "link": link,
            "source": "JSFirm",
            "tags": tag_job(title, company)
        })
    return jobs

# ---------- Company direct sites (examples) ----------

def scrape_ameriflight():
    # Hypothetical pattern; you’ll likely need to adjust if they change their site layout
    url = "https://www.ameriflight.com/careers"
    jobs = []
    resp = fetch_url(url)
    if not resp or resp.status_code != 200:
        print("Ameriflight fetch failed:", resp.status_code if resp else "no resp")
        return jobs
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for listings that include “pilot”
    for card in soup.find_all(lambda tag: tag.name in ["a","li","div"] and "pilot" in tag.get_text(strip=True).lower()):
        title = card.get_text(strip=True)
        href = card.get("href") if card.has_attr("href") else None
        link = href if href and href.startswith("http") else (url + href if href else url)
        company = "Ameriflight"
        if not is_arizona(title):
            continue
        jobs.append({
            "title": title,
            "company": company,
            "link": link,
            "source": "Ameriflight",
            "tags": tag_job(title, company)
        })
    return jobs

def scrape_boutique_air():
    url = "https://www.boutiqueair.com/careers"
    jobs = []
    resp = fetch_url(url)
    if not resp or resp.status_code != 200:
        print("Boutique Air fetch failed:", resp.status_code if resp else "no resp")
        return jobs
    soup = BeautifulSoup(resp.text, "html.parser")
    for card in soup.find_all(lambda tag: tag.name in ["a","li","div"] and "pilot" in tag.get_text(strip=True).lower()):
        title = card.get_text(strip=True)
        href = card.get("href") if card.has_attr("href") else None
        link = href if href and href.startswith("http") else (url + href if href else url)
        company = "Boutique Air"
        if not is_arizona(title):
            continue
        jobs.append({
            "title": title,
            "company": company,
            "link": link,
            "source": "Boutique Air",
            "tags": tag_job(title, company)
        })
    return jobs

def scrape_planesense():
    url = "https://www.planesense.com/careers"
    jobs = []
    resp = fetch_url(url)
    if not resp or resp.status_code != 200:
        print("PlaneSense fetch failed:", resp.status_code if resp else "no resp")
        return jobs
    soup = BeautifulSoup(resp.text, "html.parser")
    for card in soup.find_all(lambda tag: tag.name in ["a","li","div"] and "pilot" in tag.get_text(strip=True).lower()):
        title = card.get_text(strip=True)
        href = card.get("href") if card.has_attr("href") else None
        link = href if href and href.startswith("http") else (url + href if href else url)
        company = "PlaneSense"
        if not is_arizona(title):
            continue
        jobs.append({
            "title": title,
            "company": company,
            "link": link,
            "source": "PlaneSense",
            "tags": tag_job(title, company)
        })
    return jobs

# ---------- Aggregator ----------

def scrape_all_sites():
    sources = {
        "Indeed": scrape_indeed_rss,
        "PilotsGlobal": scrape_pilotsglobal,
        "JSFirm": scrape_jsfirm,
        "Ameriflight": scrape_ameriflight,
        "Boutique Air": scrape_boutique_air,
        "PlaneSense": scrape_planesense,
    }
    all_jobs = []
    counts = {}
    for name, func in sources.items():
        j = func()
        counts[name] = len(j)
        for job in j:
            job.setdefault("sources", [job["source"]])
        all_jobs.extend(j)
        # small sleep to be polite
        time.sleep(1)

    # Deduplicate
    clusters = {}
    for j in all_jobs:
        key = (norm_text(j["title"]), norm_text(j["company"]))
        link_key = norm_link(j["link"])
        if key not in clusters:
            clusters[key] = {**j, "sources": j.get("sources", [j["source"]]), "link_keys": {link_key}}
        else:
            c = clusters[key]
            if link_key not in c["link_keys"]:
                c["link_keys"].add(link_key)
            if j["source"] not in c["sources"]:
                c["sources"].append(j["source"])
            c["tags"] = sorted(set(c.get("tags",[]) + j.get("tags",[])))
    merged = []
    for c in clusters.values():
        merged.append({k:v for k,v in c.items() if k not in ("link_keys",)})
    return merged, counts

# ---------- History ----------

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(h):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, indent=2)

# ---------- HTML Generation with Filters / Tags / DarkLight etc. ----------

def generate_html(today_jobs, history, counts):
    now_str = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    html = """
    <html><head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>AZ Pilot Jobs — Direct Sources</title>
      <style>
        :root { --bg:#0b1320; --card:#121a2b; --text:#e6eefc; --muted:#9ab0d1; --accent:#4da3ff; --accent2:#2ecc71; --link:#a9cbff; }
        [data-theme='light'] { --bg:#f5f7fb; --card:#ffffff; --text:#0b1320; --muted:#445974; --accent:#0b65d4; --accent2:#1a9e4d; --link:#0b65d4; }
        body { margin:0; padding:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; background: var(--bg); color: var(--text); }
        .wrap { max-width:960px; margin:0 auto; padding:24px; }
        .card { background: var(--card); border-radius:12px; padding:20px; margin-bottom:20px; }
        h1 { font-size:28px; margin-bottom:10px; }
        .sub { color: var(--muted); margin-bottom:15px; }
        .controls { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:20px; }
        input[type="text"] { flex:1 1 300px; padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.2); background:transparent; color: var(--text); }
        button { padding:8px 12px; border:none; border-radius:8px; cursor:pointer; background: var(--accent); color:#fff; }
        button.active { background: var(--accent2); }
        ul { list-style:none; padding:0; margin:0; }
        li { margin-bottom:10px; padding:12px; background: color-mix(in srgb, var(--card) 90%, var(--text) 10%); border-radius:8px; }
        a { color: var(--link); text-decoration:none; }
        a:hover { text-decoration: underline; }
        .tag { font-size:12px; margin-left:8px; padding:2px 6px; border-radius:6px; background: var(--accent2); color:#fff; }
        .toolbar { display:flex; flex-wrap:wrap; gap:6px; }
        .sourceTag { font-size:12px; margin-left:6px; color: var(--muted); }
      </style>
    </head><body>
      <div class="wrap" id="app" data-theme="dark">
        <div class="card">
          <h1>Arizona Pilot Jobs (Direct Sources)</h1>
          <p class="sub">Updated """ + now_str + """</p>
          <div class="controls">
            <input type="text" id="jobSearch" onkeyup="filterAll()" placeholder="Search (title / company)">
            <div class="toolbar">
    """
    # Source buttons
    html += "<button onclick=\"filterSource('All')\" class=\"active\" id=\"srcAll\">All</button>"
    for src in counts.keys():
        html += f"<button onclick=\"filterSource('{src}')\" id=\"src{src.replace(' ','')}\" id_src=\"{src}\">{src}</button>"
    html += "</div><div class=\"toolbar\">"
    # Tag buttons
    for tag in [kt["label"] for kt in KEYWORD_TAGS] + ["General"]:
        html += f"<button onclick=\"toggleTag('{tag}')\" id=\"tag{tag}\">{tag}</button>"
    html += "</div>"
    html += f"<div class=\"toolbar\"><a href=\"{OUTPUT_JSON}\" target=\"_blank\">Download jobs_today.json</a></div>"
    html += "</div>"

    # Counts
    html += "<div class=\"sub\">Source counts: " + ", ".join([f"{src}: {counts[src]}" for src in counts]) + "</div>"
    html += "</div>"

    # Today’s jobs
    html += "<div class=\"card\"><h2>Today’s Jobs</h2><ul id=\"todayList\">"
    if today_jobs:
        for job in today_jobs:
            tags = job.get("tags", [])
            tag_spans = "".join([f"<span class='tag'>{t}</span>" for t in tags])
            sources = job.get("sources", [job["source"]])
            sources_text = ", ".join(sources)
            html += "<li data-source=\"" + job["source"] + "\" data-tags=\"" + "|".join(tags) + "\">"
            html += f"<a href=\"{job['link']}\" target=\"_blank\">{job['title']}</a> — {job['company']} "
            html += f"<span class='sourceTag'>({sources_text})</span> {tag_spans}"
            html += "</li>"
    else:
        html += "<li>No jobs found today.</li>"
    html += "</ul></div>"

    # Job history
    html += "<div class=\"card\"><h2>History (Last 30 Days)</h2>"
    for day, jobs in sorted(history.items(), reverse=True):
        html += f"<h3>{day} — {len(jobs)} job{'s' if len(jobs)!=1 else ''}</h3><ul>"
        for job in jobs:
            tags = job.get("tags", [])
            tag_spans = "".join([f"<span class='tag'>{t}</span>" for t in tags])
            sources = job.get("sources", [job["source"]])
            sources_text = ", ".join(sources)
            html += "<li data-source=\"" + job["source"] + "\" data-tags=\"" + "|".join(tags) + "\">"
            html += f"<a href=\"{job['link']}\" target=\"_blank\">{job['title']}</a> — {job['company']} "
            html += f"<span class='sourceTag'>({sources_text})</span> {tag_spans}"
            html += "</li>"
        html += "</ul>"
    html += "</div>"

    # JS: theme toggle, source filter, tag filter, search
    html += """
        </div>
        <script>
          const app = document.getElementById('app');
          const btnTheme = null;

          function toggleTheme(){
            let t = app.getAttribute('data-theme');
            if(t==='dark') t='light'; else t='dark';
            app.setAttribute('data-theme', t);
            localStorage.ppj_theme = t;
          }
          (function(){
            let saved = localStorage.ppj_theme;
            if(saved) app.setAttribute('data-theme', saved);
          })();

          const activeTags = new Set();
          function filterSource(src){
            document.querySelectorAll('.toolbar button').forEach(b => b.classList.remove('active'));
            // activate the source btn
            const btn = [...document.querySelectorAll('.toolbar button')].find(b => b.textContent === src);
            if(btn) btn.classList.add('active');
            filterAll();
          }
          function toggleTag(tag){
            const btn = document.getElementById('tag'+tag);
            if(activeTags.has(tag)){
              activeTags.delete(tag);
              btn.classList.remove('active');
            } else {
              activeTags.add(tag);
              btn.classList.add('active');
            }
            filterAll();
          }
          function filterAll(){
            const q = (document.getElementById('jobSearch').value || '').toLowerCase();
            const activeSrcBtn = [...document.querySelectorAll('.toolbar button')].find(b => b.classList.contains('active') && b.textContent !== 'All');
            const srcFilter = activeSrcBtn ? activeSrcBtn.textContent : 'All';
            document.querySelectorAll('li[data-source]').forEach(li => {
              let show = true;
              const text = li.textContent.toLowerCase();
              if(q && !text.includes(q)) show=false;
              if(srcFilter!=='All' && li.getAttribute('data-source')!==srcFilter) show=false;
              if(activeTags.size>0){
                const liTags = li.getAttribute('data-tags').split('|').filter(Boolean);
                activeTags.forEach(t => { if(!liTags.includes(t)) show=false; });
              }
              li.style.display = show ? '' : 'none';
            });
          }
        </script>
      </body></html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

# ---------- Main ----------

def main():
    today = datetime.date.today().isoformat()
    history = load_history()
    jobs, counts = scrape_all_sites()
    history[today] = jobs
    cutoff = datetime.date.today() - datetime.timedelta(days=DAYS_TO_KEEP)
    history = {d: j for d, j in history.items() if datetime.date.fromisoformat(d) >= cutoff}
    save_history(history)
    generate_html(jobs, history, counts)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)

if __name__ == "__main__":
    main()
