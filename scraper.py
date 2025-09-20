import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

OUTPUT_FILE = "jobs.json"
HISTORY_FILE = "jobs_history.json"

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
    return any(k in title for k in ["caravan", "cessna 208", "pc-12", "pc12", "pilatus", "king air", "navajo"])

def success_result(count):
    return {"status": "success", "count": count}

def fail_result(err):
    return {"status": "fail", "count": 0, "error": str(err)}

def scrape_pilotcareercenter():
    base = "https://pilotcareercenter.com"
    urls = [
        f"{base}/PHOENIX-PILOT-JOBS/KIWA-KDVT-KPHX-KSDL",
        f"{base}/AZ"
    ]
    jobs = []
    try:
        for url in urls:
            resp = requests.get(url, timeout=12)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("a"):
                title = a.get_text(strip=True)
                href = a.get("href")
                if not title:
                    continue
                link = href if (href and href.startswith("http")) else (base + href if href else url)
                job = {
                    "title": title,
                    "company": "PilotCareerCenter",
                    "link": link,
                    "source": "PilotCareerCenter",
                    "tags": [],
                    "date_posted": today_str()
                }
                if is_relevant(job):
                    jobs.append(add_tags(job))
        return jobs, success_result(len(jobs))
    except Exception as e:
        return [], fail_result(e)

def scrape_all_sites():
    all_jobs = []
    results = {}

    scrapers = {
        "PilotCareerCenter": scrape_pilotcareercenter
    }

    for name, func in scrapers.items():
        jobs, result = func()
        print(f"{name}: {result}")
        dedup = {(j["title"], j["link"]): j for j in jobs}
        all_jobs.extend(dedup.values())
        results[name] = result

    return all_jobs, results

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

def main():
    jobs, results = scrape_all_sites()
    print("Total relevant jobs scraped:", len(jobs))
    save_history(jobs, results)

if __name__ == "__main__":
    main()