import pandas as pd
from producthunt_bot import ProductHuntBot
from website_analyzer import WebsiteAnalyzer
from telegram_notifier import TelegramNotifier
from telegram_bot import TelegramBot
import time
import os
import sys
import requests
import threading
from flask import Flask

# CONFIGURATION
# ==========================================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8495081207:AAF1e5J8ki_y8WUrsQKLIPmfvy896HrnROw")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1003210356607")
PRODUCTHUNT_COOKIES = os.environ.get("PRODUCTHUNT_COOKIES", None)
# ==========================================

# Global state
bot_state = {
    "paused": False,
    "total_cycles": 0,
    "total_leads_found": 0,
    "last_cycle_time": None,
    "force_run": False
}

def process_products(bot, analyzer, notifier, products):
    """Process Product Hunt launches and identify leads"""
    results = []
    
    for product in products:
        print(f"Processing {product['name']}...", flush=True)
        
        # Get detailed product info
        details = bot.get_product_details(product['url'])
        
        if not details:
            continue
        
        lead_data = {
            'name': details['name'],
            'tagline': product.get('tagline', ''),
            'product_url': details['url'],
            'website': details.get('website'),
            'makers': details.get('makers', []),
            'twitter': details.get('twitter'),
            'linkedin': details.get('linkedin'),
            'facebook': details.get('facebook'),
            'instagram': details.get('instagram'),
            'email': details.get('email'),
            'website_status': 'N/A',
            'website_score': 0,
            'website_notes': ''
        }
        
        is_target = False
        
        if details.get('website'):
            print(f"  Found website: {details['website']}", flush=True)
            analysis = analyzer.analyze(details['website'])
            lead_data['website_status'] = analysis['status']
            lead_data['website_score'] = analysis['score']
            lead_data['website_notes'] = "; ".join(analysis['details'])
            print(f"  Status: {analysis['status']} (Score: {analysis['score']})", flush=True)
            
            if analysis['status'] in ['Bad', 'Potentially Bad'] or analysis['score'] < 50:
                is_target = True
        else:
            print("  No website found (High Potential Lead!)", flush=True)
            lead_data['website_status'] = "No Website"
            lead_data['website_score'] = 0
            is_target = True
        
        results.append(lead_data)
        
        if is_target:
            print("  >>> TARGET FOUND! Sending to Telegram...", flush=True)
            
            # Format makers info
            makers_text = ""
            for i, maker in enumerate(lead_data['makers'], 1):
                makers_text += f"\n**Maker {i}:** {maker['name']}"
                if maker.get('profile_url'):
                    makers_text += f"\n  - Product Hunt: {maker['profile_url']}"
                if maker.get('twitter'):
                    makers_text += f"\n  - Twitter: {maker['twitter']}"
                if maker.get('linkedin'):
                    makers_text += f"\n  - LinkedIn: {maker['linkedin']}"
                if maker.get('website'):
                    makers_text += f"\n  - Website: {maker['website']}"
                if maker.get('email'):
                    makers_text += f"\n  - Email: {maker['email']}"
                makers_text += "\n"
            
            # Build social links section
            social_links = []
            if lead_data.get('twitter'):
                social_links.append(f"Twitter: {lead_data['twitter']}")
            if lead_data.get('linkedin'):
                social_links.append(f"LinkedIn: {lead_data['linkedin']}")
            if lead_data.get('facebook'):
                social_links.append(f"Facebook: {lead_data['facebook']}")
            if lead_data.get('instagram'):
                social_links.append(f"Instagram: {lead_data['instagram']}")
            if lead_data.get('email'):
                social_links.append(f"Email: {lead_data['email']}")
            
            social_text = "\n".join(social_links) if social_links else "No social links found"
            
            # Format message for Telegram
            message = f"""
🚀 **NEW LEAD - Product Hunt**

**Product:** {lead_data['name']}
**Tagline:** {lead_data['tagline']}
**Product Hunt:** {lead_data['product_url']}

**📱 Product Social Links:**
{social_text}

**👥 Founders/Makers:**{makers_text}

**🌐 Website Analysis:**
**Status:** {lead_data['website_status']}
**URL:** {lead_data.get('website') or 'None'}
**Score:** {lead_data['website_score']}/100
**Notes:** {lead_data['website_notes'] or 'No website - perfect opportunity to offer your services!'}

---
💡 **Action:** Contact the makers and offer website development services!
"""
            notifier.send_message(message)
            time.sleep(1)
    
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
    
    telegram_bot.send_status_with_buttons(
        f"🔄 *Cycle #{bot_state['total_cycles']} Started*\n"
        f"⏰ Time: {time.strftime('%H:%M:%S')}\n"
        f"📊 Total Leads Found So Far: {bot_state['total_leads_found']}"
    )
    
    ph_bot = ProductHuntBot(headless=True)
    analyzer = WebsiteAnalyzer()
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    try:
        telegram_bot.send_message("🌐 Launching browser...")
        ph_bot.start(auth_content=PRODUCTHUNT_COOKIES)
        
        telegram_bot.send_message("🔍 Scraping Product Hunt launches...")
        products = ph_bot.get_daily_launches()
        print(f"Found {len(products)} products.", flush=True)
        
        telegram_bot.send_message(f"🎯 Found {len(products)} products. Analyzing websites...")
        results = process_products(ph_bot, analyzer, notifier, products)
        
        target_leads = [r for r in results if r.get('website_status') in ['No Website', 'Bad', 'Potentially Bad']]
        bot_state['total_leads_found'] += len(target_leads)
            
        if results:
            print(f"Cycle complete. Analyzed {len(results)} products.", flush=True)
            telegram_bot.send_status_with_buttons(
                f"✅ *Cycle #{bot_state['total_cycles']} Complete!*\n\n"
                f"📊 Analyzed: {len(results)} products\n"
                f"🎯 Target Leads: {len(target_leads)}\n"
                f"📈 Total Leads Found: {bot_state['total_leads_found']}\n"
                f"⏰ Next cycle in 4 hours"
            )
        else:
            print("Cycle complete. No products found.", flush=True)
            
    except Exception as e:
        print(f"An error occurred during cycle: {e}", flush=True)
        telegram_bot.send_message(f"⚠️ *Bot Error in Cycle #{bot_state['total_cycles']}*\n\n`{str(e)}`")
    finally:
        ph_bot.close()
        telegram_bot.send_message("🔴 Browser closed. Waiting 4 hours for next cycle...")

app = Flask(__name__)

@app.route('/')
def home():
    return "Product Hunt Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def listen_for_commands():
    global bot_state
    telegram_bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    while True:
        try:
            updates = telegram_bot.get_updates()
            
            for update in updates:
                telegram_bot.last_update_id = update.get("update_id", 0)
                
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
    
    sys.stdout.reconfigure(line_buffering=True)
    print("=== Product Hunt Lead Gen Bot (24/7 Cloud Mode) ===", flush=True)
    
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=listen_for_commands, daemon=True).start()
    
    telegram_bot = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    telegram_bot.send_status_with_buttons(
        "🚀 *Product Hunt Bot Started on Render!*\n\n"
        "Scraping daily launches for potential clients."
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_cycle()
        return

    while True:
        if bot_state["force_run"]:
            bot_state["force_run"] = False
            run_cycle()
        else:
            run_cycle()
        
        print("Sleeping for 4 hours...", flush=True)
        
        for _ in range(1440):
            if bot_state["force_run"]:
                print("Force run requested, breaking sleep...", flush=True)
                break
            time.sleep(10)

if __name__ == "__main__":
    main()
