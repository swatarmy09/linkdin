import pandas as pd
from linkedin_bot import LinkedInBot
from website_analyzer import WebsiteAnalyzer
from telegram_notifier import TelegramNotifier
import time
import os
import sys
import requests

# CONFIGURATION
# ==========================================
# These will be overridden by Environment Variables if present
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8495081207:AAF1e5J8ki_y8WUrsQKLIPmfvy896HrnROw")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1003210356607")
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
    print(f"--- Starting Cycle at {time.ctime()} ---", flush=True)
    
    # Send cycle start message
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🔄 New Search Cycle Started at {time.strftime('%H:%M:%S')}")
    except:
        pass
    
    # Force headless in production/loop mode
    bot = LinkedInBot(headless=True)
    analyzer = WebsiteAnalyzer()
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    try:
        # Send browser launch message
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🌐 Launching browser...")
        except:
            pass
            
        # Pass cookies from env var if available
        bot.start(auth_content=LINKEDIN_COOKIES)
        
        # Send login message
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🔐 Logging into LinkedIn...")
        except:
            pass
            
        bot.login()
        
        # Send login success
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=✅ LinkedIn Login Successful!")
        except:
            pass
        
        all_results = []
        
        print("\n--- Phase 1: Searching INDIA (Targeting ~40%) ---", flush=True)
        
        # Send search start message
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🔍 Searching for 'Founder New Startup' in India...")
        except:
            pass
            
        leads_india = bot.search_leads("Founder New Startup", location_filter="India", pages=1)
        print(f"Found {len(leads_india)} leads in India.", flush=True)
        
        # Send update
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🇮🇳 Found {len(leads_india)} profiles in India. Checking websites...")
        except:
            pass
            
        results_india = process_leads(bot, analyzer, notifier, leads_india)
        all_results.extend(results_india)
        
        print("\n--- Phase 2: Searching GLOBAL (Targeting ~60%) ---", flush=True)
        
        # Send search start message
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🔍 Searching for 'Founder New Startup' Globally...")
        except:
            pass
            
        leads_global = bot.search_leads("Founder New Startup", location_filter="Global", pages=1)
        print(f"Found {len(leads_global)} leads Globally.", flush=True)
        
        # Send update
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🌍 Found {len(leads_global)} profiles Globally. Checking websites...")
        except:
            pass
            
        results_global = process_leads(bot, analyzer, notifier, leads_global)
        all_results.extend(results_global)
            
        if all_results:
            print(f"Cycle complete. Found {len(all_results)} leads.", flush=True)
            # Send completion message
            try:
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=✅ Cycle Complete! Checked {len(all_results)} total profiles.")
            except:
                pass
        else:
            print("Cycle complete. No leads found.", flush=True)
            
    except Exception as e:
        print(f"An error occurred during cycle: {e}", flush=True)
        # Send error to Telegram so user knows it crashed
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=⚠️ Bot Error: {str(e)}")
        except:
            pass
    finally:
        bot.close()
        # Send browser close message
        try:
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text=🔴 Browser closed. Waiting 4 hours for next cycle...")
        except:
            pass

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
