from src.packages.EndpointProcessor import EndpointProcessor
from src.packages.JsProcessor import JsProcessor
from src.handlers.DomainHandler import DomainHandler
from src.packages.WebRequests import WebRequests
from src.utils.Banner import Banner
import time

# initialize packages
domain_handler = DomainHandler()
webrequests = WebRequests()
jsauce_banner = Banner()

class URLProcessor:
    def __init__(self):
        pass

    def process_url(self, url, templates):
        """Process a single URL"""
        # jsauce_banner.update_status(f"\n{'='*80}\nPROCESSING: {url}\n{'='*80}")
        
        domain = domain_handler.extract_domain(url)
        if not domain:
            print(f"Could not extract domain from {url}")
            return
        
        # Initialize processors
        processor = EndpointProcessor()
        jsprocessor = JsProcessor()
        processor.templates_by_category = templates
        
        # jsauce_banner.update_status(f"Domain: {domain}")
        
        # Fetch and process HTML
        html_content = webrequests.fetch_url_content(webrequests.add_protocol_if_missing(url))
        if not html_content:
            jsauce_banner.show_error(f"Failed to fetch content from {url}")
            time.sleep(1)
            return
        
        webrequests.save_url_content(url, html_content)
        js_links = jsprocessor.extract_js_links(html_content, url)
        # jsauce_banner.update_status(f"Found {len(js_links)} JS links")
        
        if js_links:
            jsprocessor.save_js_links(js_links, f"{domain}_js_links.txt")
            
            # Process each JS file
            print(f"Processing {len(js_links)} JS links...")
            for i, js_link in enumerate(js_links, 1):
                jsauce_banner.update_progress(i, len(js_links), f"Processing JS files for {url}")
                js_content = webrequests.fetch_url_content(js_link)
                if js_content:
                    findings = processor.search_js_content_by_category_with_context(
                        js_content, js_link, url, templates
                    )
                    if findings:
                        processor.merge_categorized_results(findings)
                else:
                    jsauce_banner.show_error(f"Failed to fetch JS content from {js_link}")
        
        # Save results
        #jsauce_banner.update_status(f"\n{'='*50}\nSAVING RESULTS FOR {domain}...")
        
        all_endpoints = processor.get_all_endpoints_flat()
        processor.save_endpoints_to_txt(all_endpoints, f"{domain}/{domain}_endpoints_found.txt")
        
        if all_endpoints:
            jsauce_banner.show_completion(f"Saved {len(all_endpoints)} endpoints to: ./output/{domain}_endpoints_found.txt")
        else:
            jsauce_banner.show_error(f"No endpoints found - empty file saved")
        
        # Save detailed results if any found
        if processor.categorized_results or processor.detailed_results:
            processor.save_detailed_results_to_json(f"{domain}/{domain}_endpoints_detailed.json")
            processor.save_flat_endpoints_for_db(f"{domain}/{domain}_endpoints_for_db.json")
            processor.save_summary_stats_json(f"{domain}/{domain}_endpoint_stats.json")
        
        # Print statistics
        stats = processor.get_category_stats()