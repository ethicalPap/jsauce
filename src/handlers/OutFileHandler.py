from src import config
import os

class OutFileHandler:
    def __init__(self):
        pass

    # If existing data exists in output files, it will be cleared before the script runs (once per domain)
    def clear_domain_files(self, domain):
        """Clear output files for a domain - but only if directory exists"""
        domain_path = f"{config.OUTPUT_DIR}/{domain}"
        
        # Only clear if directory already exists (from previous runs)
        if os.path.exists(domain_path):
            for suffix in ['contents_found.txt', 'contents_detailed.json', 'contents_for_db.json', 'content_stats.json']:
                file_path = f"{domain_path}/{domain}_{suffix}"
                try:
                    if os.path.exists(file_path):
                        open(file_path, 'w').close()  # Clear existing file
                except:
                    pass

    def ensure_base_directories(self):
        """Create necessary directories for output files"""
        os.makedirs(config.DATA_DIR, exist_ok=True)
        os.makedirs(f"{config.JS_FILE_DIR}", exist_ok=True)
        os.makedirs(f"{config.URL_CONTENT_DIR}", exist_ok=True)