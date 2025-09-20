import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from playwright.sync_api import sync_playwright

HEADERS = {"User-Agent": "Mozilla/5.0"}

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

def extract_hours(text):
    text_l = text.lower()
    import re
    # try match patterns like "1100 hours", "1000 hours", etc.
    m = re.findall(r"(\d{3,4})\s*hours", text_l)
    if m:
        nums = [int(x) for x in m]
        return min(nums)
    # match things like "1100 or less", "<=1100", etc.
    m2 = re.search(r"(\d{3,4})\s*(?:or less|or fewer|<=)", text_l)
    if m2:
        return int(m2.group(1))
    return None

def scrape_pilotcareercenter():
    urls = [
        "https://pilotcareercenter.com/NEW-PILOTS/USA",
        "https://pilotcareercenter.com/PILOT-JOB-NAVIGATOR/USA/All-Jobs"
    ]
    all_jobs = []
    results = {"status": "fail", "count": 0}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            scraped_total = 0
            kept_total = 0

            for url in urls:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(5000)

                anchors = page.locator("a").all()
                for a in anchors:
                    text = a.inner_text().strip()
                    href = a.get_attribute("href") or ""
                    if not text or not href:
                        continue
                    scraped_total += 1

                    plane_tags = detect_plane_tags(text)
                    if not plane_tags:
                        continue

                    hrs = extract_hours(text)
                    if hrs is None or hrs <= 1100:
                        kept_total += 1
                        all_jobs.append({
                            "title": text,
                            "company": "PilotCareerCenter",
                            "link": href if href.startswith("http") else "https://pilotcareercenter.com" + href,
                            "source": "PilotCareerCenter",
                            "tags": plane_tags,
                            "hours_required": hrs
                        })

            browser.close()
            print(f"PCC scraped_total: {scraped_total}, kept_total: {kept_total}")
            results = {"status": "success", "count": kept_total}
    except Exception as e:
        print("Error scraping PilotCareerCenter:", e)
    return all_jobs, results

def scrape_pilotsglobal():
    url = "https://pilotsglobal.com/jobs?a%5B%5D=9180aea7d6&jtc%5B%5D=vD5hZKX3ml&lc%5B%5D=04dba4cc2f&rt%5B%5D=fc12f7cb47"
    jobs = []
    results = {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # find job entries
            # Based on inspection, jobs are listed in <a> tags with job titles + other info
            listings = soup.select("a")
            scraped = 0
            kept = 0
            for l in listings:
                text = l.get_text(strip=True)
                href = l.get("href", "")
                if not text or not href:
                    continue
                scraped += 1

                plane_tags = detect_plane_tags(text)
                if not plane_tags:
                    continue

                hrs = extract_hours(text)
                if hrs is None or hrs <= 1100:
                    kept += 1
                    jobs.append({
                        "title": text,
                        "company": "PilotsGlobal",
                        "link": href if href.startswith("http") else "https://pilotsglobal.com" + href,
                        "source": "PilotsGlobal",
                        "tags": plane_tags,
                        "hours_required": hrs
                    })
            print(f"PilotsGlobal scraped: {scraped}, kept: {kept}")
            results = {"status": "success", "count": kept}
    except Exception as e:
        print("Error scraping PilotsGlobal:", e)
    return jobs, results

def scrape_skywest():
    url = "https://skywest.com/skywest-airline-jobs/"
    jobs = []
    results = {"status": "fail", "count": 0}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.find_all("a")
            scraped = 0
            kept = 0
            for l in listings:
                text = l.get_text(strip=True)
                href = l.get("href", "")
                if not text or not href:
                    continue
                scraped += 1

                plane_tags = detect_plane_tags(text)
                if not plane_tags:
                    continue

                hrs = extract_hours(text)
                if hrs is None or hrs <= 1100:
                    kept += 1
                    jobs.append({
                        "title": text,
                        "company": "SkyWest",
                        "link": href if href.startswith("http") else "https://skywest.com" + href,
                        "source": "SkyWest",
                        "tags": plane_tags,
                        "hours_required": hrs
                    })
            print(f"SkyWest scraped: {scraped}, kept: {kept}")
            results = {"status": "success", "count": kept}
    except Exception as e:
        print("Error scraping SkyWest:", e)
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
    except Exception:
        return {"today": [], "history": {}, "results": {}}

def main():
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")

    all_jobs = []
    results = {}

    # run the scrapers
    pcc_jobs, pcc_res = scrape_pilotcareercenter()
    all_jobs.extend(pcc_jobs)
    results["PilotCareerCenter"] = pcc_res

    pg_jobs, pg_res = scrape_pilotsglobal()
    all_jobs.extend(pg_jobs)
    results["PilotsGlobal"] = pg_res

    skw_jobs, skw_res = scrape_skywest()
    all_jobs.extend(skw_jobs)
    results["SkyWest"] = skw_res

    history["today"] = all_jobs
    if "history" not in history:
        history["history"] = {}
    history["history"][today] = all_jobs
    history["results"] = results

    print(f"Total jobs scraped: {len(all_jobs)}")
    save_history(history)

if __name__ == "__main__":
    main()
