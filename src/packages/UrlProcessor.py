import os
from src import config

class URLProcessor:
    def __init__(self, webrequests, domain_handler, banner, jsprocessor, category_processor, template_name):
        self.webrequests = webrequests
        self.domain_handler = domain_handler
        self.banner = banner
        self.jsprocessor = jsprocessor
        self.category_processor = category_processor
        self.template = template_name


    def process_url(self, url, templates):
        """Process a single URL - only create output if content is found"""
        domain = self.domain_handler.extract_domain(url)
        if not domain:
            self.banner.show_warning(f"Could not extract domain from {url}")
            return False

        # IMPORTANT: Reset CategoryProcessor for this URL
        self.category_processor.reset_for_new_url()
        self.category_processor.templates_by_category = templates
        
        # Fetch and process HTML
        self.banner.add_status(f"Fetching content from {domain}...")
        html_content = self.webrequests.fetch_url_content(self.webrequests.add_protocol_if_missing(url))
        if not html_content:
            self.banner.show_warning(f"Failed to fetch content from {url} trying again without user-agents")
            html_content = self.webrequests.fetch_url_content(self.webrequests.add_protocol_if_missing(url), user_agent=None)
            # if still nothing, then skip
            if not html_content:
                self.banner(f"Failed to fetch content from {url} - skipping")
                return False
           
        
        # Extract JS links
        js_links = self.jsprocessor.extract_js_links(html_content, url)
        self.banner.add_status(f"Found {len(js_links)} JavaScript files in {domain}")
        
        # Track if we actually found any endpoints
        total_content_found = 0
        has_any_findings = False
        
        if js_links:
            # Process each JS file
            for i, js_link in enumerate(js_links, 1):
                self.banner.add_status(f"Analyzing JS file {i}/{len(js_links)} from {domain}")
                js_content = self.webrequests.fetch_url_content(js_link)
                if js_content:
                    findings = self.jsprocessor.search_js_content_by_category_with_context(
                        js_content, js_link, url, templates
                    )
                    if findings:
                        self.category_processor.merge_categorized_results(findings)
                        has_any_findings = True
                        self.banner.add_status(f"Found endpoints in {js_link}", "success")
                else:
                    self.banner.show_warning(f"Failed to fetch JS content from {js_link}")
        
        # Get final endpoint count from CURRENT processing only
        all_endpoints = self.category_processor.get_all_content_flat()
        total_content_found = len(all_endpoints)
        
        # Only create output directory and files if we have actual findings
        if total_content_found > 0 or has_any_findings:
            self.banner.add_status(f"Creating output files for {domain}...")
            
            # Create the output directory (only when we have data)
            self._ensure_output_directory(domain)
            
            # Save all the results for THIS URL only
            self.category_processor.save_content_to_txt(all_endpoints, f"{domain}/{domain}_{self.template}_found.txt")
            self.banner.add_status(f"Saved {total_content_found} endpoints for {domain}", "success")
            
            # Save detailed results for THIS URL only
            if self.category_processor.categorized_results or self.category_processor.detailed_results:
                self.category_processor.save_detailed_results_to_json(f"{domain}/{domain}_{self.template}_detailed.json")
                self.category_processor.save_flat_content_for_db(f"{domain}/{domain}_{self.template}_for_db.json")
                self.category_processor.save_summary_stats_json(f"{domain}/{domain}_{self.template}_stats.json")
                self.banner.add_status(f"Analysis files saved for {domain}", "success")
            
            # Save JS links if we had any
            if js_links:
                self.jsprocessor.save_js_links(js_links, f"{domain}_js_links.txt")
            
            # Save URL content for reference
            self.webrequests.save_url_content(url, html_content)
            
            return True  # Successfully processed with findings
        else:
            self.banner.show_warning(f"No endpoints found for {domain} - skipping output creation")
            return False  # No findings, no output created
    

    """This logic is to skip domains that already exist in the output directory. Debating on if I want to keep this or just overwrite"""
    # def _domain_already_processed(self, domain):
    #     """Check if domain folder exists and contains processed data"""
    #     domain_path = f"{config.OUTPUT_DIR}/{domain}"
        
    #     # Check if directory exists
    #     if not os.path.exists(domain_path):
    #         return False
        
    #     # Check if it contains any of the expected output files
    #     expected_files = [
    #         f"{domain}_{self.template}_found.txt",
    #         f"{domain}_{self.template}_detailed.json", 
    #         f"{domain}_{self.template}_stats.json"
    #     ]
        
    #     for filename in expected_files:
    #         file_path = os.path.join(domain_path, filename)
    #         if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
    #             return True  # Found at least one non-empty output file
        
    #     return False  # Directory exists but no valid output files found

    def _ensure_output_directory(self, domain):
        """Create output directory for domain (only called when we have data)"""
        import os
        from src import config
        
        domain_output_path = f"{config.OUTPUT_DIR}/{domain}"
        os.makedirs(domain_output_path, exist_ok=True)
        self.banner.add_status(f"Created output directory: {domain_output_path}")