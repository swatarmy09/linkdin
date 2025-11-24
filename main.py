import pandas as pd
from linkedin_bot import LinkedInBot
from website_analyzer import WebsiteAnalyzer
from telegram_notifier import TelegramNotifier
import time
import os
import sys

# CONFIGURATION
# ==========================================
# These will be overridden by Environment Variables if present
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8495081207:AAF1e5J8ki_y8WUrsQKLIPmfvy896HrnROw")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8495081207")
LINKEDIN_COOKIES = os.environ.get("LINKEDIN_COOKIES", None) # JSON string of cookies
# ==========================================

def process_leads(bot, analyzer, notifier, leads):
    processed_count = 0
    results = []
    
    for lead in leads:
        print(f"Processing {lead['name']}...")
        website = bot.get_profile_details(lead['profile_url'])
        
        lead_data = lead.copy()
        lead_data['website'] = website
        lead_data['website_status'] = "N/A"
        lead_data['website_score'] = 0
        lead_data['website_notes'] = ""
        
        is_target = False
        
        if website:
            print(f"  Found website: {website}")
            analysis = analyzer.analyze(website)
            lead_data['website_status'] = analysis['status']
            lead_data['website_score'] = analysis['score']
            lead_data['website_notes'] = "; ".join(analysis['details'])
            print(f"  Status: {analysis['status']} (Score: {analysis['score']})")
            
            if analysis['status'] in ['Bad', 'Potentially Bad'] or analysis['score'] < 50:
                is_target = True
        else:
            print("  No website found (High Potential)")
            lead_data['website_status'] = "No Website"
            lead_data['website_score'] = 0 
            is_target = True
        
        results.append(lead_data)
        
        if is_target:
            print("  >>> TARGET FOUND! Sending to Telegram...")
            notifier.send_lead(lead_data)
            processed_count += 1
            
    return results

def run_cycle():
    print(f"--- Starting Cycle at {time.ctime()} ---")
    
    # Force headless in production/loop mode
    bot = LinkedInBot(headless=True)
    analyzer = WebsiteAnalyzer()
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    try:
        # Pass cookies from env var if available
        bot.start(auth_content=LINKEDIN_COOKIES)
        bot.login()
        
        all_results = []
        
        print("\n--- Phase 1: Searching INDIA (Targeting ~40%) ---")
        leads_india = bot.search_leads("Founder New Startup", location_filter="India", pages=1)
        print(f"Found {len(leads_india)} leads in India.")
        results_india = process_leads(bot, analyzer, notifier, leads_india)
        all_results.extend(results_india)
        
        print("\n--- Phase 2: Searching GLOBAL (Targeting ~60%) ---")
        leads_global = bot.search_leads("Founder New Startup", location_filter="Global", pages=1)
        print(f"Found {len(leads_global)} leads Globally.")
        results_global = process_leads(bot, analyzer, notifier, leads_global)
        all_results.extend(results_global)
            
        if all_results:
            print(f"Cycle complete. Found {len(all_results)} leads.")
        else:
            print("Cycle complete. No leads found.")
            
    except Exception as e:
        print(f"An error occurred during cycle: {e}")
        # Send error to Telegram so user knows it crashed
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=⚠️ Bot Error: {str(e)}")
        except:
            pass
    finally:
        bot.close()

import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def main():
    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True)
    print("=== LinkedIn Lead Gen Bot (24/7 Cloud Mode) ===", flush=True)
    
    # Start dummy web server for Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Send startup message
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🚀 Bot Started on Render!")
    except:
        pass
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_cycle()
        return

    while True:
        run_cycle()
        
        # Sleep for 4 hours (14400 seconds)
        print("Sleeping for 4 hours...", flush=True)
        time.sleep(14400)

if __name__ == "__main__":
    main()
