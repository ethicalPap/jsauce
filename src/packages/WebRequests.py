import requests
import os
from urllib.parse import urlparse
from src import config
from src.utils.Banner import Banner
import random

jsauce_banner = Banner()

class WebRequests:
    def __init__(self):
        # Create a session for connection reuse and better performance
        self.session = requests.Session()
        
        # Set session timeout
        self.session.timeout = config.REQUEST_TIMEOUT
        
    def fetch_url_content(self, url, timeout=config.REQUEST_TIMEOUT):
        try:
            # Try with random user agent first
            user_agent = random.choice(config.USER_AGENTS)
            headers = {'User-Agent': user_agent}
            response = self.session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:

            # Sometimes user-agent gets blocked. If we get 403/blocked, try without user agent
            if e.response and e.response.status_code in [403, 429]:
                jsauce_banner.add_status(f"User agent blocked for {url}, trying without UA...", "warning")
                try:
                    # Try again without any user agent (requests default)
                    response = self.session.get(url, timeout=timeout)
                    response.raise_for_status()
                    jsauce_banner.add_status(f"Success without user agent: {url}", "success")
                    return response.text
                
                # If ssl error occurs, try HTTP instead
                except requests.exceptions.SSLError as e:
                    # SSL error - try HTTP instead
                    if url.startswith('https://'):
                        jsauce_banner.add_status(f"SSL error with {url}, trying HTTP...", "warning")
                        http_url = url.replace('https://', 'http://', 1)
                        return self.fetch_url_content(http_url, timeout)
                    else:
                        jsauce_banner.add_status(f"SSL error: {e}", "error")
                        return None
                        
                # If any other error occurs, log it
                except requests.RequestException as e2:
                    error_details = f"Error fetching {url} (both with and without UA): {type(e2).__name__}: {str(e2)}"
                    jsauce_banner.add_status(error_details, "error")
                    return None
            else:
                error_details = f"Error fetching {url}: {type(e).__name__}: {str(e)}"
                jsauce_banner.add_status(error_details, "error")
                return None
        except requests.RequestException as e:
            # For other errors, try without user agent as fallback
            jsauce_banner.add_status(f"Request failed for {url}, trying without UA...", "warning")
            try:
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                jsauce_banner.add_status(f"Success without user agent: {url}", "success")
                return response.text
            except requests.RequestException as e2:
                error_details = f"Error fetching {url} (both with and without UA): {type(e2).__name__}: {str(e2)}"
                jsauce_banner.add_status(error_details, "error")
                return None
        
    # add protocol if missing from url
    def add_protocol_if_missing(self, url):
        if not url.startswith(('http://', 'https://')):
            return 'https://' + url
        return url

    # save url content to file
    def save_url_content(self, url, content):
        filename = os.path.basename(urlparse(url).path) or f"un-named.html"
        with open(f"{config.URL_CONTENT_DIR}/{filename}", 'w', encoding='utf-8') as file:
            file.write(content) 

    # close the session when done
    def close_session(self):
        if self.session:
            self.session.close()
    
    # session cleanup
    def __del__(self):
        self.close_session()