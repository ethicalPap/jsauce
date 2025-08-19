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
from src.handlers.ArgumentHandler import ArgumentHandler

# Initialize processors
webrequests = WebRequests()
domain_handler = DomainHandler()
converter = JSONToMermaidConverter()
mermaid_cli = MermaidCLI()
url_processor = URLProcessor()
input_file_handler = InputFileHandler()
output_handler = OutFileHandler()
jsauce_banner = Banner()
argument_handler = ArgumentHandler()

def main():
    try:
        # parse command line args here
        args = argument_handler.parse_arguments()

        # load template arg
        template_file = argument_handler.get_templates(args)
        load_template = LoadTemplate(template_file)

        # Initialize banner with persistent display
        jsauce_banner.initialize_persistent_display()
        
        # Ensure base directories exist
        output_handler.ensure_base_directories()

        # Track processing statistics
        successful_domains = []
        skipped_domains = []
        processed_domains = set()  # Track domains we've seen to avoid duplicate clearing
        
        # Load URLs and patterns
        jsauce_banner.update_progress(0, 4, "Initializing")
        jsauce_banner.add_status("Loading input URLs...")
        urls = input_file_handler.get_input_urls(args.input)
        jsauce_banner.add_status(f"Loaded {len(urls)} URLs for processing", "success")


        # load templates
        jsauce_banner.update_progress(1, 4, "Loading templates")
        jsauce_banner.add_status("Loading endpoint templates...")
        templates, _ = load_template.load_patterns(template_file)
        
        if not templates:
            jsauce_banner.show_error("No patterns loaded. Cannot proceed.")
            exit(1)
        
        jsauce_banner.add_status(f"Loaded {len(templates)} template categories", "success")
        
        # Process each URL with progress tracking
        jsauce_banner.update_progress(2, 4, "Processing URLs")
        for i, url in enumerate(urls, 1):
            # Update sub-progress for URL processing
            jsauce_banner.update_progress(i, len(urls), f"Processing URLs ({i}/{len(urls)})")
            jsauce_banner.add_status(f"Processing URL {i}/{len(urls)}: {url}")
            
            domain = domain_handler.extract_domain(url)
            
            # Clear domain files only once per domain (for multiple URLs same domain)
            if domain and domain not in processed_domains:
                output_handler.clear_domain_files(domain)  # Only clears if directory exists
                processed_domains.add(domain)
            
            # Process the URL and check if we got results
            success = url_processor.process_url(url, templates)
            
            if success and domain:
                if domain not in successful_domains:
                    successful_domains.append(domain)
            elif domain:
                if domain not in skipped_domains and domain not in successful_domains:
                    skipped_domains.append(domain)
        
        # Only proceed with post-processing if we have successful domains
        if successful_domains:
            # Clean up and generate outputs
            jsauce_banner.update_progress(3, 4, "Post-processing")
            jsauce_banner.add_status("Cleaning up JSON files...")
            converter.clean_json_files(urls)  # This will only process existing files
            jsauce_banner.add_status("JSON cleanup completed", "success")
            
            converter.generate_mermaid(urls)  # This will only process domains with data
        else:
            jsauce_banner.add_status("No successful domains to post-process", "warning")
        
        # Verify what was actually created
        jsauce_banner.update_progress(4, 4, "Finalizing")

    except KeyboardInterrupt:
        jsauce_banner.add_status("Process interrupted by user", "warning")
    except Exception as e:
        jsauce_banner.show_error(f"Unexpected error: {e}")
    finally:
        # Always close the session, even if there's an error
        jsauce_banner.add_status("Cleaning up resources...")
        webrequests.close_session()
        jsauce_banner.add_status("Session closed", "success")

if __name__ == "__main__":
    main()


