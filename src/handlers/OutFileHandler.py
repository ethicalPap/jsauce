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
            for suffix in ['endpoints_found.txt', 'endpoints_detailed.json', 'endpoints_for_db.json', 'endpoint_stats.json']:
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