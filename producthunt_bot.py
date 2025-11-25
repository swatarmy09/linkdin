from playwright.sync_api import sync_playwright
import time
import random
import json
import os

class ProductHuntBot:
    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.auth_file = "ph_auth.json"
        
    def start(self, auth_content=None):
        """Initialize browser with optional authentication"""
        print("Initializing Product Hunt bot...", flush=True)
        self.playwright = sync_playwright().start()
        
        # Load authentication if available
        storage_state = None
        if auth_content:
            try:
                cookies = json.loads(auth_content)
                storage_state = {"cookies": cookies, "origins": []}
                print("Loaded authentication from environment.", flush=True)
            except:
                print("Warning: Could not parse PRODUCTHUNT_COOKIES.", flush=True)
        elif os.path.exists(self.auth_file):
            storage_state = self.auth_file
            print("Loaded saved authentication.", flush=True)
        
        # Launch browser
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.page = self.context.new_page()
        
    def get_daily_launches(self, date=None):
        """
        Scrape products launched on Product Hunt.
        If date is None, gets today's launches.
        """
        print("Fetching Product Hunt launches...", flush=True)
        
        # Navigate to Product Hunt
        url = "https://www.producthunt.com"
        if date:
            url += f"?date={date}"
            
        self.page.goto(url, wait_until="domcontentloaded")
        time.sleep(random.uniform(3, 5))
        
        products = []
        
        try:
            # Scroll to load more products
            for _ in range(3):
                self.page.evaluate("window.scrollBy(0, 1000)")
                time.sleep(random.uniform(1, 2))
            
            # Find all product cards
            product_elements = self.page.query_selector_all('[data-test="post-item"]')
            
            if not product_elements:
                # Fallback selector
                product_elements = self.page.query_selector_all('article')
            
            print(f"Found {len(product_elements)} products on the page.", flush=True)
            
            for element in product_elements[:20]:  # Limit to top 20
                try:
                    # Extract product link
                    link_elem = element.query_selector('a[href^="/posts/"]')
                    if not link_elem:
                        continue
                        
                    product_url = "https://www.producthunt.com" + link_elem.get_attribute('href')
                    
                    # Extract product name
                    name_elem = element.query_selector('h3, strong')
                    product_name = name_elem.inner_text() if name_elem else "Unknown"
                    
                    # Extract tagline
                    tagline_elem = element.query_selector('[class*="tagline"], p')
                    tagline = tagline_elem.inner_text() if tagline_elem else ""
                    
                    products.append({
                        'name': product_name.strip(),
                        'tagline': tagline.strip(),
                        'url': product_url
                    })
                    
                except Exception as e:
                    print(f"Error extracting product: {e}", flush=True)
                    continue
            
            print(f"Successfully extracted {len(products)} products.", flush=True)
            
        except Exception as e:
            print(f"Error fetching launches: {e}", flush=True)
        
        return products
    
    def get_product_details(self, product_url):
        """Extract detailed information from a product page"""
        print(f"Fetching details for: {product_url}", flush=True)
        
        try:
            self.page.goto(product_url, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))
            
            details = {
                'url': product_url,
                'name': '',
                'description': '',
                'website': None,
                'makers': [],
                'twitter': None
            }
            
            # Get product name
            name_elem = self.page.query_selector('h1')
            if name_elem:
                details['name'] = name_elem.inner_text().strip()
            
            # Get description
            desc_elem = self.page.query_selector('[data-test="product-description"], .description, p')
            if desc_elem:
                details['description'] = desc_elem.inner_text().strip()
            
            # Get website link
            website_elem = self.page.query_selector('a[data-test="product-website"], a[href*="http"]:has-text("Visit")')
            if website_elem:
                details['website'] = website_elem.get_attribute('href')
            
            # Get makers
            maker_elements = self.page.query_selector_all('[data-test="makers-list"] a, .makers a')
            for maker_elem in maker_elements[:3]:  # Limit to 3 makers
                maker_name = maker_elem.inner_text().strip()
                maker_url = maker_elem.get_attribute('href')
                if maker_url and not maker_url.startswith('http'):
                    maker_url = "https://www.producthunt.com" + maker_url
                    
                details['makers'].append({
                    'name': maker_name,
                    'profile_url': maker_url
                })
            
            # Get Twitter link
            twitter_elem = self.page.query_selector('a[href*="twitter.com"], a[href*="x.com"]')
            if twitter_elem:
                details['twitter'] = twitter_elem.get_attribute('href')
            
            return details
            
        except Exception as e:
            print(f"Error getting product details: {e}", flush=True)
            return None
    
    def close(self):
        """Close browser"""
        if self.context:
            try:
                self.context.storage_state(path=self.auth_file)
            except:
                pass
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
