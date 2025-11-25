from playwright.sync_api import sync_playwright
import time
import random
import os

class CrunchbaseBot:
    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.auth_file = "cb_auth.json"
        
    def start(self, auth_content=None):
        """Initialize browser with optional authentication"""
        print("Initializing Crunchbase bot...", flush=True)
        self.playwright = sync_playwright().start()
        
        # Load authentication if available
        storage_state = None
        if auth_content:
            try:
                import json
                cookies = json.loads(auth_content)
                storage_state = {"cookies": cookies, "origins": []}
                print("Loaded Crunchbase authentication.", flush=True)
            except:
                pass
        elif os.path.exists(self.auth_file):
            storage_state = self.auth_file
        
        # Launch browser
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            storage_state=storage_state,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        self.page = self.context.new_page()
        
    def search_company(self, company_name):
        """Search for a company on Crunchbase and return URL if found"""
        try:
            # Clean company name
            search_query = company_name.replace(' ', '+')
            search_url = f"https://www.crunchbase.com/textsearch?q={search_query}"
            
            print(f"Searching Crunchbase for: {company_name}", flush=True)
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(random.uniform(2, 3))
            
            # Look for first company result
            company_link = self.page.query_selector('a[href^="/organization/"]')
            if company_link:
                href = company_link.get_attribute('href')
                company_url = "https://www.crunchbase.com" + href
                print(f"  Found on Crunchbase: {company_url}", flush=True)
                return company_url
            else:
                print(f"  Not found on Crunchbase.", flush=True)
                return None
                
        except Exception as e:
            print(f"Error searching Crunchbase: {e}", flush=True)
            return None
    
    def get_company_details(self, company_url):
        """Extract company details from Crunchbase page"""
        try:
            self.page.goto(company_url, wait_until="domcontentloaded", timeout=15000)
            time.sleep(random.uniform(3, 4))
            
            details = {
                'crunchbase_url': company_url,
                'funding': None,
                'employees': None,
                'location': None,
                'founded': None,
                'phone': None,
                'email': None,
                'linkedin': None,
                'description': None
            }
            
            # Get all text content for parsing
            page_text = self.page.inner_text('body')
            
            # Try to extract funding (look for patterns like "$1.5M", "$500K", etc.)
            import re
            funding_match = re.search(r'\$[\d.]+[KMB]', page_text)
            if funding_match:
                details['funding'] = funding_match.group()
            
            # Try to extract employee count
            emp_match = re.search(r'(\d+-\d+)\s+Employees', page_text, re.IGNORECASE)
            if emp_match:
                details['employees'] = emp_match.group(1)
            
            # Get location (look for common patterns)
            location_elem = self.page.query_selector('[class*="location"], [class*="headquarters"]')
            if location_elem:
                details['location'] = location_elem.inner_text().strip()
            
            # Get founded year
            founded_match = re.search(r'Founded\s+(\d{4})', page_text, re.IGNORECASE)
            if founded_match:
                details['founded'] = founded_match.group(1)
            
            # Get description
            desc_elem = self.page.query_selector('[class*="description"]')
            if desc_elem:
                desc_text = desc_elem.inner_text().strip()
                if len(desc_text) < 500:  # Reasonable description length
                    details['description'] = desc_text
            
            # Get contact info from links
            all_links = self.page.query_selector_all('a[href]')
            for link in all_links:
                href = link.get_attribute('href')
                if not href:
                    continue
                
                if 'linkedin.com/company' in href:
                    details['linkedin'] = href
                elif href.startswith('mailto:'):
                    details['email'] = href.replace('mailto:', '')
                elif href.startswith('tel:'):
                    details['phone'] = href.replace('tel:', '').replace('-', '').replace(' ', '')
            
            return details
            
        except Exception as e:
            print(f"Error getting Crunchbase details: {e}", flush=True)
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
