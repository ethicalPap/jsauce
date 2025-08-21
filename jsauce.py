from src.packages.LoadTemplate import LoadTemplate
from src.handlers.DomainHandler import DomainHandler
from src.packages.MermaidConverter import JSONToMermaidConverter  
from src.packages.MermaidCLI import MermaidCLI
from src.packages.UrlProcessor import URLProcessor
from src.packages.WebRequests import WebRequests
from src.handlers.InputHandler import InputHandler
from src.handlers.OutFileHandler import OutFileHandler
from src.utils.Banner import Banner
from src.handlers.ArgumentHandler import ArgumentHandler
from src.packages.JsProcessor import JsProcessor
from src.packages.CategoryProcessor import CategoryProcessor
from src.utils.Logger import initialize_logger, get_logger
import os
from src import config


# All dependendencies should initialize here and used in other dependencies, so that they dont re-initialize and break things.
class JSauceApp:
    """Main application class that manages all dependencies"""
    
    def __init__(self):
        # Initialize basic dependencies first (no dependencies on others)
        self.banner = Banner()
        self.web_requests = WebRequests()
        self.domain_handler = DomainHandler()
        self.argument_handler = ArgumentHandler()

        # logger function (should be after argument handling)
        self.logger = get_logger()
        
        # Initialize dependencies that depend on basic ones
        self.input_file_handler = InputHandler(self.web_requests)
        self.mermaid_cli = MermaidCLI(self.banner)
        self.category_processor = CategoryProcessor(self.banner, self.domain_handler)
        self.jsprocessor = JsProcessor(self.banner, self.category_processor)

    # get the template names from template file paths
    def _extract_template_name_from_paths(self, template_paths):
        if not template_paths:
            return "default"
        
        if len(template_paths) == 1:
            # Single template file
            template_path = template_paths[0]
            filename = os.path.basename(template_path)
            template_name = os.path.splitext(filename)[0]
            return template_name.lower().replace(' ', '_').replace('-', '_')
        else:
            # For multiple template files - use directory name or generic name
            common_dir = os.path.commonpath([os.path.dirname(p) for p in template_paths])
            if common_dir:
                dir_name = os.path.basename(common_dir)
                if dir_name and dir_name != '.':
                    return dir_name.lower().replace(' ', '_').replace('-', '_')
                
            return "multi_template"
    
    def run(self):
        """Main execution method"""
        try:
            # Parse command line args
            args = self.argument_handler.parse_arguments()

            # init loggers with verbosity levels
            log_file = f"{config.LOG_DIR}/jsauce.log"
            self.logger = initialize_logger(args.verbose, self.banner, log_file)
            self.logger.debug(f"Verbosity level: {args.verbose}")

            # Load template arg
            template_files = self.argument_handler.get_templates(args.template)

            if not template_files:
                self.banner.show_error("No templates found. Check your template path.")
                self.logger.error("No templates found. Cannot proceed.")
                return False
            
            load_template = LoadTemplate(template_files, self.banner, self.category_processor)

            # grab template name
            template_name = self._extract_template_name_from_paths(template_files)
            self.logger.verbose(f"Using template name {template_name} from file {template_files}")

            # Initialize banner with persistent display
            self.banner.initialize_persistent_display()

            if not args.input and not args.url:
                self.banner.show_error("No input specified. Use -i <input_file> or -u <single_url>")
                return False
            
            # add args to self.converter
            self.converter = JSONToMermaidConverter(
                self.domain_handler, 
                self.banner,
                self.mermaid_cli,
                template_name
            )

            # add args to self.url_processor
            self.url_processor = URLProcessor(
                self.web_requests, 
                self.domain_handler, 
                self.banner,
                self.jsprocessor, 
                self.category_processor,
                template_name
            )

            # add args to outfileHandler
            self.output_handler = OutFileHandler(template_name)

            
            # Ensure base directories exist
            self.output_handler.ensure_base_directories()
            self.logger.debug("Base directories ensured")


            # Load URLs and patterns
            self.banner.update_progress(0, 4, "Initializing")


            # load URL(s)
            if args.url:
                self.banner.add_status(f"Processing single URL: {args.url}")
                urls = self.input_file_handler.get_input_urls(single_url=args.url)
                self.logger.info(f"Processing single URL: {args.url}", "success")
            else:
                self.banner.add_status("Loading input URLs from file...")
                urls = self.input_file_handler.get_input_urls(input_file=args.input)
                self.logger.info(f"Loaded {len(urls)} URLs for processing", "success")
            
            self.logger.debug(f"URLs to process: {urls}")

            # Load templates
            self.banner.update_progress(1, 4, "Loading templates")
            self.banner.add_status("Loading endpoint templates...")
            templates, _ = load_template.load_patterns()
            
            if not templates:
                self.banner.show_error("No patterns loaded. Cannot proceed.")
                return False
            
            self.logger.log_template_loading(template_files, len(templates))
            self.banner.add_status(f"Template categories: {list(templates.keys())}")


            # Process URLs
            successful_domains = self._process_urls(urls, templates)
            
            # Post-processing
            if successful_domains:
                self._post_process(urls)
            else:
                self.banner.add_status("No successful domains to post-process", "warning")
            
            self.banner.update_progress(4, 4, "Finalizing")
            self.logger.info(f"processing completed. Successful fomainsL {len(successful_domains)}", "success")
            return True
            
        except KeyboardInterrupt:
            self.banner.add_status("Process interrupted by user", "warning")
            self.logger.warning("Process interrupted by user")
            return False
        except Exception as e:
            self.banner.show_error(f"Unexpected error: {e}")
            self.logger.error(f"Unexpected error: {e}")
            return False
        finally:
            self._cleanup()
    
    def _process_urls(self, urls, templates):
        """Process all URLs and return successful domains"""
        successful_domains = []
        skipped_domains = []
        processed_domains = set()
        
        self.banner.update_progress(2, 4, "Processing URLs")
        for i, url in enumerate(urls, 1):
            # Update sub-progress for URL processing
            self.banner.update_progress(i, len(urls), f"Processing URLs ({i}/{len(urls)})")
            self.logger.info(f"Processing URL {i}/{len(urls)}: {url}")
            
            domain = self.domain_handler.extract_domain(url)

            # Clear domain files only once per domain (for multiple URLs same domain)
            if domain and domain not in processed_domains:
                self.output_handler.clear_domain_files(domain)  # Only clears if directory exists
                processed_domains.add(domain)
                self.logger.debug(f"Cleared domain files for {domain}")
            
            # Process the URL and check if we got results
            success = self.url_processor.process_url(url, templates)
            
            if success and domain:
                if domain not in successful_domains:
                    successful_domains.append(domain)
                    self.logger.success(f"Successfully processed domain: {domain}")
            elif domain:
                if domain not in skipped_domains and domain not in successful_domains:
                    skipped_domains.append(domain)
                    self.logger.warning(f"Skipped domain: {domain}")
        
        self.logger.info(f"Processing summary - Successful Domains: {len(successful_domains)}, Skipped Domains: {len(skipped_domains)}")
        return successful_domains
    
    def _post_process(self, urls):
        """Handle post-processing tasks"""
        self.banner.update_progress(3, 4, "Post-processing")
        self.logger.info("Starting post-processing tasks")
        
        self.banner.add_status("Cleaning up JSON files...")
        self.converter.clean_json_files(urls)  # This will only process existing files
        self.logger.verbose("JSON cleanup completed", "success")
        
        self.converter.generate_mermaid(urls)  # This will only process domains with data
        self.logger.verbose("Mermaid generation completed", "success")
    
    def _cleanup(self):
        """Clean up resources"""
        self.banner.add_status("Cleaning up resources...")
        self.web_requests.close_session()
        self.logger.debug("Session closed", "success")

def main():
    """Entry point - create and run the application"""
    app = JSauceApp()
    success = app.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()