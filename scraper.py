import requests, json, datetime, os, re, time
from bs4 import BeautifulSoup

# ---------- Config ----------
HISTORY_FILE = "jobs_history.json"
OUTPUT_JSON  = "jobs.json"
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
    "phoenix", "scottsdale", "mesa", "chandler", "tempe", "glendale",
    "tucson", "flagstaff", "prescott", "yuma", "sedona",
    # airport codes
    "phx", "tus", "sdl", "iwa", "gcn", "prc"
}

# ---------- Helpers ----------

def is_arizona(text: str) -> bool:
    t = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    if " arizona " in t or re.search(r"\baz\b", t):
        return True
    for term in AZ_TERMS:
        if f" {term} " in t:
            return True
    return False

def fetch_url(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        return requests.get(url, headers=headers, timeout=20)
    except Exception as e:
        print(f"Fetch failed for {url}: {e}")
        return None

def norm_text(s):
    return re.sub(r"\s+", " ", (s or "").lower().strip())

def norm_link(url):
    return url.split("?")[0]

def tag_job(title, company):
    tags = []
    blob = f"{title} {company}"
    for kt in KEYWORD_TAGS:
        if kt["pattern"].search(blob):
            tags.append(kt["label"])
    return tags or ["General"]

# ---------- Scrapers ----------

def scrape_indeed_rss():
    url = "https://www.indeed.com/rss?q=pilot&l=Arizona"
    jobs = []
    try:
        resp = fetch_url(url)
        if not resp: return jobs
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        print(f"Indeed: {len(items)} raw items")
        for item in items:
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
        print(f" -> {len(jobs)} after AZ filter")
    except Exception as e:
        print("Error scraping Indeed:", e)
    return jobs

def scrape_pilotsglobal():
    url = "https://pilotsglobal.com/jobs?keyword=pilot&location=arizona"
    jobs = []
    try:
        resp = fetch_url(url)
        if not resp: return jobs
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.job-list a.job-card")
        print(f"PilotsGlobal: {len(cards)} raw items")
        for card in cards:
            title = card.get_text(strip=True)
            link  = card.get("href")
            company = "Unknown"
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
        print(f" -> {len(jobs)} after AZ filter")
    except Exception as e:
        print("Error scraping PilotsGlobal:", e)
    return jobs

def scrape_jsfirm():
    url = "https://www.jsfirm.com/jobs/search?keywords=pilot+arizona"
    jobs = []
    try:
        resp = fetch_url(url)
        if not resp: return jobs
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.job-card")
        print(f"JSFirm: {len(cards)} raw items")
        for card in cards:
            a = card.select_one("a")
            if not a: continue
            title = a.get_text(strip=True)
            link  = a.get("href")
            company_tag = card.select_one(".company")
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
        print(f" -> {len(jobs)} after AZ filter")
    except Exception as e:
        print("Error scraping JSFirm:", e)
    return jobs

def scrape_company(name, url):
    jobs = []
    try:
        resp = fetch_url(url)
        if not resp or resp.status_code != 200:
            return jobs
        soup = BeautifulSoup(resp.text, "html.parser")
        tags = soup.find_all(["a", "li", "div"])
        print(f"{name}: {len(tags)} raw tags")
        for tag in tags:
            text = tag.get_text(strip=True).lower()
            if "pilot" in text:
                title = tag.get_text(strip=True)
                href = tag.get("href") or url
                link = href if href.startswith("http") else url
                if not is_arizona(title):
                    continue
                jobs.append({
                    "title": title,
                    "company": name,
                    "link": link,
                    "source": name,
                    "tags": tag_job(title, name)
                })
        print(f" -> {len(jobs)} after AZ filter")
    except Exception as e:
        print(f"Error scraping {name}:", e)
    return jobs

def scrape_ameriflight():
    return scrape_company("Ameriflight", "https://www.ameriflight.com/careers")

def scrape_boutique_air():
    return scrape_company("Boutique Air", "https://www.boutiqueair.com/careers")

def scrape_planesense():
    return scrape_company("PlaneSense", "https://www.planesense.com/careers")

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
    all_jobs, counts = [], {}
    for name, func in sources.items():
        jobs = func()
        counts[name] = len(jobs)
        for j in jobs:
            j.setdefault("sources", [j["source"]])
        all_jobs.extend(jobs)
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
            c["tags"] = sorted(set(c.get("tags", []) + j.get("tags", [])))
    merged = []
    for c in clusters.values():
        merged.append({k: v for k, v in c.items() if k not in ("link_keys",)})
    return merged, counts

# ---------- History + Main ----------

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

def main():
    today = datetime.date.today().isoformat()
    history = load_history()
    jobs, counts = scrape_all_sites()
    history[today] = jobs

    # keep only last 30 days
    cutoff = datetime.date.today() - datetime.timedelta(days=DAYS_TO_KEEP)
    history = {d: j for d, j in history.items() if datetime.date.fromisoformat(d) >= cutoff}

    save_history(history)

    # Save combined JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"today": jobs, "history": history}, f, indent=2)

    print(f"Saved {len(jobs)} jobs for {today}, source counts: {counts}")

if __name__ == "__main__":
    main()
