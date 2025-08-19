from src import config
import os

class OutFileHandler:
    def __init__(self):
        pass

    # If existing data exists in output files, it will be cleared before the script runs (once per domain)
    def clear_domain_files(self, domain):
        """Clear output files for a domain (called once per domain)"""
        os.makedirs(f"{config.OUTPUT_DIR}/{domain}", exist_ok=True)
        for suffix in ['endpoints_found.txt', 'endpoints_detailed.json', 'endpoints_for_db.json', 'endpoint_stats.json']:
            try:
                open(f"{config.OUTPUT_DIR}/{domain}/{domain}_{suffix}", 'w').close()
            except:
                pass

    def create_directories(self):
        """Create necessary directories for output files"""
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        os.makedirs(config.DATA_DIR, exist_ok=True)
        os.makedirs(f"{config.JS_FILE_DIR}", exist_ok=True)
        os.makedirs(f"{config.URL_CONTENT_DIR}", exist_ok=True)