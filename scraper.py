import requests, json, datetime, os, re, time
from bs4 import BeautifulSoup

HISTORY_FILE = "jobs_history.json"
OUTPUT_JSON  = "jobs.json"
DAYS_TO_KEEP = 30

# (Include your scraping functions here, same as before with Indeed/JSFirm/PilotsGlobal etc.)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_history(h):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(h, f, indent=2)

def main():
    today = datetime.date.today().isoformat()
    history = load_history()
    jobs, counts = scrape_all_sites()
    history[today] = jobs

    # keep only last 30 days
    cutoff = datetime.date.today() - datetime.timedelta(days=DAYS_TO_KEEP)
    history = {d: j for d, j in history.items() if datetime.date.fromisoformat(d) >= cutoff}

    save_history(history)

    # Save combined JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"today": jobs, "history": history}, f, indent=2)

    print(f"Saved {len(jobs)} jobs for {today}, source counts: {counts}")

if __name__ == "__main__":
    main()
