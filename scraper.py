import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

OUTPUT_FILE = "jobs.json"
HISTORY_FILE = "jobs_history.json"

# -------------------------------
# Scrapers
# -------------------------------

def scrape_indeed_rss():
    url = "https://rss.indeed.com/rss?q=pilot&l=Arizona"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        for item in soup.find_all("item"):
            title = item.title.get_text()
            link = item.link.get_text()
            if any(tag in title.lower() for tag in ["caravan", "pc-12", "pc12", "pilatus", "cessna", "baron", "navajo", "king air"]):
                jobs.append({
                    "title": title,
                    "company": "Indeed",
                    "link": link,
                    "source": "Indeed RSS",
                    "tags": []
                })
        status = "success"
    except Exception as e:
        print("Error scraping Indeed RSS:", e)
        status, jobs = "fail", []
    return jobs, {"status": status, "count": len(jobs)}

def scrape_cutter():
    url = "https://cutteraviation.com/careers"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for job in soup.select("a"):
            title = job.get_text(strip=True)
            link = job.get("href")
            if title and "pilot" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "Cutter Aviation",
                    "link": link if link and link.startswith("http") else url,
                    "source": "Cutter Aviation",
                    "tags": []
                })
        status = "success"
    except Exception as e:
        print("Error scraping Cutter:", e)
        status, jobs = "fail", []
    return jobs, {"status": status, "count": len(jobs)}

def scrape_boutique_air():
    url = "https://www.boutiqueair.com/careers"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for job in soup.select("div.careers-listing li, div.careers-listing a, li a"):
            title = job.get_text(strip=True)
            link = job.get("href") if job.has_attr("href") else url
            if "pilot" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "Boutique Air",
                    "link": link if link.startswith("http") else url,
                    "source": "Boutique Air",
                    "tags": []
                })
        status = "success"
    except Exception as e:
        print("Error scraping Boutique Air:", e)
        status, jobs = "fail", []
    return jobs, {"status": status, "count": len(jobs)}

def scrape_contour_aviation():
    url = "https://www.contouraviation.com/careers"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for job in soup.select("div.job-listing, li a, h3, h4"):
            title = job.get_text(strip=True)
            link = job.get("href") if job.has_attr("href") else url
            if "pilot" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "Contour Aviation",
                    "link": link if link.startswith("http") else url,
                    "source": "Contour Aviation",
                    "tags": []
                })
        status = "success"
    except Exception as e:
        print("Error scraping Contour Aviation:", e)
        status, jobs = "fail", []
    return jobs, {"status": status, "count": len(jobs)}

def scrape_ameriflight():
    url = "https://www.ameriflight.com/careers"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for job in soup.select("a"):
            title = job.get_text(strip=True)
            link = job.get("href")
            if title and "pilot" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "Ameriflight",
                    "link": link if link and link.startswith("http") else url,
                    "source": "Ameriflight",
                    "tags": []
                })
        status = "success"
    except Exception as e:
        print("Error scraping Ameriflight:", e)
        status, jobs = "fail", []
    return jobs, {"status": status, "count": len(jobs)}

def scrape_skywest():
    url = "https://www.skywest.com/skywest-airline-jobs/career-guides/pilots/"
    jobs = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for job in soup.select("a"):
            title = job.get_text(strip=True)
            link = job.get("href")
            if title and "pilot" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "SkyWest",
                    "link": link if link and link.startswith("http") else url,
                    "source": "SkyWest",
                    "tags": []
                })
        status = "success"
    except Exception as e:
        print("Error scraping SkyWest:", e)
        status, jobs = "fail", []
    return jobs, {"status": status, "count": len(jobs)}

# -------------------------------
# Main Aggregator
# -------------------------------

def scrape_all_sites():
    all_jobs = []
    results = {}

    scrapers = {
        "Indeed RSS": scrape_indeed_rss,
        "Cutter Aviation": scrape_cutter,
        "Boutique Air": scrape_boutique_air,
        "Contour Aviation": scrape_contour_aviation,
        "Ameriflight": scrape_ameriflight,
        "SkyWest": scrape_skywest,
    }

    for name, func in scrapers.items():
        jobs, result = func()
        print(f"{name}: {result['count']} jobs scraped")
        all_jobs.extend(jobs)
        results[name] = result

    return all_jobs, results

# -------------------------------
# Save / Load Helpers
# -------------------------------

def save_history(today_jobs, results):
    today = datetime.now().strftime("%Y-%m-%d")

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

    # Also save to jobs_history.json for redundancy
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# -------------------------------
# Main
# -------------------------------

def main():
    all_jobs, results = scrape_all_sites()
    print("Total jobs scraped:", len(all_jobs))
    save_history(all_jobs, results)

if __name__ == "__main__":
    main()
