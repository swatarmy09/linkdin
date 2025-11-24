import time
import random
import os
from playwright.sync_api import sync_playwright

class LinkedInBot:
    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.auth_file = 'auth.json'

    def start(self, auth_content=None):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        
        if auth_content:
             print("Loading authentication from Environment Variable...")
             # Create a temporary auth file from the env content
             with open(self.auth_file, 'w') as f:
                 f.write(auth_content)
             self.context = self.browser.new_context(storage_state=self.auth_file)
        elif os.path.exists(self.auth_file):
            print(f"Loading authentication from {self.auth_file}...")
            self.context = self.browser.new_context(storage_state=self.auth_file)
        else:
            print("No authentication found. Starting fresh context.")
            self.context = self.browser.new_context()
        
        self.page = self.context.new_page()

    def login(self):
        """
        Navigates to LinkedIn. If not logged in, waits for user to log in manually.
        """
        print("Navigating to LinkedIn...")
        self.page.goto("https://www.linkedin.com/")
        
        # Check if logged in by looking for specific element (e.g., search bar or profile icon)
        try:
            self.page.wait_for_selector(".global-nav__content", timeout=5000)
            print("Already logged in!")
        except:
            print("Not logged in. Please log in manually in the browser window.")
            print("Waiting for you to log in... (I'll check every 5 seconds)")
            
            while True:
                try:
                    # Check for a common element present when logged in (e.g., feed identity module)
                    if self.page.query_selector(".global-nav__content"):
                        print("Login detected!")
                        break
                except:
                    pass
                time.sleep(5)
            
            # Save state
            print("Saving authentication state...")
            self.context.storage_state(path=self.auth_file)

    def search_leads(self, keyword, location_filter=None, pages=1):
        """
        Searches for people with the given keyword and location.
        location_filter: 'India' or 'Global' (for now we just append to keyword or use geoUrn if known)
        """
        print(f"Searching for '{keyword}' in {location_filter or 'Global'}...")
        
        # Construct URL with location
        # Geo URNs: India = 102713980, USA = 103644278, UK = 101165590
        geo_param = ""
        if location_filter == "India":
            geo_param = "&geoUrn=%5B%22102713980%22%5D" # India
        elif location_filter == "Global":
            # Mix of USA, UK, Canada, Australia
            geo_param = "&geoUrn=%5B%22103644278%22%2C%22101165590%22%2C%22101174742%22%2C%22101452733%22%5D"
            
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={keyword}{geo_param}&origin=SWITCH_SEARCH_VERTICAL"
        self.page.goto(search_url)
        
        leads = []
        
        for i in range(pages):
            print(f"Scraping page {i+1}...")
            try:
                self.page.wait_for_selector(".reusable-search__result-container", timeout=10000)
            except:
                print("No results found or timeout.")
                break
            
            # Scroll down to load all results
            for _ in range(3):
                self.page.mouse.wheel(0, 1000)
                time.sleep(random.uniform(1, 2))
            
            results = self.page.query_selector_all(".reusable-search__result-container")
            
            for result in results:
                try:
                    name_el = result.query_selector(".entity-result__title-text a")
                    title_el = result.query_selector(".entity-result__primary-subtitle")
                    loc_el = result.query_selector(".entity-result__secondary-subtitle")
                    
                    if name_el:
                        name = name_el.inner_text().strip().split('\n')[0]
                        profile_url = name_el.get_attribute("href")
                        title = title_el.inner_text().strip() if title_el else "N/A"
                        location = loc_el.inner_text().strip() if loc_el else "N/A"
                        
                        leads.append({
                            "name": name,
                            "profile_url": profile_url,
                            "title": title,
                            "location": location
                        })
                except Exception as e:
                    print(f"Error parsing result: {e}")
            
            # Go to next page if requested and available
            if i < pages - 1:
                next_button = self.page.query_selector("button[aria-label='Next']")
                if next_button and next_button.is_enabled():
                    next_button.click()
                    time.sleep(random.uniform(3, 5))
                else:
                    print("No more pages.")
                    break
                    
        return leads

    def get_profile_details(self, profile_url):
        """
        Visits a profile and tries to find a website in the Contact Info.
        """
        print(f"Visiting profile: {profile_url}")
        try:
            self.page.goto(profile_url)
            time.sleep(random.uniform(2, 4))
            
            # Click "Contact info" if available
            # The selector for contact info link usually contains 'contact-info' in href or id
            contact_link = self.page.query_selector("a[id='top-card-text-details-contact-info']")
            
            website = None
            
            if contact_link:
                contact_link.click()
                time.sleep(random.uniform(1, 2))
                
                # Wait for modal
                self.page.wait_for_selector(".pv-contact-info__contact-type", timeout=5000)
                
                # Look for website section
                # This is tricky as structure changes. We look for links in the modal.
                links = self.page.query_selector_all(".pv-contact-info__contact-type.ci-websites a")
                for link in links:
                    href = link.get_attribute("href")
                    if href:
                        website = href
                        break # Just take the first one for now
                
                # Close modal
                close_btn = self.page.query_selector("button[aria-label='Dismiss']")
                if close_btn:
                    close_btn.click()
            
            return website
            
        except Exception as e:
            print(f"Error getting details for {profile_url}: {e}")
            return None

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
