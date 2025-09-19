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

# Aircraft/ops keywords we care about
KEYWORDS = [
    "caravan", "pc-12", "pc12", "pilatus", "cessna 208", "sky courier", "skycourier",
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

# Arizona check: state terms + a set of city names (expandable)
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

# ---------- ScraperAPI routing ----------
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def fetch_url(url, **kwargs):
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
        "name": "Glassdoor",
        "url_fn": glassdoor_url,
        "parser": "html.parser",
        "selectors": {
            "job":     "li.react-job-listing, li#MainCol div.jobCard",
            "title":   "a.jobLink, a.jobTitle",
            "company": "div.jobHeader a, div.jobInfoItem.jobEmpolyerName",
            "location":"span.pr-xxsm, span.css-56kyx5, div.location"
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
    s = (s or "").lower()
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"[^\w\s&]", " ", s)        
    s = re.sub(r"\b(inc|llc|l\.l\.c|co|corp|corporation|company)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def norm_link(url):
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

# ---------- Scraping ----------
# (scrape_site_for_query, scrape_all_sites, and HTML generation go here — unchanged from the last version you pasted in)

# ---------- Main ----------
def main():
    today_key = datetime.date.today().isoformat()
    history = load_history()

    today_jobs, counts = scrape_all_sites()

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

    # NEW: save today's jobs as JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(today_jobs, f, indent=2)

if __name__ == "__main__":
    main()
