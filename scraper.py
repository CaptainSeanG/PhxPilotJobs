import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---------------------------
# Utility: Parse hours from text
# ---------------------------
def extract_hours(text):
    text = text.lower()
    if "hour" in text:
        for token in text.split():
            if token.isdigit():
                return int(token)
            if token.replace(",", "").isdigit():
                return int(token.replace(",", ""))
    return None

# ---------------------------
# Scraper: Pilot Career Center
# ---------------------------
def scrape_pilotcareercenter():
    url = "https://pilotcareercenter.com/NEW-PILOTS/USA"
    jobs = []
    results = {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.find_all("a")

            scraped_count = 0
            for l in listings:
                text = l.get_text(strip=True)
                href = l.get("href", "")
                if not text:
                    continue
                scraped_count += 1
                hrs = extract_hours(text)

                # ✅ keep if no hours listed OR <= 1100
                if hrs is None or hrs <= 1100:
                    jobs.append({
                        "title": text,
                        "company": "PilotCareerCenter",
                        "link": href if href.startswith("http") else "https://pilotcareercenter.com" + href,
                        "source": "PilotCareerCenter",
                        "tags": [],
                        "hours_required": hrs
                    })

            print(f"PilotCareerCenter scraped: {scraped_count}, kept: {len(jobs)}")
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping PilotCareerCenter:", e)
    return jobs, results

# ---------------------------
# Scraper: SkyWest
# ---------------------------
def scrape_skywest():
    url = "https://skywest.com/skywest-airline-jobs/"
    jobs = []
    results = {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.find_all("a")

            scraped_count = 0
            for l in listings:
                text = l.get_text(strip=True)
                href = l.get("href", "")
                if not text:
                    continue
                scraped_count += 1
                hrs = extract_hours(text)

                if hrs is None or hrs <= 1100:
                    jobs.append({
                        "title": text,
                        "company": "SkyWest",
                        "link": href if href.startswith("http") else "https://skywest.com" + href,
                        "source": "SkyWest",
                        "tags": [],
                        "hours_required": hrs
                    })

            print(f"SkyWest scraped: {scraped_count}, kept: {len(jobs)}")
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping SkyWest:", e)
    return jobs, results

# ---------------------------
# Main
# ---------------------------
def main():
    all_jobs = []
    results_summary = {}

    scrapers = [scrape_pilotcareercenter, scrape_skywest]

    for scraper in scrapers:
        jobs, results = scraper()
        all_jobs.extend(jobs)
        results_summary[results.get("source", scraper.__name__)] = results

    # Write jobs.json
    today_str = datetime.now().strftime("%Y-%m-%d")
    data = {
        "today": all_jobs,
        "history": {today_str: all_jobs},
        "results": results_summary
    }
    with open("jobs.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Total jobs scraped: {len(all_jobs)}")

if __name__ == "__main__":
    main()
