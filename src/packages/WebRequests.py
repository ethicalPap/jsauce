import requests
import os
from urllib.parse import urlparse
from src import config
from src.utils.Banner import Banner
from src.utils.Logger import get_logger
import random

jsauce_banner = Banner()

class WebRequests:
    def __init__(self):
        # Create a session for connection reuse and better performance
        self.session = requests.Session()
        
        # Set session timeout
        self.session.timeout = config.REQUEST_TIMEOUT

        # init logger instance
        self.logger = get_logger()

        
    def fetch_url_content(self, url, timeout=config.REQUEST_TIMEOUT, user_agent = random.choice(config.USER_AGENTS)):
        self.logger.debug(f"Fetching URL: {url} with user-agent: {user_agent}")

        try:
            # Try with random user agent first
            headers = {'User-Agent': user_agent}
            self.logger.verbose(f"making request to {url} with headers: {headers}")

            response = self.session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            content_length = len(response.content)
            self.logger.log_request_details(url, response.status_code, content_length)
            self.logger.debug(f"Response headers: {dict(response.headers)}")

            return response.text

        except requests.exceptions.HTTPError as e:
            self.logger.debug(f"HTTP Error for {url}: {e}")

            # Sometimes user-agent gets blocked. If we get 403/blocked, try without user agent
            if e.response and e.response.status_code in [403, 429]:
                jsauce_banner.add_status(f"User agent blocked for {url}, trying without UA...", "warning")
                self.logger.warning(f"User agent blocked for {url}, trying without UA...")

                try:
                    self.logger.verbose(f"making request to {url} without user-agent")

                    # Try again without any user agent (requests default)
                    response = self.session.get(url, timeout=timeout)
                    response.raise_for_status()

                    content_length = len(response.content)
                    self.logger.log_request_details(url, response.status_code, content_length)
                    jsauce_banner.add_status(f"Success without user agent: {url}", "success")

                    return response.text
                
                # If ssl error occurs, try HTTP instead
                except requests.exceptions.SSLError as e:
                    self.logger.debug(f"SSL Error for {url}: {e}")

                    # SSL error - try HTTP instead
                    if url.startswith('https://'):
                        jsauce_banner.add_status(f"SSL error with {url}, trying HTTP...", "warning")
                        self.logger.warning(f"SSL error with {url}, trying HTTP...")
                        http_url = url.replace('https://', 'http://', 1)
                        return self.fetch_url_content(http_url, timeout)
                    else:
                        jsauce_banner.add_status(f"SSL error: {e}", "error")
                        self.logger.error(f"SSL error: {e}")
                        return None
                        
                # If any other error occurs, log it
                except requests.RequestException as e2:
                    error_details = f"Error fetching {url} (both with and without UA): {type(e2).__name__}: {str(e2)}"
                    jsauce_banner.add_status(error_details, "error")
                    self.logger.error(error_details)
                    return None
            else:
                error_details = f"Error fetching {url}: {type(e).__name__}: {str(e)}"
                jsauce_banner.add_status(error_details, "error")
                self.logger.error(error_details)
                return None
        except requests.RequestException as e:
            self.logger.debug(f"Request Error for {url}: {e}")
            # For other errors, try without user agent as fallback
            jsauce_banner.add_status(f"Request failed for {url}, trying without UA...", "warning")
            self.logger.warning(f"Request failed for {url}, trying without UA...")

            try:
                self.logger.verbose(f"making request to {url} without user-agent")
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()

                content_length = len(response.content)
                self.logger.log_request_details(url, response.status_code, content_length)
                jsauce_banner.add_status(f"Success without user agent: {url}", "success")
                self.logger.success(f"Success without user agent: {url}")

                return response.text
            except requests.RequestException as e2:
                error_details = f"Error fetching {url} (both with and without UA): {type(e2).__name__}: {str(e2)}"
                jsauce_banner.add_status(error_details, "error")
                self.logger.error(error_details)
                return None
        
    # add protocol if missing from url
    def add_protocol_if_missing(self, url):
        if not url.startswith(('http://', 'https://')):
            modified_url = 'https://' + url
            self.logger.debug(f"added protocol to {url} - {modified_url}")
            return modified_url
        return url

    # save url content to file
    def save_url_content(self, url, content):
        filename = os.path.basename(urlparse(url).path) or f"un-named.html"
        file_path = f"{config.URL_CONTENT_DIR}/{filename}"

        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            self.logger.log_file_operation("Saved", file_path, True)
            self.logger.debug(f"Saved {len(content)} bytes to {file_path}")
        except Exception as e:
            self.logger.log_file_operation("Failed to save", file_path, False)
            self.logger.error(f"Error saving content to {file_path}: {e}")

    # close the session when done
    def close_session(self):
        if self.session:
            self.session.close()
            self.logger.debug("HTTP Session closed")
    
    # session cleanup
    def __del__(self):
        self.close_session()


