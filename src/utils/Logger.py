# verbose logging -v -vv -vvv
from enum import IntEnum
import logging
import sys
import os

class VerbosityLevel(IntEnum):
    SILENT = 0
    NORMAL = 1
    VERBOSE = 2
    DEBUG = 3

class LoggingConfig:
    def __init__(self, verbosity_level=0, banner=None, log_file=None):
        self.verbosity_level = verbosity_level
        self.banner = banner

        # setup logging
        self.logger = logging.getLogger('jsauce')
        self.logger.setLevel(self._get_log_level()) # grab log level

        # clear existing handlers
        self.logger.handlers.clear()

        # add console handler if -v > 0
        if verbosity_level > 0:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s]', datefmt='%H:%M:%S')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        # add file handler to export logs to if -v is specified
        if log_file:
            try:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)

                # Always log at least INFO level to file
                if self.logger.level > logging.INFO:
                    self.logger.setLevel(logging.INFO)
            except Exception as e:
                print(f"Warning: Could not create log file {log_file}: {e}")
            
    # Log levels mapped to verbosity
    def _get_log_level(self):
        if self.verbosity_level == VerbosityLevel.DEBUG:
            return logging.DEBUG
        elif self.verbosity_level >= VerbosityLevel.VERBOSE:
            return logging.INFO
        elif self.verbosity_level >= VerbosityLevel.NORMAL:
            return logging.WARNING
        else:
            return logging.CRITICAL


    """now we need to set functions for each verosity level"""

    def debug(self, message, *args, **kwargs):
        if self.verbosity_level >= VerbosityLevel.DEBUG:
            self.logger.debug(message, *args, **kwargs)
            if self.banner:
                self.banner.add_status(f"[DEBUG] {message}", "info")

    def verbose(self, message, *args, **kwargs):
        if self.verbosity_level >= VerbosityLevel.VERBOSE:
            self.logger.info(message, *args, **kwargs)
            if self.banner:
                self.banner.add_status(f"[VERBOSE] {message}", "info")

    def info(self, message, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)
        if self.banner:
            self.banner.add_status(f"[INFO] {message}", "info")

    def success(self, message, *args, **kwargs):
        self.logger.info(message, *args, **kwargs)
        if self.banner:
            self.banner.add_status(f"[SUCCESS] {message}", "success")

    def warning(self, message, *args, **kwargs):
        self.logger.warning(message, *args, **kwargs)
        if self.banner:
            self.banner.add_status(f"[WARNING] {message}", "warning")

    def error(self, message, *args, **kwargs):
        self.logger.error(message, *args, **kwargs)
        if self.banner:
            self.banner.add_status(f"[ERROR] {message}", "error")


    """Create log levels for each package that is used as well"""

    def log_request_details(self, url, status_code, content_length):
        self.verbose(f"HTTP Request Details - URL: {url}, Status Code: {status_code}, Content Length: {content_length}")

    def log_js_analysis(self, js_url, patterns_found, total_patterns):
        self.verbose(f"JS Analysis - URL: {js_url}, Patterns Found: {patterns_found}, Total Patterns: {total_patterns}")

    def log_pattern_match(self, pattern, matches, category):
        self.verbose(f"Pattern Match - Pattern: {pattern}, Matches: {matches}, Category: {category}")

    def log_template_loading(self, template_file, categories_count):
        self.verbose(f"Template Loading - File: {template_file}, Categories Count: {categories_count}")

    def log_file_operation(self, operation, file_path, success=True):
        self.verbose(f"{operation} File - Path: {file_path}, Success: {success}")

    def log_processing_stats(self, domain, total_content_found, has_any_findings, je_files_with_findings, js_files_processed):
        self.info(f"Processing Stats - Domain: {domain}, Endpoints Found: {total_content_found}, Has Findings: {has_any_findings}, JS Files with Findings: {je_files_with_findings}/{js_files_processed}")


class NullLogger:
    """A null logger that does nothing - used as fallback when -v is not set"""
    def debug(self, message, *args, **kwargs):
        pass
    
    def verbose(self, message, *args, **kwargs):
        pass
    
    def info(self, message, message_type="success", *args, **kwargs):
        pass
    
    def success(self, message, *args, **kwargs):
        pass
    
    def warning(self, message, *args, **kwargs):
        pass
    
    def error(self, message, *args, **kwargs):
        pass
    
    def log_request_details(self, url, status_code, content_length):
        pass
    
    def log_js_analysis(self, js_url, patterns_found, total_patterns):
        pass
    
    def log_pattern_match(self, pattern, matches, category):
        pass
    
    def log_template_loading(self, template_file, categories_count):
        pass
    
    def log_file_operation(self, operation, file_path, success=True):
        pass
    
    def log_processing_stats(self, domain, endpoints_found, has_findings, js_files_with_findings, js_files_processed):
        pass

# Global logger instance ---> might move to main later, we'll see
_logger_instance = None

# get global logger instance
def get_logger():
    global _logger_instance
    if _logger_instance is None:
        return NullLogger()
    return _logger_instance

def initialize_logger(verbosity_level, banner=None, log_file=None):
    global _logger_instance
    _logger_instance = LoggingConfig(verbosity_level, banner, log_file)
    return _logger_instance



            
        
        
