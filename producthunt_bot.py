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
                'twitter': None,
                'linkedin': None,
                'facebook': None,
                'instagram': None,
                'email': None
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
            
            # Get all social links
            all_links = self.page.query_selector_all('a[href]')
            for link in all_links:
                href = link.get_attribute('href')
                if not href:
                    continue
                    
                # Twitter/X
                if 'twitter.com' in href or 'x.com' in href:
                    details['twitter'] = href
                # LinkedIn
                elif 'linkedin.com' in href:
                    details['linkedin'] = href
                # Facebook
                elif 'facebook.com' in href:
                    details['facebook'] = href
                # Instagram
                elif 'instagram.com' in href:
                    details['instagram'] = href
                # Email
                elif href.startswith('mailto:'):
                    details['email'] = href.replace('mailto:', '')
            
            # Get makers with their profiles
            maker_elements = self.page.query_selector_all('[data-test="makers-list"] a, .makers a')
            for maker_elem in maker_elements[:3]:  # Limit to 3 makers
                maker_name = maker_elem.inner_text().strip()
                maker_url = maker_elem.get_attribute('href')
                if maker_url and not maker_url.startswith('http'):
                    maker_url = "https://www.producthunt.com" + maker_url
                
                # Get maker details
                maker_info = self.get_maker_details(maker_url) if maker_url else {}
                    
                details['makers'].append({
                    'name': maker_name,
                    'profile_url': maker_url,
                    'twitter': maker_info.get('twitter'),
                    'linkedin': maker_info.get('linkedin'),
                    'website': maker_info.get('website'),
                    'email': maker_info.get('email')
                })
            
            return details
            
        except Exception as e:
            print(f"Error getting product details: {e}", flush=True)
            return None
    
    def get_maker_details(self, maker_url):
        """Extract contact details from maker's profile"""
        try:
            self.page.goto(maker_url, wait_until="domcontentloaded")
            time.sleep(random.uniform(1, 2))
            
            maker_info = {
                'twitter': None,
                'linkedin': None,
                'website': None,
                'email': None
            }
            
            # Get all links from profile
            all_links = self.page.query_selector_all('a[href]')
            for link in all_links:
                href = link.get_attribute('href')
                if not href:
                    continue
                
                if 'twitter.com' in href or 'x.com' in href:
                    maker_info['twitter'] = href
                elif 'linkedin.com' in href:
                    maker_info['linkedin'] = href
                elif href.startswith('mailto:'):
                    maker_info['email'] = href.replace('mailto:', '')
                elif href.startswith('http') and 'producthunt.com' not in href:
                    # Likely personal website
                    if not maker_info['website']:
                        maker_info['website'] = href
            
            return maker_info
            
        except Exception as e:
            print(f"Error getting maker details: {e}", flush=True)
            return {}
    
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
