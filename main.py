import pandas as pd
from linkedin_bot import LinkedInBot
from website_analyzer import WebsiteAnalyzer
from telegram_notifier import TelegramNotifier
from telegram_bot import TelegramBot
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

# Global state
bot_state = {
    "paused": False,
    "total_cycles": 0,
    "total_leads_found": 0,
    "last_cycle_time": None,
    "force_run": False
}

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
    global bot_state
    
    if bot_state["paused"]:
        print("Bot is paused. Skipping cycle.", flush=True)
        return
        
    bot_state["total_cycles"] += 1
    bot_state["last_cycle_time"] = time.strftime('%H:%M:%S')
    
    print(f"--- Starting Cycle #{bot_state['total_cycles']} at {time.ctime()} ---", flush=True)
    
    telegram_bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    # Send cycle start message with buttons
    telegram_bot.send_status_with_buttons(
        f"🔄 *Cycle #{bot_state['total_cycles']} Started*\n"
        f"⏰ Time: {time.strftime('%H:%M:%S')}\n"
        f"📊 Total Leads Found So Far: {bot_state['total_leads_found']}"
    )
    
    # Force headless in production/loop mode
    linkedin_bot = LinkedInBot(headless=True)
    analyzer = WebsiteAnalyzer()
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    try:
        # Send browser launch message
        telegram_bot.send_message("🌐 Launching browser...")
            
        # Pass cookies from env var if available
        linkedin_bot.start(auth_content=LINKEDIN_COOKIES)
        
        # Send login message
        telegram_bot.send_message("🔐 Logging into LinkedIn...")
            
        linkedin_bot.login()
        
        # Send login success
        telegram_bot.send_message("✅ LinkedIn Login Successful!")
        
        all_results = []
        
        print("\n--- Phase 1: Searching INDIA (Targeting ~40%) ---", flush=True)
        
        # Send search start message
        telegram_bot.send_message("🔍 Searching for 'Founder New Startup' in India...")
            
        leads_india = linkedin_bot.search_leads("Founder New Startup", location_filter="India", pages=1)
        print(f"Found {len(leads_india)} leads in India.", flush=True)
        
        # Send update
        telegram_bot.send_message(f"🇮🇳 Found {len(leads_india)} profiles in India. Checking websites...")
            
        results_india = process_leads(linkedin_bot, analyzer, notifier, leads_india)
        all_results.extend(results_india)
        
        print("\n--- Phase 2: Searching GLOBAL (Targeting ~60%) ---", flush=True)
        
        # Send search start message
        telegram_bot.send_message("🔍 Searching for 'Founder New Startup' Globally...")
            
        leads_global = linkedin_bot.search_leads("Founder New Startup", location_filter="Global", pages=1)
        print(f"Found {len(leads_global)} leads Globally.", flush=True)
        
        # Send update
        telegram_bot.send_message(f"🌍 Found {len(leads_global)} profiles Globally. Checking websites...")
            
        results_global = process_leads(linkedin_bot, analyzer, notifier, leads_global)
        all_results.extend(results_global)
        
        # Count target leads
        target_leads = [r for r in all_results if r.get('website_status') in ['No Website', 'Bad', 'Potentially Bad']]
        bot_state['total_leads_found'] += len(target_leads)
            
        if all_results:
            print(f"Cycle complete. Found {len(all_results)} leads.", flush=True)
            # Send completion message with buttons
            telegram_bot.send_status_with_buttons(
                f"✅ *Cycle #{bot_state['total_cycles']} Complete!*\n\n"
                f"📊 Checked: {len(all_results)} profiles\n"
                f"🎯 Target Leads: {len(target_leads)}\n"
                f"📈 Total Leads Found: {bot_state['total_leads_found']}\n"
                f"⏰ Next cycle in 4 hours"
            )
        else:
            print("Cycle complete. No leads found.", flush=True)
            
    except Exception as e:
        print(f"An error occurred during cycle: {e}", flush=True)
        # Send error to Telegram
        telegram_bot.send_message(f"⚠️ *Bot Error in Cycle #{bot_state['total_cycles']}*\n\n`{str(e)}`")
    finally:
        linkedin_bot.close()
        # Send browser close message
        telegram_bot.send_message("🔴 Browser closed. Waiting 4 hours for next cycle...")

import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def listen_for_commands():
    """Background thread to listen for Telegram button clicks"""
    global bot_state
    telegram_bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    while True:
        try:
            updates = telegram_bot.get_updates()
            
            for update in updates:
                telegram_bot.last_update_id = update.get("update_id", 0)
                
                # Handle button callbacks
                if "callback_query" in update:
                    callback = update["callback_query"]
                    data = callback.get("data")
                    
                    if data == "start_cycle":
                        bot_state["force_run"] = True
                        telegram_bot.send_message("▶️ Starting new cycle immediately...")
                        
                    elif data == "get_status":
                        status = (
                            f"📊 *Bot Status*\n\n"
                            f"🔄 Total Cycles: {bot_state['total_cycles']}\n"
                            f"🎯 Total Leads Found: {bot_state['total_leads_found']}\n"
                            f"⏰ Last Cycle: {bot_state['last_cycle_time'] or 'Not started'}\n"
                            f"⏸️ Paused: {'Yes' if bot_state['paused'] else 'No'}"
                        )
                        telegram_bot.send_status_with_buttons(status)
                        
                    elif data == "view_stats":
                        telegram_bot.send_message(
                            f"📈 *Detailed Statistics*\n\n"
                            f"Total Cycles Run: {bot_state['total_cycles']}\n"
                            f"Total Target Leads: {bot_state['total_leads_found']}\n"
                            f"Average per Cycle: {bot_state['total_leads_found'] / max(bot_state['total_cycles'], 1):.1f}"
                        )
                        
                    elif data == "pause_bot":
                        bot_state["paused"] = not bot_state["paused"]
                        status = "⏸️ Bot Paused" if bot_state["paused"] else "▶️ Bot Resumed"
                        telegram_bot.send_message(status)
                    
                    # Answer callback to remove loading state
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                        json={"callback_query_id": callback["id"]}
                    )
                    
        except Exception as e:
            print(f"Error in command listener: {e}", flush=True)
            time.sleep(5)
        
        time.sleep(2)

def main():
    global bot_state
    
    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True)
    print("=== LinkedIn Lead Gen Bot (24/7 Cloud Mode) ===", flush=True)
    
    # Start dummy web server for Render
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Start command listener
    threading.Thread(target=listen_for_commands, daemon=True).start()
    
    telegram_bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    # Send startup message with buttons
    telegram_bot.send_status_with_buttons(
        "🚀 *Bot Started on Render!*\n\n"
        "Use the buttons below to control the bot."
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_cycle()
        return

    while True:
        # Check if force run requested
        if bot_state["force_run"]:
            bot_state["force_run"] = False
            run_cycle()
        else:
            run_cycle()
        
        # Sleep for 4 hours (14400 seconds)
        print("Sleeping for 4 hours...", flush=True)
        
        # Sleep in small intervals to check for force_run
        for _ in range(1440):  # 1440 * 10 seconds = 4 hours
            if bot_state["force_run"]:
                print("Force run requested, breaking sleep...", flush=True)
                break
            time.sleep(10)

if __name__ == "__main__":
    main()
