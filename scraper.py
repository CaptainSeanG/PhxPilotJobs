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

# ---------- Indeed via RSS ----------
def scrape_indeed_rss():
    url = "https://www.indeed.com/rss?q=pilot&l=Phoenix%2C+AZ"
    jobs = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            company = entry.get("author", "Unknown")
            jobs.append({
                "title": title,
                "company": company,
                "link": link,
                "source": "Indeed RSS",
                "tags": detect_tags(title)
            })
    except Exception as e:
        print("Error scraping Indeed RSS:", e)
    return jobs

# ---------- Cutter Aviation ----------
def scrape_cutter():
    url = "https://cutteraviation.com/careers/"
    jobs = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for li in soup.select("ul.job_listings li.job_listing a.job_listing-clickbox"):
            title = li.get("title", "Pilot Job")
            link = li["href"]
            company = "Cutter Aviation"
            jobs.append({
                "title": title,
                "company": company,
                "link": link,
                "source": "Cutter Aviation",
                "tags": detect_tags(title)
            })
    except Exception as e:
        print("Error scraping Cutter Aviation:", e)
    return jobs

# ---------- Contour Aviation ----------
def scrape_contour():
    url = "https://contouraviation.com/careers"
    jobs = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.select("a[href*='position']"):
            title = a.get_text(strip=True)
            link = a["href"]
            if not link.startswith("http"):
                link = "https://contouraviation.com" + link
            company = "Contour Aviation"
            jobs.append({
                "title": title,
                "company": company,
                "link": link,
                "source": "Contour Aviation",
                "tags": detect_tags(title)
            })
    except Exception as e:
        print("Error scraping Contour Aviation:", e)
    return jobs

# ---------- Ameriflight ----------
def scrape_ameriflight():
    url = "https://www.ameriflight.com/careers/"
    jobs = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.select("a[href*='careers']"):
            title = a.get_text(strip=True)
            link = a["href"]
            if not link.startswith("http"):
                link = "https://www.ameriflight.com" + link
            if "pilot" in title.lower():
                company = "Ameriflight"
                jobs.append({
                    "title": title,
                    "company": company,
                    "link": link,
                    "source": "Ameriflight",
                    "tags": detect_tags(title)
                })
    except Exception as e:
        print("Error scraping Ameriflight:", e)
    return jobs

# ---------- Save & Load History ----------
def load_history():
    if os.path.exists("jobs.json"):
        with open("jobs.json", "r") as f:
            return json.load(f)
    return {"today": [], "history": {}}

def save_history(data):
    with open("jobs.json", "w") as f:
        json.dump(data, f, indent=2)

# ---------- Main ----------
def main():
    all_jobs = []
    all_jobs.extend(scrape_indeed_rss())
    all_jobs.extend(scrape_cutter())
    all_jobs.extend(scrape_contour())
    all_jobs.extend(scrape_ameriflight())

    today = datetime.now().strftime("%Y-%m-%d")

    history = load_history()
    history["today"] = all_jobs
    history["history"][today] = all_jobs

    # Keep only last 30 days of history
    dates = sorted(history["history"].keys(), reverse=True)
    for d in dates[30:]:
        del history["history"][d]

    save_history(history)
    print(f"Saved {len(all_jobs)} jobs for {today}")

if __name__ == "__main__":
    main()
