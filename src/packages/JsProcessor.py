import os
import re
from urllib.parse import urljoin
from src.utils.Logger import get_logger
from src import config

class JsProcessor:
    def __init__(self, banner, category_processor):
        self.banner = banner
        self.category_processor = category_processor
        self.logger = get_logger()


    # parse saved url content for js links
    def extract_js_links(self, html_content, base_url):
        self.logger.debug(f"Extracting JS links from {base_url}")
        self.logger.debug(f"HTML content length: {len(html_content)} bytes")

        js_links = []
        
        # Find all URLs in the HTML that contain .js
        all_links = re.findall(r'["\']([^"\']*\.js[^"\']*)["\']', html_content, re.IGNORECASE)
        self.logger.verbose(f"Found {len(all_links)} JS links")
        
        for link in all_links:
            # Clean up the URL - remove escaped slashes and other artifacts
            clean_link = link.replace('\\/', '/').replace('\\"', '"').replace("\\'", "'")
            self.logger.debug(f"Cleaned link: {clean_link}")
            
            # Skip obviously malformed URLs
            if clean_link.startswith('//'):
                # Protocol-relative URL, add https
                clean_link = 'https:' + clean_link
                self.logger.debug(f"Added protocol to {link}")
            elif clean_link.startswith('/'):
                # Root-relative URL
                clean_link = urljoin(base_url, clean_link)
                self.logger.debug(f"Added base URL to {link}")
            elif not clean_link.startswith(('http://', 'https://')):
                # Relative URL
                clean_link = urljoin(base_url, clean_link)
                self.logger.debug(f"Added base URL to {link}")
            
            # Basic validation - skip if it looks malformed
            if '\\' in clean_link or clean_link.count('//') > 1:
                self.banner.show_error(f"Skipping malformed URL: {link}")
                self.logger.warning(f"Skipping malformed URL: {link}")
                continue
                
            js_links.append(clean_link)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_js_links = []
        for link in js_links:
            if link not in seen:
                seen.add(link)
                unique_js_links.append(link)

        self.logger.info(f"Found {len(unique_js_links)} unique JS links", "success")
        self.logger.debug(f"Unique JS links: {unique_js_links}")
        
        return unique_js_links


    # save js links to file
    def save_js_links(self, js_links, output_file):
        # look it through until we reach the end
        os.makedirs(f"{config.JS_FILE_DIR}", exist_ok=True)
        file_path = f"{config.JS_FILE_DIR}/{output_file}"

        try:
            with open(f"{file_path}", 'w') as file:
                for link in js_links:
                    file.write(link + '\n')
            self.logger.log_file_operation("Saved", file_path, True)
            self.logger.verbose(f"Saved {len(js_links)} JS links")
        except Exception as e:
            self.logger.log_file_operation("Failed to save", file_path, False)
            self.logger.error(f"Error saving JS links to {file_path}: {e}")

    # read js links from file
    def read_js_links(self, file_path):
        full_path = f"{config.JS_FILE_DIR}/{file_path}"

        try:
            with open(f"{full_path}", 'r') as file:
                lines = file.readlines()
                js_links = [line.strip() for line in lines if line.strip()]
                self.logger.verbose(f"Read {len(js_links)} JS links from {file_path}")
                return js_links
        except FileNotFoundError:
            self.banner.show_error(f"File {file_path} not found")
            self.logger.error(f"File {file_path} not found")
            return []
        
    # read js file content
    def read_js_file(self, file_path):
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                self.logger.verbose(f"Read {len(content)} bytes from {file_path}")
                return content
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return None
        
    def search_js_content_by_category_with_context(self, js_content, js_url, source_url, templates_by_category=None):
        """Search JS content with context"""
        self.logger.debug(f"Analyzing KS content from {js_url}")
        self.logger.debug(f"KS content length: {len(js_content)} bytes")

        templates = templates_by_category or self.category_processor.templates_by_category
        results = {}
        total_patterns = sum(len(patterns) for patterns in templates.values())
        patterns_processed = 0
        
        for category, patterns in templates.items():
            matches = []
            for pattern in patterns:
                try:
                    flags = re.MULTILINE if any(k in category.lower() for k in ['token', 'key', 'secret', 'auth']) else re.IGNORECASE | re.MULTILINE
                    found = re.findall(pattern, js_content, flags)
                    
                    # Handle tuples from capture groups
                    if found and isinstance(found[0], tuple):
                        found = [next((g for g in match if g and g.strip()), '') for match in found]
                    
                    pattern_matches = [m.strip() for m in found if m and m.strip()]
                    matches.extend(pattern_matches)

                    if pattern_matches:
                        self.logger.log_pattern_match(pattern, pattern_matches, category)

                except:
                    self.logger.debug(f"Pattern failed: {pattern} in category {category}")
                    continue
            
            if matches:
                filtered = [m for m in matches if not self.category_processor._is_false_positive(m, category)]
                if filtered:
                    results[category] = list(dict.fromkeys(filtered))
                    self.logger.verbose(f"Found {len(filtered)} matches in {category}")

        total_matches = sum(len(matches) for matches in results.values())
        self.logger.log_js_analysis(js_url, total_matches, total_patterns)
        
        # Store results
        if js_url not in self.category_processor.detailed_results:
           self.category_processor.detailed_results[js_url] = {'source_url': source_url, 'js_url': js_url, 'categories': {}}
        
        for category, matches in results.items():
            if category not in self.category_processor.detailed_results[js_url]['categories']:
                self.category_processor.detailed_results[js_url]['categories'][category] = []
            self.category_processor.detailed_results[js_url]['categories'][category].extend(matches)
            self.category_processor.detailed_results[js_url]['categories'][category] = list(dict.fromkeys(
                self.category_processor.detailed_results[js_url]['categories'][category]
            ))
        
        return results
        
    def search_js_content_by_category(self, js_content, templates_by_category=None):
        """Search JS content by category"""
        self.logger.debug(f"Analyzing JS content ({len(js_content)}) bytes")


        templates = templates_by_category or self.category_processor.templates_by_category
        results = {}
        
        for category, patterns in templates.items():
            matches = []
            for pattern in patterns:
                try:
                    flags = re.MULTILINE if any(k in category.lower() for k in ['token', 'key', 'secret', 'auth']) else re.IGNORECASE | re.MULTILINE
                    found = re.findall(pattern, js_content, flags)
                    
                    if found and isinstance(found[0], tuple):
                        found = [next((g for g in match if g and g.strip()), '') for match in found]
                    
                    matches.extend([m.strip() for m in found if m and m.strip()])
                except:
                    self.logger.debug(f"Pattern failed: {pattern} in category {category}")
                    continue
            
            if matches:
                filtered = [m for m in matches if not self.category_processor._is_false_positive(m, category)]
                if filtered:
                    results[category] = list(dict.fromkeys(filtered))
        
        return results