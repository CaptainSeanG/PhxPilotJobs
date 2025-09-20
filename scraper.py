import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_pilotcareercenter():
    url = "https://pilotcareercenter.com/Pilot-Job-Search?c=USA&s=Arizona"
    jobs = []
    results = {"status": "fail", "count": 0}

    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.select("div.jobListing")
            for l in listings:
                title = l.find("h3")
                company = l.find("h4")
                link = l.find("a", href=True)
                if title and company and link:
                    jobs.append({
                        "title": title.get_text(strip=True),
                        "company": company.get_text(strip=True),
                        "link": "https://pilotcareercenter.com" + link["href"],
                        "source": "PilotCareerCenter",
                        "tags": []
                    })
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping PilotCareerCenter:", e)

    return jobs, results

def save_history(history):
    with open("jobs.json", "w") as f:
        json.dump(history, f, indent=2)
    with open("jobs_history.json", "w") as f:
        json.dump(history, f, indent=2)

def load_history():
    try:
        with open("jobs.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"today": [], "history": {}, "results": {}}

def main():
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")

    all_jobs = []
    results = {}

    # Currently only PilotCareerCenter scraper enabled
    pcc_jobs, pcc_results = scrape_pilotcareercenter()
    all_jobs.extend(pcc_jobs)
    results["PilotCareerCenter"] = pcc_results

    history["today"] = all_jobs
    if "history" not in history:
        history["history"] = {}
    history["history"][today] = all_jobs
    history["results"] = results

    print("Scraped", len(all_jobs), "jobs")
    save_history(history)

if __name__ == "__main__":
    main()
