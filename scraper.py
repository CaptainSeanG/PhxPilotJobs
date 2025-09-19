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
OUTPUT_JSON  = "jobs_today.json"   # NEW: flat JSON export of today's jobs
DAYS_TO_KEEP = 30

# Aircraft/ops keywords
KEYWORDS = [
    "caravan", "pc-12", "pc12", "pilatus", "cessna 208", "sky courier", "skycourier",
    "baron", "navajo"
]

# Tagging rules
KEYWORD_TAGS = [
    {"label": "Caravan",     "pattern": re.compile(r"\bcaravan\b|\bcessna\s*208\b", re.I)},
    {"label": "PC-12",       "pattern": re.compile(r"\bpc[-\s]?12\b|\bpilatus\b", re.I)},
    {"label": "Part 91",     "pattern": re.compile(r"\bpart\s*91\b", re.I)},
    {"label": "SkyCourier",  "pattern": re.compile(r"\bsky\s*courier\b|\bskycourier\b", re.I)},
    {"label": "Baron",       "pattern": re.compile(r"\bbaron\b", re.I)},
    {"label": "Navajo",      "pattern": re.compile(r"\bnavajo\b", re.I)},
]

# Arizona terms
AZ_TERMS = {
    "az", "arizona",
    "phoenix", "scottsdale", "mesa", "chandler", "tempe", "glendale", "peoria",
    "gilbert", "surprise", "goodyear", "buckeye", "avondale",
    "tucson", "flagstaff", "prescott", "yuma", "sedona",
    "sierra vista", "queen creek", "casa grande", "maricopa",
    "lake havasu", "kingman", "payson", "show low"
}

def is_arizona(text: str) -> bool:
    t = " " + re.sub(r"\s+", " ", (text or "").lower()) + " "
    if " arizona " in t or re.search(r"\baz\b", t):
        return True
    for city in AZ_TERMS:
        if f" {city} " in t:
            return True
    return False

