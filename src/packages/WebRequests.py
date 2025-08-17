import requests
import os
from urllib.parse import urlparse
import config

class WebRequests:
    def __init__(self):
        pass
  
    def fetch_url_content(self, url, timeout=config.REQUEST_TIMEOUT):
        try:
            response = requests.get(url, timeout=timeout) # need to add headers here
            response.raise_for_status()  # Raise an error for bad responses
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
        
    # add protocol if missing from url
    def add_protocol_if_missing(self, url):
        if not url.startswith(('http://', 'https://')):
            return 'https://' + url
        return url


    # save url content to file
    def save_url_content(self, url, content):
        filename = os.path.basename(urlparse(url).path) or "index.html"
        os.makedirs("./data/url_content", exist_ok=True)
        with open(f"./data/url_content/{filename}", 'w', encoding='utf-8') as file:
            file.write(content) 