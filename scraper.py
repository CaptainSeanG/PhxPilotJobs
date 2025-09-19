import os, re, json, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin

HISTORY_FILE = "jobs_history.json"
OUTPUT_FILE = "jobs.json"

AZ_TERMS = ["Arizona", "AZ", "Phoenix", "Scottsdale", "PHX"]

def fetch_url(url):
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=20,
        )
        resp.raise_for_status()
        return resp
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def save_debug_html(name, content):
    folder = "debug_html"
    os.makedirs(folder, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    path = os.path.join(folder, f"{safe_name}.html")
    with open(path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(content)
    print(f"[DEBUG] Saved raw HTML -> {path}")

# ✅ Indeed RSS feed
def scrape_indeed():
    jobs = []
    url = "https://rss.indeed.com/rss?q=pilot&l=Arizona"
    resp = fetch_url(url)
    if not resp:
        return jobs
    soup = BeautifulSoup(resp.text, "xml")
    for item in soup.find_all("item"):
        title = item.title.get_text()
        link = item.link.get_text()
        jobs.append({
            "title": title,
            "company": "Unknown",
            "link": link,
            "source": "Indeed",
            "tags": detect_tags(title),
        })
    print(f"Indeed: {len(jobs)} jobs found")
    return jobs

# 🔹 Ameriflight Careers
def scrape_ameriflight_careers():
    jobs = []
    url = "https://w3.ameriflight.com/pilots/careers/"
    resp = fetch_url(url)
    if not resp:
        return jobs
    soup = BeautifulSoup(resp.text, "html.parser")
    for link in soup.select("a"):
        title = link.get_text(strip=True)
        href = link.get("href")
        if not title or not href:
            continue
        if not href.startswith("http"):
            href = urljoin(url, href)
        text_blob = title + " " + href
        if not any(term.lower() in text_blob.lower() for term in AZ_TERMS):
            continue
        jobs.append({
            "title": title,
            "company": "Ameriflight",
            "link": href,
            "source": "Ameriflight",
            "tags": detect_tags(title),
        })
    print(f"Ameriflight: {len(jobs)} AZ jobs found")
    return jobs

# 🔹 Pilot Career Center (AZ jobs)
def scrape_pilotcareercenter_az():
    jobs = []
    url = "https://pilotcareercenter.com/AZ-Pilot-Jobs/Arizona"
    resp = fetch_url(url)
    if not resp:
        return jobs
    soup = BeautifulSoup(resp.text, "html.parser")
    for card in soup.select("a"):
        title = card.get_text(strip=True)
        href = card.get("href")
        if not title or not href:
            continue
        if not href.startswith("http"):
            href = urljoin(url, href)
        text_blob = title + " " + href
        if not any(term.lower() in text_blob.lower() for term in AZ_TERMS):
            continue
        jobs.append({
            "title": title,
            "company": "PilotCareerCenter",
            "link": href,
            "source": "PilotCareerCenter",
            "tags": detect_tags(title),
        })
    print(f"PCC: {len(jobs)} AZ jobs found")
    return jobs

# 🔹 JSFirm (still may block, but we try)
def scrape_jsfirm():
    jobs = []
    url = "https://www.jsfirm.com/pilot-jobs-in-Arizona/US/State-2"
    resp = fetch_url(url)
    if not resp:
        return jobs
    soup = BeautifulSoup(resp.text, "html.parser")
    for card in soup.select(".job-title"):
        title = card.get_text(strip=True)
        link = card.get("href", "#")
        if not link.startswith("http"):
            link = "https://www.jsfirm.com" + link
        jobs.append({
            "title": title,
            "company": "JSFirm",
            "link": link,
            "source": "JSFirm",
            "tags": detect_tags(title),
        })
    print(f"JSFirm: {len(jobs)} jobs found")
    return jobs

# Detect tags
def detect_tags(text):
    text = text.lower()
    tags = []
    if "caravan" in text or "208" in text: tags.append("Caravan")
    if "pc-12" in text or "pc12" in text or "pilatus" in text: tags.append("PC-12")
    if "sky courier" in text or "skycourier" in text: tags.append("SkyCourier")
    if "baron" in text: tags.append("Baron")
    if "navajo" in text: tags.append("Navajo")
    if "part 91" in text: tags.append("Part 91")
    return tags

# Filters
def filter_arizona(jobs):
    return [j for j in jobs if any(term.lower() in (j.get("title","") + j.get("company","")).lower() for term in AZ_TERMS)]

def deduplicate(jobs):
    seen, results = set(), []
    for j in jobs:
        key = (j["title"], j["company"], j["source"])
        if key not in seen:
            seen.add(key)
            results.append(j)
    return results

# History
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_history(history):
    cutoff = datetime.now() - timedelta(days=30)
    trimmed = {d: v for d,v in history.items() if datetime.fromisoformat(d) >= cutoff}
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(trimmed, f, indent=2)

def save_output(today_jobs, history):
    data = {"today": today_jobs, "history": history}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Main
def scrape_all_sites():
    all_jobs = []
    all_jobs.extend(scrape_indeed())
    all_jobs.extend(scrape_jsfirm())
    all_jobs.extend(scrape_ameriflight_careers())
    all_jobs.extend(scrape_pilotcareercenter_az())
    return all_jobs

def main():
    today = datetime.now().date().isoformat()
    history = load_history()
    jobs = scrape_all_sites()
    print(f"[INFO] Scraped {len(jobs)} raw jobs")
    jobs = filter_arizona(jobs)
    jobs = deduplicate(jobs)
    print(f"[INFO] {len(jobs)} after AZ filter & dedupe")
    history[today] = jobs
    save_history(history)
    save_output(jobs, history)

if __name__ == "__main__":
    main()
