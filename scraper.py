import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
from urllib.parse import quote_plus

OUTPUT_FILE = "jobs.json"
HISTORY_FILE = "jobs_history.json"

# Southwest coverage cities
SW_CITIES = [
    "Phoenix, AZ", "Scottsdale, AZ", "Mesa, AZ", "Chandler, AZ", "Glendale, AZ",
    "Tempe, AZ", "Prescott, AZ", "Flagstaff, AZ", "Tucson, AZ", "Yuma, AZ",
    "Albuquerque, NM", "Santa Fe, NM", "Las Cruces, NM",
    "Las Vegas, NV", "Henderson, NV", "North Las Vegas, NV",
    "St George, UT", "Cedar City, UT",
    "Grand Junction, CO", "Durango, CO", "Montrose, CO", "Colorado Springs, CO",
    "El Paso, TX", "Midland, TX", "Odessa, TX",
    "San Diego, CA", "Carlsbad, CA", "Oceanside, CA", "Riverside, CA",
    "San Bernardino, CA", "Ontario, CA", "Palm Springs, CA", "Imperial, CA",
    "Burbank, CA", "Long Beach, CA", "Orange County, CA"
]

# Keywords for filtering
KEYWORDS = ["caravan", "cessna 208", "pc-12", "pc12", "pilatus", "king air", "navajo", "pa-31"]

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def add_tags(job):
    title = (job.get("title") or "").lower()
    tags = set(job.get("tags") or [])

    if "caravan" in title or "cessna 208" in title or "208b" in title:
        tags.update(["Caravan", "Cessna 208"])
    if "pc-12" in title or "pc12" in title or "pilatus" in title:
        tags.update(["PC-12", "Pilatus"])
    if "king air" in title or "be200" in title or "be350" in title or "c90" in title:
        tags.add("King Air")
    if "navajo" in title or "pa-31" in title:
        tags.add("Navajo")

    job["tags"] = sorted(tags)
    return job

def is_relevant(job):
    title = (job.get("title") or "").lower()
    return any(k in title for k in KEYWORDS)

def success_result(count, message="OK"):
    return {"status": "success", "count": count, "message": message}

def fail_result(err):
    return {"status": "fail", "count": 0, "message": str(err)}

# -------------------------------
# Indeed RSS scraper
# -------------------------------
def scrape_indeed_rss_southwest():
    all_jobs = []
    errors = []
    for city in SW_CITIES:
        try:
            url = f"https://rss.indeed.com/rss?q={quote_plus('pilot')}&l={quote_plus(city)}"
            resp = requests.get(url, timeout=12)
            if resp.status_code != 200:
                errors.append(f"{city}: HTTP {resp.status_code}")
                continue
            soup = BeautifulSoup(resp.text, "xml")
            for item in soup.find_all("item"):
                title = item.title.get_text(strip=True) if item.title else ""
                link = item.link.get_text(strip=True) if item.link else ""
                pub_date = item.pubDate.get_text(strip=True) if item.pubDate else None
                date_posted = today_str()
                if pub_date:
                    try:
                        date_posted = datetime.strptime(pub_date[:16], "%a, %d %b %Y").strftime("%Y-%m-%d")
                    except:
                        pass
                job = {
                    "title": title,
                    "company": "Indeed",
                    "link": link,
                    "source": f"Indeed RSS ({city})",
                    "tags": [],
                    "date_posted": date_posted
                }
                if is_relevant(job):
                    all_jobs.append(add_tags(job))
        except Exception as e:
            errors.append(f"{city}: {e}")

    if errors and not all_jobs:
        return [], fail_result("; ".join(errors))
    if not all_jobs:
        return [], success_result(0, "No relevant jobs found")
    return all_jobs, success_result(len(all_jobs))

# -------------------------------
# Company scrapers
# -------------------------------
def scrape_cutter():
    url = "https://cutteraviation.com/careers"
    jobs = []
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a"):
            title = a.get_text(strip=True)
            href = a.get("href")
            if not title:
                continue
            job = {
                "title": title,
                "company": "Cutter Aviation",
                "link": href if (href and href.startswith("http")) else url,
                "source": "Cutter Aviation",
                "tags": [],
                "date_posted": today_str()
            }
            if is_relevant(job):
                jobs.append(add_tags(job))
        return jobs, success_result(len(jobs))
    except Exception as e:
        return [], fail_result(e)

def scrape_boutique_air():
    url = "https://www.boutiqueair.com/careers"
    jobs = []
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for el in soup.select("div.careers-listing li, div.careers-listing a, li a"):
            title = el.get_text(strip=True)
            href = el.get("href") if el.has_attr("href") else None
            if not title:
                continue
            job = {
                "title": title,
                "company": "Boutique Air",
                "link": href if (href and href.startswith("http")) else url,
                "source": "Boutique Air",
                "tags": [],
                "date_posted": today_str()
            }
            if is_relevant(job):
                jobs.append(add_tags(job))
        return jobs, success_result(len(jobs))
    except Exception as e:
        return [], fail_result(e)

