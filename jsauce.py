from src import config
from src.packages.LoadTemplate import LoadTemplate
from src.handlers.DomainHandler import DomainHandler
from src.packages.MermaidConverter import JSONToMermaidConverter  
from src.packages.MermaidCLI import MermaidCLI
from src.packages.UrlProcessor import URLProcessor
from src.packages.WebRequests import WebRequests
from src.handlers.InputFileHandler import InputFileHandler
from src.handlers.OutFileHandler import OutFileHandler
from src.utils.Banner import Banner
import sys

# Initialize processors
webrequests = WebRequests()
domain_handler = DomainHandler()
converter = JSONToMermaidConverter()
mermaid_cli = MermaidCLI()
url_processor = URLProcessor()
load_template = LoadTemplate(config.DEFAULT_TEMPLATE)
input_file_handler = InputFileHandler()
output_handler = OutFileHandler()
jsauce_banner = Banner()

# create necessary directories if they do not exist
output_handler.create_directories()


def main():
    # Banner for tool
    jsauce_banner.print_frozen_banner()

    if len(sys.argv) != 2:
        print("Usage: python main.py <input_file>")
        exit(1)
    
    # Load URLs and patterns
    urls = input_file_handler.get_input_urls(sys.argv[1])

    # load templates
    templates, _ = load_template.load_patterns()
    
    if not templates:
        jsauce_banner.show_error("ERROR: No patterns loaded. Cannot proceed.")
        exit(1)
    
    # Group URLs by domain and clear files once per domain
    domains_processed = set()
    
    # Process each URL
    for url in urls:
        domain = domain_handler.extract_domain(url)
        if domain and domain not in domains_processed:
            # Clear files only on first URL for this domain
            output_handler.clear_domain_files(domain)
            domains_processed.add(domain)
        
        url_processor.process_url(url, templates)
    
    # Clean up and generate outputs
    converter.clean_json_files(urls)
    converter.generate_mermaid(urls)
    
if __name__ == "__main__":
    main()