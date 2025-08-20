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
from src.packages.JsProcessor import JsProcessor
from src.packages.CategoryProcessor import CategoryProcessor
import os


# All dependendencies should initialize here and used in other dependencies, so that they dont re-initialize and break things.
class JSauceApp:
    """Main application class that manages all dependencies"""
    
    def __init__(self):
        # Initialize basic dependencies first (no dependencies on others)
        self.banner = Banner()
        self.web_requests = WebRequests()
        self.domain_handler = DomainHandler()
        self.argument_handler = ArgumentHandler()
        
        # Initialize dependencies that depend on basic ones
        self.input_file_handler = InputFileHandler(self.web_requests)
        self.mermaid_cli = MermaidCLI(self.banner)
        self.category_processor = CategoryProcessor(self.banner, self.domain_handler)
        self.jsprocessor = JsProcessor(self.banner, self.category_processor)

    # get the template name for output files
    def _extract_template_name(self, template_file_path):
        """Extract a clean template name from the file path for use in filenames"""
        if not template_file_path:
            return "default"
        
        # Get the filename without extension
        filename = os.path.basename(template_file_path)
        template_name = os.path.splitext(filename)[0]
        
        # Clean up the name for use in filenames
        clean_name = template_name.lower().replace(' ', '_').replace('-', '_')
        
        # Map common template files to shorter names
        name_mappings = {
            'endpoints': 'endpoints',
            'sinks': 'security', 
            'security': 'security',
            'default_template': 'default',
            'custom': 'custom'
        }
        
        return name_mappings.get(clean_name, clean_name)
    
    def run(self):
        """Main execution method"""
        try:
            # Parse command line args
            args = self.argument_handler.parse_arguments()

            # Load template arg
            template_file = self.argument_handler.get_templates(args.template)
            load_template = LoadTemplate(template_file, self.banner, self.category_processor)

            # grab template name
            template_name = self._extract_template_name(template_file)

            # Initialize banner with persistent display
            self.banner.initialize_persistent_display()

            if not args.input:
                self.banner.show_error("No input file specified. Use -i <input_file>")
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

            # Load URLs and patterns
            self.banner.update_progress(0, 4, "Initializing")
            self.banner.add_status("Loading input URLs...")
            urls = self.input_file_handler.get_input_urls(args.input)
            self.banner.add_status(f"Loaded {len(urls)} URLs for processing", "success")

            # Load templates
            self.banner.update_progress(1, 4, "Loading templates")
            self.banner.add_status("Loading endpoint templates...")
            templates, _ = load_template.load_patterns()
            
            if not templates:
                self.banner.show_error("No patterns loaded. Cannot proceed.")
                return False
            
            self.banner.add_status(f"Loaded {len(templates)} template categories", "success")

            # Process URLs
            successful_domains = self._process_urls(urls, templates)
            
            # Post-processing
            if successful_domains:
                self._post_process(urls)
            else:
                self.banner.add_status("No successful domains to post-process", "warning")
            
            self.banner.update_progress(4, 4, "Finalizing")
            return True
            
        except KeyboardInterrupt:
            self.banner.add_status("Process interrupted by user", "warning")
            return False
        except Exception as e:
            self.banner.show_error(f"Unexpected error: {e}")
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
            self.banner.add_status(f"Processing URL {i}/{len(urls)}: {url}")
            
            domain = self.domain_handler.extract_domain(url)

            # Clear domain files only once per domain (for multiple URLs same domain)
            if domain and domain not in processed_domains:
                self.output_handler.clear_domain_files(domain)  # Only clears if directory exists
                processed_domains.add(domain)
            
            # Process the URL and check if we got results
            success = self.url_processor.process_url(url, templates)
            
            if success and domain:
                if domain not in successful_domains:
                    successful_domains.append(domain)
            elif domain:
                if domain not in skipped_domains and domain not in successful_domains:
                    skipped_domains.append(domain)
        
        return successful_domains
    
    def _post_process(self, urls):
        """Handle post-processing tasks"""
        self.banner.update_progress(3, 4, "Post-processing")
        self.banner.add_status("Cleaning up JSON files...")
        self.converter.clean_json_files(urls)  # This will only process existing files
        self.banner.add_status("JSON cleanup completed", "success")
        
        self.converter.generate_mermaid(urls)  # This will only process domains with data
    
    def _cleanup(self):
        """Clean up resources"""
        self.banner.add_status("Cleaning up resources...")
        self.web_requests.close_session()
        self.banner.add_status("Session closed", "success")

def main():
    """Entry point - create and run the application"""
    app = JSauceApp()
    success = app.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()