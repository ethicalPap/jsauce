import os
import re
from urllib.parse import urljoin


class JsProcessor:
    def __init__(self):
        pass

    # parse saved url content for js links
    def extract_js_links(self, html_content, base_url):
        js_links = []
        
        # Find all URLs in the HTML that contain .js
        all_links = re.findall(r'["\']([^"\']*\.js[^"\']*)["\']', html_content, re.IGNORECASE)
        
        for link in all_links:
            # Clean up the URL - remove escaped slashes and other artifacts
            clean_link = link.replace('\\/', '/').replace('\\"', '"').replace("\\'", "'")
            
            # Skip obviously malformed URLs
            if clean_link.startswith('//'):
                # Protocol-relative URL, add https
                clean_link = 'https:' + clean_link
            elif clean_link.startswith('/'):
                # Root-relative URL
                clean_link = urljoin(base_url, clean_link)
            elif not clean_link.startswith(('http://', 'https://')):
                # Relative URL
                clean_link = urljoin(base_url, clean_link)
            
            # Basic validation - skip if it looks malformed
            if '\\' in clean_link or clean_link.count('//') > 1:
                print(f"Skipping malformed URL: {link}")
                continue
                
            js_links.append(clean_link)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_js_links = []
        for link in js_links:
            if link not in seen:
                seen.add(link)
                unique_js_links.append(link)
        
        return unique_js_links


    # save js links to file
    def save_js_links(self, js_links, output_file):
        # look it through until we reach the end
        os.makedirs("./data/js_files", exist_ok=True)
        with open(f"./data/js_files/{output_file}", 'w') as file:
            for link in js_links:
                file.write(link + '\n')


    # read js links from file
    def read_js_links(self, file_path):
        try:
            with open(f"./data/js_files/{file_path}", 'r') as file:
                lines = file.readlines()
                js_links = [line.strip() for line in lines if line.strip()]
                return js_links
        except FileNotFoundError:
            print(f"File {file_path} not found")
            return []
        

    # read js file content
    def read_js_file(self, file_path):
        with open(file_path, 'r') as file:
            content = file.read()
            return content


    # search js content for findings based on templates (legacy function)
    def search_js_content(self, js_content, templates):
        results = {}
        for template, regex in templates.items():
            try:
                matches = re.findall(regex, js_content)
                if matches:
                    results[template] = matches
            except re.error as e:
                print(f"Invalid regex '{regex}': {e}")
                continue
        return results  