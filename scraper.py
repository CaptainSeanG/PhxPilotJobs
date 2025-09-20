import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from playwright.sync_api import sync_playwright

HEADERS = {"User-Agent": "Mozilla/5.0"}

# helper for detecting plane tags
def detect_plane_tags(text):
    t = text.lower()
    tags = []
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
    return tags

# helper for detecting hours requirement
def extract_hours_requirement(text):
    """Return the hours number if job says something like '1100 hours', '<= 1100', etc."""
    t = text.lower()
    import re
    # look for pattern like "1000 hours", "1100 hours", maybe "<= 1100", "1100 or less"
    matches = re.findall(r"(\d{3,4})\s*hours", t)
    if matches:
        # convert to int
        hrs = [int(m) for m in matches]
        # take the smallest found
        return min(hrs)
    # also check for phrases like "1100 or less", "1000 or fewer"
    m2 = re.search(r"(\d{3,4})\s*(?:or less|or fewer|<=)", t)
    if m2:
        return int(m2.group(1))
    return None

def scrape_pilotcareercenter():
    """Scrape NEW-PILOTS and ALL-JOBS pages, filter for <=1100 hours and your plane types."""
    base = "https://pilotcareercenter.com"
    urls = [
        base + "/NEW-PILOTS/USA",
        base + "/PILOT-JOB-NAVIGATOR/USA/All-Jobs"
    ]
    jobs = []
    results = {"status": "fail", "count": 0}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            for url in urls:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(5000)

                # find job link elements; you may need to inspect their actual selectors 
                anchors = page.locator("a").all()
                for a in anchors:
                    text = a.inner_text().strip()
                    href = a.get_attribute("href") or ""
                    # Skip if no text or no link
                    if not text or not href:
                        continue

                    # apply plane filter
                    plane_tags = detect_plane_tags(text)
                    if not plane_tags:
                        continue

                    # check hours requirement if mentioned
                    hrs = extract_hours_requirement(text)
                    if hrs is not None and hrs <= 1100:
                        jobs.append({
                            "title": text,
                            "company": "PilotCareerCenter",
                            "link": (base + href) if href.startswith("/") else href,
                            "source": "PilotCareerCenter",
                            "tags": plane_tags,
                            "hours_required": hrs
                        })
                    # if hours not mentioned, maybe include? you can decide
                    # else:
                    #     jobs.append(...)  # uncomment if you want those too

            browser.close()
        results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping PilotCareerCenter:", e)
    return jobs, results


# Other scrapers unchanged except they also use plane_tags if you want

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
                if not text:
                    continue
                plane_tags = detect_plane_tags(text)
                if not plane_tags:
                    continue

                # check hours maybe from text if possible
                hrs = extract_hours_requirement(text)
                if hrs is not None and hrs <= 1100:
                    link_full = href if href.startswith("http") else "https://skywest.com" + href
                    jobs.append({
                        "title": text,
                        "company": "SkyWest",
                        "link": link_full,
                        "source": "SkyWest",
                        "tags": plane_tags,
                        "hours_required": hrs
                    })
                else:
                    # optionally include if hours not mentioned
                    # jobs.append(...) 
                    pass
            results = {"status": "success", "count": len(jobs)}
    except Exception as e:
        print("Error scraping SkyWest:", e)
    return jobs, results

# include other scrapers similarly

def save_history(history):
    with open("jobs.json", "w") as f:
        json.dump(history, f, indent=2)
    with open("jobs_history.json", "w") as f:
        json.dump(history, f, indent=2)

def load_history():
    try:
        with open("jobs.json", "r") as f:
            return json.load(f)
    except:
        return {"today": [], "history": {}, "results": {}}

def main():
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")

    all_jobs = []
    results = {}

    # execute scrapers
    pcc_jobs, pcc_res = scrape_pilotcareercenter()
    all_jobs.extend(pcc_jobs)
    results["PilotCareerCenter"] = pcc_res

    skw_jobs, skw_res = scrape_skywest()
    all_jobs.extend(skw_jobs)
    results["SkyWest"] = skw_res

    # optionally include other sources with similar filtering

    history["today"] = all_jobs
    if "history" not in history:
        history["history"] = {}
    history["history"][today] = all_jobs
    history["results"] = results

    print("Scraped", len(all_jobs), "jobs meeting filters")
    save_history(history)

if __name__ == "__main__":
    main()
