from src import config
import os
import time

class OutFileHandler:
    def __init__(self, template):
        self.cleared_domains = set()  # Track which domains we've already cleared
        self.template = template

    def clear_domain_files(self, domain):
        """Clear output files for a domain - but only once per session"""
        # Avoid clearing the same domain multiple times in one session
        if domain in self.cleared_domains:
            return
        
        domain_path = f"{config.OUTPUT_DIR}/{domain}"
        
        # Only clear if directory already exists (from previous runs)
        if os.path.exists(domain_path):
            file_suffixes = [
                f'{self.template}_found.txt', 
                f'{self.template}_detailed.json', 
                f'{self.template}_for_db.json', 
                f'{self.template}_stats.json'
            ]
            
            for suffix in file_suffixes:
                file_path = f"{domain_path}/{domain}_{suffix}"
                try:
                    if os.path.exists(file_path):
                        # Create backup before clearing (safety net)
                        backup_path = f"{file_path}.pre_run_backup"
                        if os.path.getsize(file_path) > 0:  # Only backup non-empty files
                            import shutil
                            shutil.copy2(file_path, backup_path)
                        
                        # Clear the file
                        open(file_path, 'w').close()
                        
                except Exception as e:
                    print(f"Warning: Could not clear {file_path}: {e}")
        
        # Mark this domain as cleared
        self.cleared_domains.add(domain)

    def ensure_base_directories(self):
        """Create necessary directories for output files"""
        os.makedirs(config.DATA_DIR, exist_ok=True)
        os.makedirs(f"{config.JS_FILE_DIR}", exist_ok=True)
        os.makedirs(f"{config.URL_CONTENT_DIR}", exist_ok=True)
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    def safe_append_json(self, file_path, json_data):
        """Safely append JSON data to a file with error recovery"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        try:
            # Try to append the JSON object
            with open(file_path, 'a', encoding='utf-8') as f:
                import json
                json.dump(json_data, f, ensure_ascii=False)
                f.write('\n')  # Add newline for easier parsing later
            
        except Exception as e:
            print(f"Error appending to {file_path}: {e}")
            
            # Try to recover by creating a new file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump([json_data], f, indent=2, ensure_ascii=False)
                print(f"Recovered by creating new file: {file_path}")
                
            except Exception as e2:
                print(f"Failed to recover {file_path}: {e2}")
                return False
        
        return True

    def get_file_lock(self, file_path, timeout=5):
        """Simple file locking mechanism to prevent concurrent writes"""
        lock_file = f"{file_path}.lock"
        start_time = time.time()
        
        while os.path.exists(lock_file):
            if time.time() - start_time > timeout:
                # Force remove stale lock
                try:
                    os.remove(lock_file)
                except:
                    pass
                break
            time.sleep(0.1)
        
        # Create lock
        try:
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            return lock_file
        except:
            return None

    def release_file_lock(self, lock_file):
        """Release file lock"""
        try:
            if lock_file and os.path.exists(lock_file):
                os.remove(lock_file)
        except:
            pass