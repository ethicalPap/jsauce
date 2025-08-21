from src import config
import os
import time
from src.utils.Logger import get_logger

class OutFileHandler:
    def __init__(self, template):
        self.cleared_domains = set()  # Track which domains we've already cleared
        self.template = template
        self.logger = get_logger()
        
        self.logger.debug(f"Initializing OutFileHandler with template: {template}")

    def clear_domain_files(self, domain):
        """Clear output files for a domain - but only once per session"""
        self.logger.debug(f"Attempting to clear domain files for: {domain}")
        
        # Avoid clearing the same domain multiple times in one session
        if domain in self.cleared_domains:
            self.logger.debug(f"Domain {domain} already cleared in this session, skipping")
            return
        
        domain_path = f"{config.OUTPUT_DIR}/{domain}"
        self.logger.debug(f"Domain path: {domain_path}")
        
        # Only clear if directory already exists (from previous runs)
        if os.path.exists(domain_path):
            self.logger.verbose(f"Found existing domain directory: {domain_path}")
            
            file_suffixes = [
                f'{self.template}_found.txt', 
                f'{self.template}_detailed.json', 
                f'{self.template}_for_db.json', 
                f'{self.template}_stats.json'
            ]
            
            files_cleared = 0
            files_backed_up = 0
            files_skipped = 0
            files_failed = 0
            
            for suffix in file_suffixes:
                file_path = f"{domain_path}/{domain}_{suffix}"
                
                try:
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        self.logger.debug(f"Processing file: {file_path} ({file_size} bytes)")
                        
                        # Create backup before clearing (safety net)
                        backup_path = f"{file_path}.pre_run_backup"
                        
                        if file_size > 0:  # Only backup non-empty files
                            import shutil
                            shutil.copy2(file_path, backup_path)
                            files_backed_up += 1
                            self.logger.debug(f"Created backup: {backup_path}")
                        else:
                            self.logger.debug(f"Skipping backup for empty file: {file_path}")
                        
                        # Clear the file
                        open(file_path, 'w').close()
                        files_cleared += 1
                        self.logger.verbose(f"Cleared file: {file_path}")
                        
                    else:
                        files_skipped += 1
                        self.logger.debug(f"File does not exist, skipping: {file_path}")
                        
                except Exception as e:
                    files_failed += 1
                    error_msg = f"Warning: Could not clear {file_path}: {e}"
                    print(error_msg)  # Keep original print for backward compatibility
                    self.logger.error(f"Failed to clear {file_path}: {e}")
            
            # Log summary for this domain
            self.logger.info(f"Domain {domain} file clearing summary:")
            self.logger.info(f"  - Cleared: {files_cleared} files")
            self.logger.info(f"  - Backed up: {files_backed_up} files")
            self.logger.info(f"  - Skipped: {files_skipped} files")
            self.logger.info(f"  - Failed: {files_failed} files")
            
        else:
            self.logger.debug(f"Domain directory does not exist: {domain_path}")
        
        # Mark this domain as cleared
        self.cleared_domains.add(domain)
        self.logger.debug(f"Marked domain {domain} as cleared")

    def ensure_base_directories(self):
        """Create necessary directories for output files"""
        self.logger.debug("Ensuring base directories exist")
        
        directories = [
            config.DATA_DIR,
            config.JS_FILE_DIR,
            config.URL_CONTENT_DIR,
            config.OUTPUT_DIR
        ]
        
        created_dirs = 0
        existing_dirs = 0
        failed_dirs = 0
        
        for directory in directories:
            try:
                if os.path.exists(directory):
                    existing_dirs += 1
                    self.logger.debug(f"Directory already exists: {directory}")
                else:
                    os.makedirs(directory, exist_ok=True)
                    created_dirs += 1
                    self.logger.verbose(f"Created directory: {directory}")
                    
            except Exception as e:
                failed_dirs += 1
                self.logger.error(f"Failed to create directory {directory}: {e}")
        
        self.logger.info(f"Base directory setup complete:")
        self.logger.info(f"  - Created: {created_dirs} directories")
        self.logger.info(f"  - Already existed: {existing_dirs} directories")
        self.logger.info(f"  - Failed: {failed_dirs} directories")

    def safe_append_json(self, file_path, json_data):
        """Safely append JSON data to a file with error recovery"""
        self.logger.debug(f"Attempting to safely append JSON to: {file_path}")
        
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(file_path)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                self.logger.debug(f"Created directory: {dir_path}")
            
            # Check if file already exists and get size
            file_exists = os.path.exists(file_path)
            file_size = os.path.getsize(file_path) if file_exists else 0
            
            self.logger.debug(f"File exists: {file_exists}, Size: {file_size} bytes")
            
            # Try to append the JSON object
            with open(file_path, 'a', encoding='utf-8') as f:
                import json
                json.dump(json_data, f, ensure_ascii=False)
                f.write('\n')  # Add newline for easier parsing later
            
            new_size = os.path.getsize(file_path)
            self.logger.success(f"Successfully appended JSON to {file_path} ({file_size} -> {new_size} bytes)")
            return True
            
        except Exception as e:
            self.logger.warning(f"Error appending to {file_path}: {e}")
            print(f"Error appending to {file_path}: {e}")  # Keep original print
            
            # Try to recover by creating a new file
            try:
                self.logger.debug("Attempting recovery by creating new file")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    import json
                    json.dump([json_data], f, indent=2, ensure_ascii=False)
                
                recovery_size = os.path.getsize(file_path)
                self.logger.warning(f"Recovered by creating new file: {file_path} ({recovery_size} bytes)")
                print(f"Recovered by creating new file: {file_path}")  # Keep original print
                return True
                
            except Exception as e2:
                self.logger.error(f"Failed to recover {file_path}: {e2}")
                print(f"Failed to recover {file_path}: {e2}")  # Keep original print
                return False

    def get_file_lock(self, file_path, timeout=5):
        """Simple file locking mechanism to prevent concurrent writes"""
        lock_file = f"{file_path}.lock"
        self.logger.debug(f"Attempting to acquire file lock: {lock_file} (timeout: {timeout}s)")
        
        start_time = time.time()
        wait_count = 0
        
        while os.path.exists(lock_file):
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                self.logger.warning(f"Lock timeout after {timeout}s, forcing removal of stale lock: {lock_file}")
                # Force remove stale lock
                try:
                    os.remove(lock_file)
                    self.logger.debug("Successfully removed stale lock")
                except Exception as e:
                    self.logger.error(f"Failed to remove stale lock: {e}")
                break
                
            wait_count += 1
            if wait_count % 10 == 0:  # Log every second (10 * 0.1s)
                self.logger.debug(f"Waiting for lock {lock_file} ({elapsed:.1f}s elapsed)")
                
            time.sleep(0.1)
        
        # Create lock
        try:
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            self.logger.debug(f"Successfully acquired file lock: {lock_file}")
            return lock_file
            
        except Exception as e:
            self.logger.error(f"Failed to create lock file {lock_file}: {e}")
            return None

    def release_file_lock(self, lock_file):
        """Release file lock"""
        if not lock_file:
            self.logger.debug("No lock file to release")
            return
            
        self.logger.debug(f"Attempting to release file lock: {lock_file}")
        
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
                self.logger.debug(f"Successfully released file lock: {lock_file}")
            else:
                self.logger.debug(f"Lock file already removed: {lock_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to release lock file {lock_file}: {e}")

    def cleanup_old_backups(self, domain, max_age_hours=24):
        """Clean up old backup files for a domain"""
        self.logger.debug(f"Cleaning up old backups for domain: {domain}")
        
        domain_path = f"{config.OUTPUT_DIR}/{domain}"
        
        if not os.path.exists(domain_path):
            self.logger.debug(f"Domain path does not exist: {domain_path}")
            return
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        removed_files = 0
        total_size_removed = 0
        
        try:
            for filename in os.listdir(domain_path):
                if filename.endswith('.pre_run_backup'):
                    file_path = os.path.join(domain_path, filename)
                    
                    try:
                        file_stat = os.stat(file_path)
                        file_age = current_time - file_stat.st_mtime
                        
                        if file_age > max_age_seconds:
                            file_size = file_stat.st_size
                            os.remove(file_path)
                            
                            removed_files += 1
                            total_size_removed += file_size
                            
                            self.logger.debug(f"Removed old backup: {filename} (age: {file_age/3600:.1f}h, size: {file_size} bytes)")
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to process backup file {filename}: {e}")
            
            if removed_files > 0:
                self.logger.verbose(f"Cleanup complete for {domain}: removed {removed_files} old backups ({total_size_removed} bytes)")
            else:
                self.logger.debug(f"No old backups to remove for {domain}")
                
        except Exception as e:
            self.logger.error(f"Error during backup cleanup for {domain}: {e}")

    def get_domain_file_stats(self, domain):
        """Get statistics about files for a domain"""
        self.logger.debug(f"Getting file statistics for domain: {domain}")
        
        domain_path = f"{config.OUTPUT_DIR}/{domain}"
        
        if not os.path.exists(domain_path):
            self.logger.debug(f"Domain path does not exist: {domain_path}")
            return None
        
        stats = {
            'domain': domain,
            'total_files': 0,
            'total_size': 0,
            'files': {}
        }
        
        try:
            for filename in os.listdir(domain_path):
                file_path = os.path.join(domain_path, filename)
                
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_mtime = os.path.getmtime(file_path)
                    
                    stats['files'][filename] = {
                        'size': file_size,
                        'modified': file_mtime
                    }
                    
                    stats['total_files'] += 1
                    stats['total_size'] += file_size
            
            self.logger.debug(f"Domain {domain} statistics: {stats['total_files']} files, {stats['total_size']} bytes")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting statistics for domain {domain}: {e}")
            return None