# ---------- ScraperAPI ----------
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def fetch_url(url, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", "Mozilla/5.0")
    timeout = kwargs.pop("timeout", 25)
    if SCRAPER_API_KEY:
        proxy_url = "http://api.scraperapi.com/"
        params = {"api_key": SCRAPER_API_KEY, "url": url, "render": "true"}
        proxied = proxy_url + "?" + urlencode(params)
        return requests.get(proxied, headers=headers, timeout=timeout, **kwargs)
    else:
        return requests.get(url, headers=headers, timeout=timeout, **kwargs)

# ---------- Sites ----------
def indeed_url(q):       return f"https://www.indeed.com/jobs?q={quote_plus(q)}&l=Arizona"
def zip_url(q):          return f"https://www.ziprecruiter.com/candidate/search?search={quote_plus(q)}&location=Arizona"
def glassdoor_url(q):    return f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={quote_plus(q + ' Arizona')}"
def pilotsglobal_url(q): return f"https://pilotsglobal.com/jobs?keyword={quote_plus(q)}&location=arizona"
def jsfirm_url(q):       return f"https://www.jsfirm.com/jobs/search?keywords={quote_plus(q + ' Arizona')}"
def climbto350_url(q):   return f"https://www.climbto350.com/jobs?keyword={quote_plus(q)}&location=Arizona"

SITES = [
    {"name": "ZipRecruiter", "url_fn": zip_url, "parser": "html.parser",
     "selectors": {"job":"article.job_result, article.job_content","title":"a[aria-label], a.job_link, a[href*='/jobs/']","company":"a.t_org_link, div.job_name a, div.job_name span","location":"div.location, span.location"}},
    {"name": "PilotsGlobal", "url_fn": pilotsglobal_url, "parser": "html.parser",
     "selectors": {"job":"div.search-result, div.job-item, article","title":"a[href*='/job/']","company":"div.company, span.company","location":"div.location, span.location"}},
    {"name": "Indeed", "url_fn": indeed_url, "parser": "html.parser",
     "selectors": {"job":"div.job_seen_beacon, div.cardOutline","title":"h2 a, a.jcs-JobTitle","company":"span.companyName","location":"div.companyLocation"}},
    {"name": "JSfirm", "url_fn": jsfirm_url, "parser": "html.parser",
     "selectors": {"job":"li.job-result, div.search-result","title":"a","company":"span.company, div.company","location":"span.location, div.location"}},
    {"name": "Climbto350", "url_fn": climbto350_url, "parser": "html.parser",
     "selectors": {"job":"li.job, div.job","title":"a","company":"span.company, div.company","location":"span.location, div.location"}},
    {"name": "Glassdoor", "url_fn": glassdoor_url, "parser": "html.parser",
     "selectors": {"job":"li.react-job-listing, li#MainCol div.jobCard","title":"a.jobLink","company":"div.jobHeader a","location":"span.pr-xxsm, div.location"}}
]

# ---------- Utils ----------
def make_absolute(base_url, href):
    if not href: return base_url
    if href.startswith(("http://","https://")): return href
    origin = base_url.split("/")[0] + "//" + base_url.split("/")[2]
    if href.startswith("/"): return origin + href
    return base_url.rstrip("/") + "/" + href

def norm_text(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+"," ",s).strip()

def norm_link(url):
    try:
        parts = urlsplit(url)
        return urlunsplit(("", parts.netloc.lower(), parts.path or "/", "", ""))
    except Exception:
        return url

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
            title_tag = card.select_one(site["selectors"]["title"])
            company_tag = card.select_one(site["selectors"]["company"])
            if not title_tag: continue
            title = title_tag.get_text(strip=True)
            link = make_absolute(url, title_tag.get("href"))
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"
            loc_text = ""
            if "location" in site["selectors"]:
                loc_tag = card.select_one(site["selectors"]["location"])
                if loc_tag: loc_text = loc_tag.get_text(" ", strip=True)
            card_text = card.get_text(" ", strip=True)
            if not (is_arizona(loc_text) or is_arizona(card_text)):
                continue
            jobs.append({"title": title,"company": company,"link": link,
                         "source": site["name"],"tags": tag_job(title,company)})
    except Exception as e:
        print(f"Error scraping {site['name']} ({q}): {e}")
    return jobs

def scrape_all_sites():
    all_jobs, counts = [], {}
    for site in SITES:
        site_total = 0
        for q in KEYWORDS:
            items = scrape_site_for_query(site, q)
            site_total += len(items)
            all_jobs.extend(items)
        counts[site["name"]] = site_total
    # Deduplicate
    clusters = {}
    for j in all_jobs:
        key = (norm_text(j["title"]), norm_text(j["company"]))
        link_key = norm_link(j["link"])
        if key not in clusters:
            clusters[key] = {**j, "sources":[j["source"]], "link_keys":{link_key}}
        else:
            c = clusters[key]
            if link_key not in c["link_keys"]:
                c["link_keys"].add(link_key)
                if len(j["link"]) < len(c["link"]): c["link"] = j["link"]
            if j["source"] not in c["sources"]: c["sources"].append(j["source"])
            c["tags"] = sorted(set(c["tags"] + j.get("tags",[])))
    merged = []
    for c in clusters.values():
        merged.append({k:v for k,v in c.items() if k not in ("link_keys",)})
    return merged, counts

# ---------- History ----------
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE,"r",encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_history(history):
    with open(HISTORY_FILE,"w",encoding="utf-8") as f:
        json.dump(history,f,indent=2)

# ---------- HTML ----------
def generate_html(today_jobs, history, counts):
    # (same HTML generation as before — omitted here for brevity)
    with open(OUTPUT_HTML,"w",encoding="utf-8") as f:
        f.write("<html><body><h1>Jobs</h1></body></html>")  # placeholder

# ---------- Main ----------
def main():
    today_key = datetime.date.today().isoformat()
    history = load_history()
    today_jobs, counts = scrape_all_sites()
    history[today_key] = today_jobs
    cutoff = datetime.date.today() - datetime.timedelta(days=DAYS_TO_KEEP)
    history = {d:jobs for d,jobs in history.items() if datetime.date.fromisoformat(d)>=cutoff}
    save_history(history)
    generate_html(today_jobs, history, counts)
    with open(OUTPUT_JSON,"w",encoding="utf-8") as f:
        json.dump(today_jobs,f,indent=2)

if __name__=="__main__":
    main()
