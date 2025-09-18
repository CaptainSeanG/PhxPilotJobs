import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import re
from urllib.parse import urlencode

# ---------- Config ----------
HISTORY_FILE = "jobs_history.json"
OUTPUT_HTML = "index.html"
DAYS_TO_KEEP = 30

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

def fetch_url(url, **kwargs):
    """
    Wrapper for requests.get that uses ScraperAPI if API key is present.
    """
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                                     "Chrome/120.0 Safari/537.36")
    timeout = kwargs.pop("timeout", 25)

    if SCRAPER_API_KEY:
        proxy_url = "http://api.scraperapi.com/"
        params = {
            "api_key": SCRAPER_API_KEY,
            "url": url,
            "render": "true",   # render JavaScript
            "country_code": "us"
        }
        proxied = proxy_url + "?" + urlencode(params)
        return requests.get(proxied, headers=headers, timeout=timeout, **kwargs)
    else:
        return requests.get(url, headers=headers, timeout=timeout, **kwargs)

SITES = [
    {
        "name": "ZipRecruiter",
        "url": "https://www.ziprecruiter.com/candidate/search?search=pilot&location=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {"job": "article.job_result, article.job_content",
                      "title": "a[aria-label], a.job_link, a[href*='/jobs/']",
                      "company": "a.t_org_link, div.job_name a, div.job_name span"}
    },
    {
        "name": "PilotsGlobal",
        "url": "https://pilotsglobal.com/jobs?keyword=pilot&location=phoenix",
        "parser": "html.parser",
        "selectors": {"job": "div.search-result, div.job-item, article",
                      "title": "a[href*='/job/']",
                      "company": "div.company, span.company, a[href*='/company/']"}
    },
    {
        "name": "Indeed",
        "url": "https://www.indeed.com/jobs?q=pilot&l=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {"job": "div.job_seen_beacon, div.cardOutline, div.slider_container",
                      "title": "h2 a, a.jcs-JobTitle",
                      "company": "span.companyName, span[data-testid='company-name']"}
    },
    {
        "name": "JSfirm",
        "url": "https://www.jsfirm.com/pilot/phoenix-az",
        "parser": "html.parser",
        "selectors": {"job": "li.job-result, div.search-result",
                      "title": "a",
                      "company": "span.company, div.company"}
    },
    {
        "name": "Climbto350",
        "url": "https://www.climbto350.com/jobs?keyword=pilot&location=Phoenix%2C+AZ",
        "parser": "html.parser",
        "selectors": {"job": "li.job, div.job",
                      "title": "a",
                      "company": "span.company, div.company"}
    },
    {
        "name": "Glassdoor",
        "url": "https://www.glassdoor.com/Job/phoenix-pilot-jobs-SRCH_IL.0,7_IC1133904_KO8,13.htm",
        "parser": "html.parser",
        "selectors": {"job": "li.react-job-listing",
                      "title": "a.jobLink",
                      "company": "div.jobHeader a"}
    },
]

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
                blob = f"{title} {company}"
                for kt in KEYWORD_TAGS:
                    if kt["pattern"].search(blob):
                        tags.append(kt["label"])
                jobs.append({"title": title, "company": company, "link": link, "source": site["name"], "tags": tags})
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

# (HTML generation function omitted here for brevity — keep your working version with dark/light toggle + filters + debug counts)

def main():
    today_key = datetime.date.today().isoformat()
    history = load_history()
    jobs, counts = scrape_all_sites()

    # Replace today's jobs
    history[today_key] = jobs

    # Trim to last N days
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
    # Call your existing generate_html(jobs, history, counts) here

if __name__ == "__main__":
    main()
