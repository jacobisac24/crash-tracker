"""
BC.Game Crash - Cloud Linker v5.0
================================
Captures games and PUSHES them to your new Lovable website.
"""

import json
import csv
import sys
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

import os
CSV_FILENAME = "crash_history_log.csv"
INGEST_URL = "https://znqwnsxbiqpaioaprien.supabase.co/functions/v1/ingest-games"
# Priority 1: GitHub Secret | Priority 2: Hardcoded Key
INGEST_API_KEY = os.environ.get("INGEST_API_KEY") or "U-X#y4FSjAh/aft"
# ------------------------------------

all_records = {}

def get_now():
    return datetime.now().strftime("%H:%M:%S")

def load_existing():
    try:
        with open(CSV_FILENAME, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                gid = row.get('id')
                if gid:
                    all_records[gid] = {"time": row.get('time'), "mult": row.get('multiplier')}
    except FileNotFoundError:
        pass

def save_local():
    sorted_ids = sorted(all_records.keys(), key=lambda x: int(x) if x.isdigit() else 0, reverse=True)
    with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["id", "time", "multiplier"])
        for gid in sorted_ids:
            rec = all_records[gid]
            writer.writerow([gid, rec['time'], rec['mult']])

def push_to_cloud(new_games):
    """Sends the new games to your Lovable/Supabase website."""
    if not new_games:
        return
    
    print(f"[{get_now()}] Preparing to push {len(new_games)} games to the cloud...")
    
    # Format the data exactly how Lovable expects it
    payload = {
        "api_key": INGEST_API_KEY,
        "games": []
    }
    
    for gid, t, m in new_games:
        # Convert multiplier "2.50x" to number 2.50
        try:
            m_num = float(m.replace('x', ''))
        except:
            m_num = 0.0
            
        payload["games"].append({
            "id": gid,
            "time": t.replace(' ', 'T') + 'Z', # Convert to ISO format for Supabase
            "multiplier": m_num
        })

    try:
        response = requests.post(INGEST_URL, json=payload, timeout=15)
        if response.status_code == 200:
            print(f"[{get_now()}] CLOUD PUSH SUCCESSFUL! Website updated. ✅")
        else:
            print(f"[{get_now()}] CLOUD PUSH FAILED (Code {response.status_code}): {response.text} ❌")
    except Exception as e:
        print(f"[{get_now()}] CLOUD PUSH ERROR: {e} ❌")

def main():
    print("\n" + "="*45)
    print(" BC.GAME HISTORY SYNCER - v5.0")
    print("="*45)
    
    if INGEST_API_KEY == "PASTE_YOUR_SECRET_PASSWORD_HERE":
        print("[!] ERROR: You forgot to paste your Secret Password in the script!")
        return

    load_existing()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        new_games_list = [] # Store new ones to push later

        def on_response(response):
            if "bet/multi/history" in response.url:
                try:
                    data = response.json()
                    items = data.get("data", {}).get("list", [])
                    for item in items:
                        gid = str(item.get("gameId", ""))
                        if gid and gid not in all_records:
                            detail = json.loads(item.get("gameDetail", "{}"))
                            raw_time = detail.get("endTime") or detail.get("beginTime")
                            formatted_time = datetime.fromtimestamp(raw_time/1000).strftime("%Y-%m-%d %H:%M:%S") if raw_time else "N/A"
                            new_games_list.append((gid, formatted_time, f"{detail.get('rate')}x"))
                except:
                    pass

        page.on("response", on_response)
        
        try:
            print(f"[{get_now()}] Connecting to BC.Game...")
            page.goto("https://bc.game/game/crash", timeout=60000)
            page.wait_for_timeout(10000) 
        except Exception as e:
            print(f"[!] Connection failed: {e}")
            sys.exit(1)

        added = 0
        for gid, t, m in new_games_list:
            if gid not in all_records:
                all_records[gid] = {"time": t, "mult": m}
                added += 1

        if added > 0:
            save_local()
            push_to_cloud(new_games_list)
            print(f"[{get_now()}] Done. {added} games sync'd.")
        else:
            print(f"[{get_now()}] Dashboard is up to date.")

        browser.close()

if __name__ == "__main__":
    main()
