# main.py
# grab js files from links, read them, then grab content based on templates

import config
from src.packages.LoadTemplate import LoadTemplate
from src.packages.EndpointProcessor import EndpointProcessor
from src.packages.WebRequests import WebRequests
from src.packages.JsProcessor import JsProcessor
from src.packages.DomainHandler import DomainHandler
import sys
from collections import defaultdict

# Global Vars
input_urls = []
js_files = []
input_url_domains = {}

# read input from args
def get_input_from_argsys1(input_file):
    global input_urls
    try:
        with open(input_file, 'r') as file:
            for line in file:
                line = line.strip()
                # skip line if ends in .js
                if line and line.endswith('.js'):
                    print(f"Skipping JS file: {line}")
                    js_files.append(line)
                elif line and not line.startswith('#'):
                    input_urls.append(line)
    except Exception as e:
        print(f"Error reading input file {input_file}: {e}")
        exit(1)
    return input_urls


def main():
    # Check command line arguments (sysarg1 only so far)
    if len(sys.argv) != 2:
        print("Invalid number of arguments. Please provide an input file.") 
        exit(1)
    else:
        args_input = sys.argv[1]

    # Initialize processors
    webrequests = WebRequests()
    processor = EndpointProcessor()
    jsprocessor = JsProcessor()
    domain_handler = DomainHandler()
    
    # Load templates
    template_loader = LoadTemplate(config.TEMPLATE_ENDPOINTS)
    print("Template loaded from:", config.TEMPLATE_ENDPOINTS)
    template_lines = template_loader.get_lines()
    
    # Parse templates by category using the processor
    templates_by_category = processor.parse_templates_by_category(template_lines)
    
    # Get argument input URLs
    urls = get_input_from_argsys1(args_input)
    all_js_links = []
    url_to_js_mapping = {}  # Track which JS files came from which URLs

    # map input URLs to domains
    for url in urls:
        domain = domain_handler.extract_domain(url)
        if domain:
            input_url_domains[url] = domain

    print(f"\nProcessing {len(urls)} URLs...")

    # Save all js links to a file
    if all_js_links:
        # group js links by domain
        domain_to_js_links = defaultdict(list)
        for url in urls:
            domain = domain_handler.extract_domain(url)
            if domain:
                html_content = webrequests.fetch_url_content(webrequests.add_protocol_if_missing(url))
                if html_content:
                    webrequests.save_url_content(url, html_content)
                    js_links = jsprocessor.extract_js_links(html_content, url)
                    all_js_links.extend(js_links)
                    js_files.extend(js_links)
                    url_to_js_mapping.update({js_link: url for js_link in js_links})
                    domain_to_js_links[domain].extend(js_links)
                    print(f"  Found {len(js_links)} JS links.")
                else:
                    print(f"  Failed to fetch content from {url}")

        # Save all js links to a file by input domain
        for domain, js_links in domain_to_js_links.items():
            jsprocessor.save_js_links(js_links, f"{domain}_js_links.txt")
                
    # Read js links from file
    js_links = jsprocessor.read_js_links(domain)
    
    if not js_links:
        print("No JS links to process")
        return
    
    print(f"Total JS links to process: {len(js_links)}")
    
    # Process each JS link using the new processor
    print("\nProcessing JS links...")
    if not templates_by_category:
        print("No templates found to search in JS files.")
        return

    # Iterate through each JS link and search for findings
    for i, js_link in enumerate(js_links, 1):
        print(f"Processing JS Link {i}/{len(js_links)}: {js_link}")
        js_content = webrequests.fetch_url_content(js_link)
        if js_content:
            # Get source URL for this JS file
            source_url = url_to_js_mapping.get(js_link, "unknown")
            
            # Use context-aware search
            findings = processor.search_js_content_by_category_with_context(
                js_content, js_link, source_url, templates_by_category
            )
            
            if findings:
                processor.merge_categorized_results(findings)
            else:
                print(f"  No findings in {js_link}")
        else:
            print(f"  Failed to fetch JS content from {js_link}")

    # Get all results
    all_endpoints_found = processor.get_all_endpoints_flat()
    
    # Save and categorize endpoints
    if all_endpoints_found or processor.categorized_results:
        print(f"\n{'='*50}")
        print("SAVING RESULTS...")
        
        # Save original flat list for backwards compatibility
        if all_endpoints_found:
            processor.save_endpoints_to_txt(all_endpoints_found, f"{domain}_endpoints_found.txt")
            print(f"All endpoints saved to: ./output/{domain}endpoints_found.txt ({len(all_endpoints_found)} endpoints)")
        
        # Save categorized results to JS file
        if processor.categorized_results:
            endpoints_detailed = processor.save_detailed_results_to_json(f"{domain}_endpoints_detailed.json")
            print(f"Categorized endpoints saved to: ./output/{domain}endpoints_by_category.js")

            endpoints_flat = processor.save_flat_endpoints_for_db(f"{domain}_endpoints_for_db.json")
            print(f"Flat endpoints for DB saved to: ./output/{domain}endpoints_for_db.json")

            stats = processor.save_summary_stats_json(f"{domain}_endpoint_stats.json")
            print(f"Summary statistics saved to: ./output/{domain}endpoint_stats.json")

        
        # Final statistics
        stats = processor.get_category_stats()
        print(f"\n{'='*50}")
        print(f"Total Categories: {stats['total_categories']}")
        print(f"Total Endpoints: {stats['total_endpoints']}")
        print(f"Processing completed successfully!")
        
    else:
        print("No endpoints found")


if __name__ == "__main__":
    main()