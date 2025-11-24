import requests
from bs4 import BeautifulSoup
import urllib3

# Disable warnings for self-signed certs if we decide to allow them (optional)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebsiteAnalyzer:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def analyze(self, url):
        """
        Analyzes a website and returns a dictionary with status and details.
        """
        if not url.startswith('http'):
            url = 'https://' + url

        result = {
            'url': url,
            'status': 'Unknown', # Good, Bad, Error
            'details': [],
            'score': 0 # 0-100, lower is "worse" (which is what we want)
        }

        try:
            response = requests.get(url, headers=self.headers, timeout=10, verify=False) # verify=False to catch bad SSL too
            
            # Check Status Code
            if response.status_code >= 400:
                result['status'] = 'Bad'
                result['details'].append(f"HTTP Error: {response.status_code}")
                result['score'] = 10
                return result

            # Check for SSL (if we requested https and got it)
            if url.startswith('https') and response.url.startswith('http:'):
                 result['details'].append("Redirected to HTTP (Insecure)")
                 result['score'] -= 20

            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = soup.get_text().lower()

            # Heuristics for "Bad" or "New" websites
            bad_keywords = ['coming soon', 'under construction', 'domain for sale', 'buy this domain', 'wordpress default', 'lorem ipsum']
            
            found_keywords = [kw for kw in bad_keywords if kw in text_content]
            if found_keywords:
                result['status'] = 'Bad'
                result['details'].append(f"Found placeholder text: {', '.join(found_keywords)}")
                result['score'] -= 50

            # Check content length (very short pages might be empty)
            if len(text_content) < 200:
                result['status'] = 'Bad'
                result['details'].append("Very little content on page")
                result['score'] -= 30

            # Title check
            if not soup.title or not soup.title.string:
                 result['details'].append("Missing title tag")
                 result['score'] -= 10
            elif 'test' in soup.title.string.lower() or 'home' == soup.title.string.lower().strip():
                 result['details'].append("Generic title tag")
                 result['score'] -= 10

            if result['score'] <= 50 and result['status'] == 'Unknown':
                result['status'] = 'Potentially Bad'
            elif result['status'] == 'Unknown':
                result['status'] = 'Good'
                result['score'] = 80 # Default good score

        except requests.exceptions.RequestException as e:
            result['status'] = 'Bad'
            result['details'].append(f"Connection Error: {str(e)}")
            result['score'] = 0
        
        return result

if __name__ == "__main__":
    # Test
    analyzer = WebsiteAnalyzer()
    print(analyzer.analyze("example.com"))
    print(analyzer.analyze("http://nonexistentwebsite12345.com"))