def scrape_contour_aviation():
    url = "https://www.contouraviation.com/careers"
    jobs = []
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for el in soup.select("div.job-listing, li a, h3, h4"):
            title = el.get_text(strip=True)
            href = el.get("href") if el.has_attr("href") else None
            if not title:
                continue
            job = {
                "title": title,
                "company": "Contour Aviation",
                "link": href if (href and href.startswith("http")) else url,
                "source": "Contour Aviation",
                "tags": [],
                "date_posted": today_str()
            }
            if is_relevant(job):
                jobs.append(add_tags(job))
        return jobs, success_result(len(jobs))
    except Exception as e:
        return [], fail_result(e)

def scrape_ameriflight():
    url = "https://www.ameriflight.com/careers"
    jobs = []
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a"):
            title = a.get_text(strip=True)
            href = a.get("href")
            if not title:
                continue
            job = {
                "title": title,
                "company": "Ameriflight",
                "link": href if (href and href.startswith("http")) else url,
                "source": "Ameriflight",
                "tags": [],
                "date_posted": today_str()
            }
            if is_relevant(job):
                jobs.append(add_tags(job))
        return jobs, success_result(len(jobs))
    except Exception as e:
        return [], fail_result(e)

def scrape_skywest():
    url = "https://www.skywest.com/skywest-airline-jobs/career-guides/pilots/"
    jobs = []
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.select("a"):
            title = a.get_text(strip=True)
            href = a.get("href")
            if not title:
                continue
            job = {
                "title": title,
                "company": "SkyWest",
                "link": href if (href and href.startswith("http")) else url,
                "source": "SkyWest",
                "tags": [],
                "date_posted": today_str()
            }
            if is_relevant(job):
                jobs.append(add_tags(job))
        return jobs, success_result(len(jobs))
    except Exception as e:
        return [], fail_result(e)

def scrape_pilotcareercenter_sw():
    urls = [
        "https://pilotcareercenter.com/PHOENIX-PILOT-JOBS/KIWA-KDVT-KPHX-KSDL",
        "https://pilotcareercenter.com/AZ",
    ]
    jobs = []
    errs = []
    try:
        for url in urls:
            try:
                resp = requests.get(url, timeout=12)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.select("a"):
                    title = a.get_text(strip=True)
                    href = a.get("href")
                    if not title:
                        continue
                    job = {
                        "title": title,
                        "company": "PilotCareerCenter",
                        "link": href if (href and href.startswith("http")) else url,
                        "source": "PilotCareerCenter.com",
                        "tags": [],
                        "date_posted": today_str()
                    }
                    if is_relevant(job):
                        jobs.append(add_tags(job))
            except Exception as e:
                errs.append(f"{url}: {e}")
        if errs and not jobs:
            return [], fail_result("; ".join(errs))
        return jobs, success_result(len(jobs))
    except Exception as e:
        return [], fail_result(e)

# -------------------------------
# Aggregator
# -------------------------------
def scrape_all_sites():
    all_jobs = []
    results = {}

    scrapers = {
        "Indeed RSS (SW multi-city)": scrape_indeed_rss_southwest,
        "Cutter Aviation": scrape_cutter,
        "Boutique Air": scrape_boutique_air,
        "Contour Aviation": scrape_contour_aviation,
        "Ameriflight": scrape_ameriflight,
        "SkyWest": scrape_skywest,
        "PilotCareerCenter.com": scrape_pilotcareercenter_sw,
    }

    for name, func in scrapers.items():
        jobs, result = func()
        print(f"{name}: {result.get('count', 0)} jobs scraped ({result.get('message','')})")
        dedup = {(j["title"], j.get("company",""), j["link"]): j for j in jobs}
        jobs = list(dedup.values())
        all_jobs.extend(jobs)
        results[name] = result

    all_jobs = list({(j["title"], j.get("company",""), j["link"]): j for j in all_jobs}.values())
    return all_jobs, results

# -------------------------------
# Save
# -------------------------------
def save_history(today_jobs, results):
    today = today_str()

    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            history = json.load(f)
    else:
        history = {"today": [], "history": {}, "results": {}}

    history["today"] = today_jobs
    history["history"][today] = today_jobs
    history["results"] = results

    with open(OUTPUT_FILE, "w") as f:
        json.dump(history, f, indent=2)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# -------------------------------
# Main
# -------------------------------
def main():
    all_jobs, results = scrape_all_sites()
    print("Total relevant jobs scraped:", len(all_jobs))
    save_history(all_jobs, results)

if __name__ == "__main__":
    main()
