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


# Initialize processors
webrequests = WebRequests()
domain_handler = DomainHandler()

# Global Vars
input_urls = []
js_files = []
input_url_domains = {}

# Load templates
template_loader = LoadTemplate(config.TEMPLATE_ENDPOINTS)
print("Template loaded from:", config.TEMPLATE_ENDPOINTS)
template_lines = template_loader.get_lines()

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
                    input_urls.append(webrequests.add_protocol_if_missing(line))
                    print(line)
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
    
    # Get argument input URLs
    urls = get_input_from_argsys1(args_input)
    
    # map input URLs to domains
    for url in urls:
        domain = domain_handler.extract_domain(url)
        if domain:
            input_url_domains[url] = domain


    print(f"\nProcessing {len(urls)} URLs...")

    # Process each URL individually
    for url in urls:
        print(f"\n{'='*80}")
        print(f"PROCESSING: {url}")
        print(f"{'='*80}")

        # Initialize processors for each URL ---> must be in the loop to reset state and prevent data from being combined across URLs
        processor = EndpointProcessor()
        jsprocessor = JsProcessor()
    
        # Parse templates by category using the processor
        templates_by_category = processor.parse_templates_by_category(template_lines)
        
        domain = domain_handler.extract_domain(url)
        if not domain:
            print(f"Could not extract domain from {url}, skipping...")
            continue
            
        print(f"Domain: {domain}")
        
        # Process this specific URL
        protocol_url = webrequests.add_protocol_if_missing(url)
        html_content = webrequests.fetch_url_content(protocol_url)
        js_links = []
        
        if html_content:
            webrequests.save_url_content(url, html_content)
            js_links = jsprocessor.extract_js_links(html_content, url)
            print(f"Found {len(js_links)} JS links for {url}")
            
            # Save JS links for this domain
            if js_links:
                jsprocessor.save_js_links(js_links, f"{domain}_js_links.txt")
                print(f"Saved {len(js_links)} JS links for {domain}")
        else:
            print(f"Failed to fetch content from {url}")
        
        # Process JS links for this URL
        if js_links and templates_by_category:
            print(f"\nProcessing {len(js_links)} JS links...")
            
            for i, js_link in enumerate(js_links, 1):
                print(f"Processing JS Link {i}/{len(js_links)}: {js_link}")
                js_content = webrequests.fetch_url_content(js_link)
                if js_content:
                    # Use context-aware search
                    findings = processor.search_js_content_by_category_with_context(
                        js_content, js_link, url, templates_by_category
                    )
                    
                    if findings:
                        processor.merge_categorized_results(findings)
                        # print(f"  Found endpoints in {len(findings)} categories")
                    else:
                        # print(f"  No findings in {js_link}")
                        pass
                else:
                    print(f"  Failed to fetch JS content from {js_link}")
        
        # Generate output for this URL/domain
        print(f"\n{'='*50}")
        print(f"SAVING RESULTS FOR {domain}...")
        
        # Get all results for this URL
        all_endpoints_found = processor.get_all_endpoints_flat()
        
        # Always save results, even if empty
        if all_endpoints_found:
            processor.save_endpoints_to_txt(all_endpoints_found, f"{domain}_endpoints_found.txt")
            print(f"All endpoints saved to: ./output/{domain}_endpoints_found.txt ({len(all_endpoints_found)} endpoints)")
        else:
            # Create empty file to indicate processing was attempted
            processor.save_endpoints_to_txt([], f"{domain}_endpoints_found.txt")
            print(f"No endpoints found - empty file saved to: ./output/{domain}_endpoints_found.txt")
        
        # Save detailed results if any were found
        if processor.categorized_results or processor.detailed_results:
            endpoints_detailed = processor.save_detailed_results_to_json(f"{domain}_endpoints_detailed.json")
            print(f"Detailed endpoints saved to: ./output/{domain}_endpoints_detailed.json")

            endpoints_flat = processor.save_flat_endpoints_for_db(f"{domain}_endpoints_for_db.json")
            print(f"Flat endpoints for DB saved to: ./output/{domain}_endpoints_for_db.json")

            stats = processor.save_summary_stats_json(f"{domain}_endpoint_stats.json")
            print(f"Summary statistics saved to: ./output/{domain}_endpoint_stats.json")
        # else:
        #     # Save empty JSON files for consistency
        #     import json
        #     import os
            
        #     # Empty detailed results
        #     empty_detailed = {
        #         'metadata': {
        #             'total_sources': 1,
        #             'total_js_files': 0,
        #             'total_endpoints': 0,
        #             'extraction_date': processor._get_current_timestamp()
        #         },
        #         'endpoints_by_source': {url: {'source_url': url, 'js_files': {}}},
        #         'endpoints_summary': {}
        #     }
            
        #     os.makedirs(f"{config.OUTPUT_DIR}", exist_ok=True)
        #     with open(f"{config.OUTPUT_DIR}{domain}_endpoints_detailed.json", 'w', encoding='utf-8') as file:
        #         json.dump(empty_detailed, file, indent=2)
        #     print(f"Empty detailed results saved to: ./output/{domain}_endpoints_detailed.json")
            
        #     # Empty flat results
        #     empty_flat = {
        #         'metadata': {
        #             'total_records': 0,
        #             'extraction_date': processor._get_current_timestamp(),
        #             'schema_version': '1.0'
        #         },
        #         'endpoints': []
        #     }
            
        #     with open(f"{config.OUTPUT_DIR}{domain}_endpoints_for_db.json", 'w', encoding='utf-8') as file:
        #         json.dump(empty_flat, file, indent=2)
        #     print(f"Empty flat results saved to: ./output/{domain}_endpoints_for_db.json")
            
        #     # Empty stats
        #     empty_stats = {
        #         'sources': {url: {'js_files_count': 0, 'total_endpoints': 0, 'categories': {}}},
        #         'categories': {},
        #         'overall': {
        #             'total_sources': 1,
        #             'total_js_files': 0,
        #             'total_endpoints': 0,
        #             'unique_endpoints': 0
        #         },
        #         'metadata': {
        #             'extraction_date': processor._get_current_timestamp(),
        #             'top_categories': []
        #         }
        #     }
            
        #     with open(f"{config.OUTPUT_DIR}{domain}_endpoint_stats.json", 'w', encoding='utf-8') as file:
        #         json.dump(empty_stats, file, indent=2)
        #     print(f"Empty stats saved to: ./output/{domain}_endpoint_stats.json")

        # Final statistics for this URL
        stats = processor.get_category_stats()
        print(f"\nRESULTS for {domain}:")
        print(f"  Categories: {stats['total_categories']}")
        print(f"  Endpoints: {stats['total_endpoints']}")
        print(f"  JS files processed: {len(js_links)}")
        print(f"Processing completed for {domain}!")

        del processor
        del jsprocessor

    print(f"\n{'='*80}")
    print(f"ALL PROCESSING COMPLETED!")
    print(f"Processed {len(urls)} URLs total")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()