import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from playwright.sync_api import sync_playwright

HEADERS = {"User-Agent": "Mozilla/5.0"}

# -------------------------------
# Scrapers
# -------------------------------

def scrape_pilotcareercenter():
    """Scrape PilotCareerCenter jobs for Arizona using Playwright"""
    url = "https://pilotcareercenter.com/Pilot-Job-Search?c=USA&s=Arizona"
    jobs = []
    results = {"status": "fail", "count": 0}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(5000)  # allow JS to load

            links = page.locator("a").all()
            for l in links:
                text = l.inner_text().strip()
                href = l.get_attribute("href") or ""
                if any(word in text for word in ["Pilot", "Captain", "First Officer"]):
                    jobs.append({
                        "title": text,
                        "company": "PilotCareerCenter",
                        "link": "https://pilotcareercenter.com" + href if href.startswith("/") else href,
                        "source": "PilotCareerCenter",
                        "tags": []
                    })

            browser.close()

        results = {"status": "success", "count": len(jobs)}

    except Exception as e:
        print("Error scraping PilotCareerCenter with Playwright:", e)

    return jobs, results


def scrape_ameriflight():
    url = "https://w3.ameriflight.com/careers/pilots/"
    jobs, results = [], {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.find_all("a", class_="job-title")
            for l in listings:
                jobs.append({
                    "title": l.get_text(strip=True),
                    "company": "Ameriflight",
                    "link": l["href"],
                    "source": "Ameriflight",
                    "tags": ["Cargo"]
                })
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Ameriflight:", e)
    return jobs, results


def scrape_cutter():
    url = "https://cutteraviation.com/careers/"
    jobs, results = [], {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.find_all("a")
            for l in listings:
                if "Pilot" in l.get_text() or "Captain" in l.get_text():
                    jobs.append({
                        "title": l.get_text(strip=True),
                        "company": "Cutter Aviation",
                        "link": l.get("href", ""),
                        "source": "Cutter Aviation",
                        "tags": []
                    })
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Cutter Aviation:", e)
    return jobs, results


def scrape_contour():
    url = "https://www.contouraviation.com/careers"
    jobs, results = [], {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.find_all("a")
            for l in listings:
                if "Pilot" in l.get_text() or "Captain" in l.get_text():
                    jobs.append({
                        "title": l.get_text(strip=True),
                        "company": "Contour Aviation",
                        "link": l.get("href", ""),
                        "source": "Contour Aviation",
                        "tags": []
                    })
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Contour Aviation:", e)
    return jobs, results


def scrape_skywest():
    url = "https://skywest.com/skywest-airline-jobs/"
    jobs, results = [], {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.find_all("a")
            for l in listings:
                text = l.get_text(strip=True)
                href = l.get("href", "")
                if "Pilot" in text or "Captain" in text:
                    jobs.append({
                        "title": text,
                        "company": "SkyWest",
                        "link": href if href.startswith("http") else "https://skywest.com" + href,
                        "source": "SkyWest",
                        "tags": []
                    })
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping SkyWest:", e)
    return jobs, results


def scrape_boutique():
    url = "https://www.boutiqueair.com/pages/careers"
    jobs, results = [], {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.find_all("a")
            for l in listings:
                if "Pilot" in l.get_text() or "Captain" in l.get_text():
                    jobs.append({
                        "title": l.get_text(strip=True),
                        "company": "Boutique Air",
                        "link": l.get("href", ""),
                        "source": "Boutique Air",
                        "tags": []
                    })
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Boutique Air:", e)
    return jobs, results


# -------------------------------
# Helpers
# -------------------------------

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


# -------------------------------
# Main
# -------------------------------

def main():
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")

    all_jobs = []
    results = {}

    scrapers = {
        "PilotCareerCenter": scrape_pilotcareercenter,
        "Ameriflight": scrape_ameriflight,
        "Cutter Aviation": scrape_cutter,
        "Contour Aviation": scrape_contour,
        "SkyWest": scrape_skywest,
        "Boutique Air": scrape_boutique,
    }

    for name, func in scrapers.items():
        jobs, res = func()
        all_jobs.extend(jobs)
        results[name] = res

    history["today"] = all_jobs
    if "history" not in history:
        history["history"] = {}
    history["history"][today] = all_jobs
    history["results"] = results

    print("Scraped", len(all_jobs), "jobs")
    save_history(history)


if __name__ == "__main__":
    main()
