from src.packages.CategoryProcessor import CategoryProcessor
from src.packages.JsProcessor import JsProcessor
from src.handlers.DomainHandler import DomainHandler
from src.packages.WebRequests import WebRequests
from src.utils.Banner import Banner

# initialize packages
domain_handler = DomainHandler()
webrequests = WebRequests()
jsauce_banner = Banner()

class URLProcessor:
    def __init__(self):
        pass

    def process_url(self, url, templates):
        """Process a single URL - only create output if content is found"""
        domain = domain_handler.extract_domain(url)
        if not domain:
            jsauce_banner.show_warning(f"Could not extract domain from {url}")
            return False  # Return False to indicate no processing occurred
        
        # Initialize processors
        processor = CategoryProcessor()
        jsprocessor = JsProcessor()
        processor.templates_by_category = templates
        
        # Fetch and process HTML
        jsauce_banner.add_status(f"Fetching content from {domain}...")
        html_content = webrequests.fetch_url_content(webrequests.add_protocol_if_missing(url))
        if not html_content:
            jsauce_banner.show_warning(f"Failed to fetch content from {url} - skipping")
            return False  # Return False - no content means no processing
        
        # Extract JS links
        js_links = jsprocessor.extract_js_links(html_content, url)
        jsauce_banner.add_status(f"Found {len(js_links)} JavaScript files in {domain}")
        
        # Track if we actually found any endpoints
        total_content_found = 0
        has_any_findings = False
        
        if js_links:
            # Process each JS file
            for i, js_link in enumerate(js_links, 1):
                jsauce_banner.add_status(f"Analyzing JS file {i}/{len(js_links)} from {domain}") # this might have to be add_status if it causes issues
                js_content = webrequests.fetch_url_content(js_link)
                if js_content:
                    findings = jsprocessor.search_js_content_by_category(
                        js_content, js_link, url, templates
                    )
                    if findings:
                        processor.merge_categorized_results(findings)
                        has_any_findings = True
                        jsauce_banner.add_status(f"Found endpoints in {js_link}", "success")
                else:
                    jsauce_banner.show_warning(f"Failed to fetch JS content from {js_link}")
        
        # Get final endpoint count
        all_endpoints = processor.get_all_content_flat()
        total_content_found = len(all_endpoints)
        
        # Only create output directory and files if we have actual findings
        if total_content_found > 0 or has_any_findings:
            jsauce_banner.add_status(f"Creating output files for {domain}...")
            
            # NOW create the output directory (only when we have data)
            self._ensure_output_directory(domain)
            
            # Save all the results
            processor.save_content_to_txt(all_endpoints, f"{domain}/{domain}_content_found.txt")
            jsauce_banner.add_status(f"Saved {total_content_found} endpoints for {domain}", "success")
            
            # Save detailed results
            if processor.categorized_results or processor.detailed_results:
                processor.save_detailed_results_to_json(f"{domain}/{domain}_content_detailed.json")
                processor.save_flat_content_for_db(f"{domain}/{domain}_content_for_db.json")
                processor.save_summary_stats_json(f"{domain}/{domain}_content_stats.json")
                jsauce_banner.add_status(f"Analysis files saved for {domain}", "success")
            
            # Save JS links if we had any
            if js_links:
                jsprocessor.save_js_links(js_links, f"{domain}_js_links.txt")
            
            # Save URL content for reference
            webrequests.save_url_content(url, html_content)
            
            return True  # Successfully processed with findings
        else:
            jsauce_banner.show_warning(f"No endpoints found for {domain} - skipping output creation")
            return False  # No findings, no output created
    
    def _ensure_output_directory(self, domain):
        """Create output directory for domain (only called when we have data)"""
        import os
        from src import config
        
        domain_output_path = f"{config.OUTPUT_DIR}/{domain}"
        os.makedirs(domain_output_path, exist_ok=True)
        jsauce_banner.add_status(f"Created output directory: {domain_output_path}")