import requests

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_lead(self, lead_data):
        """
        Formats and sends a lead to Telegram.
        """
        if not self.token or not self.chat_id:
            print("Telegram token or chat ID missing. Skipping notification.")
            return

        message = (
            f"🚀 **New Lead Found!**\n\n"
            f"👤 **Name:** {lead_data.get('name', 'N/A')}\n"
            f"💼 **Title:** {lead_data.get('title', 'N/A')}\n"
            f"📍 **Location:** {lead_data.get('location', 'N/A')}\n"
            f"🔗 **LinkedIn:** {lead_data.get('profile_url', 'N/A')}\n\n"
            f"🌐 **Website Status:** {lead_data.get('website_status', 'N/A')}\n"
            f"🔗 **Website:** {lead_data.get('website', 'N/A')}\n"
            f"📝 **Notes:** {lead_data.get('website_notes', '')}\n"
        )

        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(self.base_url, json=payload)
            if response.status_code != 200:
                print(f"Failed to send Telegram message: {response.text}")
        except Exception as e:
            print(f"Error sending Telegram message: {e}")

if __name__ == "__main__":
    # Test
    # Replace with real values to test
    notifier = TelegramNotifier("YOUR_TOKEN", "YOUR_CHAT_ID")
    notifier.send_lead({"name": "Test User", "title": "CEO", "website_status": "No Website"})
