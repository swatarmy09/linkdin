import requests
import threading
import time

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.last_update_id = 0
        
    def send_message(self, text, buttons=None):
        """Send a message with optional inline buttons"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        if buttons:
            keyboard = {"inline_keyboard": buttons}
            payload["reply_markup"] = keyboard
            
        try:
            response = requests.post(url, json=payload)
            return response.json()
        except Exception as e:
            print(f"Error sending message: {e}")
            return None
    
    def send_status_with_buttons(self, status_text):
        """Send status message with control buttons"""
        buttons = [
            [
                {"text": "▶️ Start Cycle Now", "callback_data": "start_cycle"},
                {"text": "📊 Get Status", "callback_data": "get_status"}
            ],
            [
                {"text": "📈 View Stats", "callback_data": "view_stats"},
                {"text": "⏸️ Pause Bot", "callback_data": "pause_bot"}
            ]
        ]
        self.send_message(status_text, buttons)
    
    def get_updates(self):
        """Get pending updates from Telegram"""
        url = f"{self.base_url}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 30}
        
        try:
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            
            if data.get("ok"):
                return data.get("result", [])
        except Exception as e:
            print(f"Error getting updates: {e}")
        
        return []
    
    def process_callback(self, callback_data):
        """Process button clicks"""
        return callback_data
