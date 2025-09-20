import requests
from bs4 import BeautifulSoup
import feedparser
import json
from datetime import datetime
import os

# ---------- Tag Detection ----------
def detect_tags(title):
    tags = []
    t = title.lower()
    if "caravan" in t or "cessna 208" in t:
        tags.append("Caravan")
    if "pc-12" in t or "pc12" in t or "pilatus" in t:
        tags.append("PC-12")
    if "king air" in t:
        tags.append("King Air")
    if "baron" in t:
        tags.append("Baron")
    if "navajo" in t:
        tags.append("Navajo")
    if "sky courier" in t or "skycourier" in t:
        tags.append("SkyCourier")
    if "part 91" in t:
        tags.append("Part 91")
    return tags

# ---------- Scrapers ----------
def scrape_indeed_rss(results):
    url = "https://www.indeed.com/rss?q=pilot&l=Phoenix%2C+AZ"
    jobs = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            jobs.append({
                "title": entry.title,
                "company": entry.get("author", "Unknown"),
                "link": entry.link,
                "source": "Indeed RSS",
                "tags": detect_tags(entry.title)
            })
        results["Indeed RSS"] = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Indeed RSS:", e)
        results["Indeed RSS"] = {"status": "fail", "count": 0}
    return jobs

def scrape_cutter(results):
    url = "https://cutteraviation.com/careers/"
    jobs = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("ul.job_listings li.job_listing a.job_listing-clickbox")

        for li in listings:
            title = li.get("title", "Pilot Job")
            link = li["href"]
            jobs.append({
                "title": title,
                "company": "Cutter Aviation",
                "link": link,
                "source": "Cutter Aviation",
                "tags": detect_tags(title)
            })
        results["Cutter Aviation"] = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Cutter Aviation:", e)
        results["Cutter Aviation"] = {"status": "fail", "count": 0}
    return jobs

def scrape_contour(results):
    url = "https://contouraviation.com/careers"
    jobs = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("a[href*='position']")

        for a in listings:
            title = a.get_text(strip=True)
            link = a["href"]
            if not link.startswith("http"):
                link = "https://contouraviation.com" + link
            jobs.append({
                "title": title,
                "company": "Contour Aviation",
                "link": link,
                "source": "Contour Aviation",
                "tags": detect_tags(title)
            })
        results["Contour Aviation"] = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Contour Aviation:", e)
        results["Contour Aviation"] = {"status": "fail", "count": 0}
    return jobs

def scrape_ameriflight(results):
    url = "https://www.ameriflight.com/careers/"
    jobs = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("a[href*='careers']")

        for a in listings:
            title = a.get_text(strip=True)
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.ameriflight.com" + link
            if "pilot" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "Ameriflight",
                    "link": link,
                    "source": "Ameriflight",
                    "tags": detect_tags(title)
                })
        results["Ameriflight"] = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Ameriflight:", e)
        results["Ameriflight"] = {"status": "fail", "count": 0}
    return jobs

def scrape_skywest(results):
    url = "https://www.skywest.com/skywest-airline-jobs/"
    jobs = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("a.jobTitle")

        for a in listings:
            title = a.get_text(strip=True)
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.skywest.com" + link
            if "pilot" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "SkyWest Airlines",
                    "link": link,
                    "source": "SkyWest",
                    "tags": detect_tags(title)
                })
        results["SkyWest"] = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping SkyWest:", e)
        results["SkyWest"] = {"status": "fail", "count": 0}
    return jobs

def scrape_boutique(results):
    url = "https://www.boutiqueair.com/pages/careers"
    jobs = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("a[href*='jobs']")

        for a in listings:
            title = a.get_text(strip=True)
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.boutiqueair.com" + link
            if "pilot" in title.lower():
                jobs.append({
                    "title": title,
                    "company": "Boutique Air",
                    "link": link,
                    "source": "Boutique Air",
                    "tags": detect_tags(title)
                })
        results["Boutique Air"] = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping Boutique Air:", e)
        results["Boutique Air"] = {"status": "fail", "count": 0}
    return jobs

# ---------- Save & Load History ----------
def load_history():
    if os.path.exists("jobs.json"):
        with open("jobs.json", "r") as f:
            return json.load(f)
    return {"today": [], "history": {}, "results": {}}

def save_history(data):
    with open("jobs.json", "w") as f:
        json.dump(data, f, indent=2)

# ---------- Main ----------
def main():
    all_jobs = []
    results = {}

    all_jobs.extend(scrape_indeed_rss(results))
    all_jobs.extend(scrape_cutter(results))
    all_jobs.extend(scrape_contour(results))
    all_jobs.extend(scrape_ameriflight(results))
    all_jobs.extend(scrape_skywest(results))
    all_jobs.extend(scrape_boutique(results))

    today = datetime.now().strftime("%Y-%m-%d")

    history = load_history()
    history["today"] = all_jobs
    history["history"][today] = all_jobs
    history["results"] = results

    # Keep only last 30 days of history
    dates = sorted(history["history"].keys(), reverse=True)
    for d in dates[30:]:
        del history["history"][d]

    save_history(history)
    print(f"Saved {len(all_jobs)} jobs for {today}")
    print("Scraper results:", results)

if __name__ == "__main__":
    main()
