import requests
import os
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN = "8495081207:AAF1e5J8ki_y8WUrsQKLIPmfvy896HrnROw"
CHAT_ID = "-1003210356607"

# Test 1: Send simple message
print("Test 1: Sending simple message...")
response = requests.get(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    params={"chat_id": CHAT_ID, "text": "Test Message from Bot"}
)
result = response.json()
print(f"Success: {result.get('ok')}")
if not result.get('ok'):
    print(f"Error: {result.get('description')}")

# Test 2: Send message with buttons
print("\nTest 2: Sending message with buttons...")
buttons = {
    "inline_keyboard": [
        [
            {"text": "Button 1", "callback_data": "test1"},
            {"text": "Button 2", "callback_data": "test2"}
        ]
    ]
}
response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,
        "text": "🧪 Test with Buttons",
        "reply_markup": buttons
    }
)
print(f"Response: {response.json()}")

# Test 3: Get bot info
print("\nTest 3: Getting bot info...")
response = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe")
print(f"Bot Info: {response.json()}")

# Test 4: Get chat info
print("\nTest 4: Getting chat info...")
response = requests.get(
    f"https://api.telegram.org/bot{TOKEN}/getChat",
    params={"chat_id": CHAT_ID}
)
print(f"Chat Info: {response.json()}")
