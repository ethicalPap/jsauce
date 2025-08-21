# Load template files that are used as search strings (regex)

import os
import yaml
import time
from src.utils.Logger import get_logger

class LoadTemplate:
    def __init__(self, file_path, banner, category_processor):
        self.file_path = file_path
        self.lines = []
        self.banner = banner
        self.category_processor = category_processor
        self.logger = get_logger()
        
        self.logger.debug(f"Initializing LoadTemplate with file: {file_path}")
        self.read_file()

    def read_file(self):
        """Read template file and store lines"""
        self.logger.debug(f"Reading template file: {self.file_path}")
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                self.lines = file.readlines()
            
            self.logger.info(f"Successfully read template file: {len(self.lines)} lines from {self.file_path}")
            self.logger.debug(f"File size: {os.path.getsize(self.file_path)} bytes")
            
        except FileNotFoundError:
            self.logger.error(f"Template file not found: {self.file_path}")
            self.banner.show_error(f"Template file not found: {self.file_path}")
            self.lines = []
        except PermissionError:
            self.logger.error(f"Permission denied reading template file: {self.file_path}")
            self.banner.show_error(f"Permission denied: {self.file_path}")
            self.lines = []
        except Exception as e:
            self.logger.error(f"Error reading template file {self.file_path}: {e}")
            self.banner.show_error(f"Error reading template: {e}")
            self.lines = []

    def get_lines(self):
        """Return loaded template lines"""
        self.logger.debug(f"Returning {len(self.lines)} template lines")
        return self.lines
    
    def load_patterns(self):
        """Load patterns from YAML or text format"""
        self.logger.debug("Starting pattern loading process")
        
        # Try YAML format first
        yaml_path = self.file_path.replace('.txt', '.yaml')
        
        if os.path.exists(yaml_path):
            self.logger.info(f"Found YAML template file: {yaml_path}")
            self.banner.add_status(f"Loading YAML: {yaml_path}")
            
            templates = self.load_patterns_from_yaml(yaml_path)
            if templates:
                self.logger.success(f"Successfully loaded {len(templates)} template categories from YAML")
                return templates, self.category_processor
            else:
                self.logger.warning("YAML loading failed, falling back to text format")
        else:
            self.logger.debug(f"YAML file not found: {yaml_path}, trying text format")
        
        # Fallback to text format
        self.logger.info(f"Loading patterns from text file: {self.file_path}")
        loader = LoadTemplate(self.file_path, self.banner, self.category_processor)
        templates = self.category_processor.parse_templates_by_category(loader.get_lines())
        
        if templates:
            self.logger.success(f"Successfully loaded {len(templates)} template categories from text file")
        else:
            self.logger.error("Failed to load any templates from text file")
        
        return templates, self.category_processor
    
    def load_patterns_from_yaml(self, yaml_file_path):
        """Load regex patterns from YAML file"""
        self.logger.debug(f"Loading YAML patterns from: {yaml_file_path}")
        
        try:
            # Check file accessibility
            if not os.access(yaml_file_path, os.R_OK):
                self.logger.error(f"Cannot read YAML file: {yaml_file_path}")
                return {}
            
            file_size = os.path.getsize(yaml_file_path)
            self.logger.debug(f"YAML file size: {file_size} bytes")
            
            with open(yaml_file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self.logger.debug("Successfully parsed YAML content")
            
            if not data or not isinstance(data, dict):
                self.logger.warning(f"Invalid YAML structure in {yaml_file_path}: expected dict, got {type(data)}")
                self.banner.show_error(f"Warning: Invalid YAML file {yaml_file_path}")
                time.sleep(2)
                return {}
            
            templates = {}
            total_patterns = 0
            
            for category, cat_data in data.items():
                if isinstance(cat_data, dict) and 'patterns' in cat_data:
                    pattern_count = len(cat_data['patterns'])
                    templates[category] = {p: p for p in cat_data['patterns']}
                    total_patterns += pattern_count
                    
                    self.logger.verbose(f"Loaded category '{category}': {pattern_count} patterns")
                    
                    # Log category description if available
                    if 'description' in cat_data:
                        self.logger.debug(f"Category '{category}' description: {cat_data['description']}")
                    
                    # Log sensitive flag if present
                    if cat_data.get('sensitive', False):
                        self.logger.debug(f"Category '{category}' marked as sensitive")
                else:
                    self.logger.warning(f"Skipping invalid category '{category}': missing 'patterns' key or invalid structure")
            
            self.templates_by_category = templates
            
            self.logger.info(f"Successfully loaded {len(templates)} categories with {total_patterns} total patterns")
            self.banner.add_status(f"Total categories: {len(templates)}")
            
            # Log summary of top categories by pattern count
            if templates:
                sorted_categories = sorted(templates.items(), key=lambda x: len(x[1]), reverse=True)
                top_5 = sorted_categories[:5]
                self.logger.verbose(f"Top categories by pattern count: {[(cat, len(patterns)) for cat, patterns in top_5]}")
            
            return templates
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in {yaml_file_path}: {e}")
            self.banner.show_error(f"YAML parsing error: {e}")
            time.sleep(2)
            return {}
        except FileNotFoundError:
            self.logger.error(f"YAML file not found: {yaml_file_path}")
            self.banner.show_error(f"YAML file not found: {yaml_file_path}")
            time.sleep(2)
            return {}
        except PermissionError:
            self.logger.error(f"Permission denied reading YAML file: {yaml_file_path}")
            self.banner.show_error(f"Permission denied: {yaml_file_path}")
            time.sleep(2)
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error loading YAML {yaml_file_path}: {e}")
            self.banner.show_error(f"Error loading YAML: {e}")
            time.sleep(2)
            return {}
    
    # def parse_templates_by_category(self, template_lines):
    #     """Legacy text file parser"""
    #     self.logger.debug(f"Parsing {len(template_lines)} lines from text template")
        
    #     templates = {}
    #     current_category = None
    #     total_patterns = 0
    #     skipped_lines = 0
        
    #     for line_num, line in enumerate(template_lines, 1):
    #         line = line.strip()
            
    #         if not line:
    #             continue
            
    #         if line.startswith('#[') and line.endswith(']'):
    #             current_category = line[2:-1]
    #             templates[current_category] = {}
    #             self.logger.debug(f"Found category at line {line_num}: '{current_category}'")
                
    #         elif current_category and line:
    #             # Skip comment lines
    #             if line.startswith('#'):
    #                 skipped_lines += 1
    #                 self.logger.debug(f"Skipping comment at line {line_num}: {line[:50]}...")
    #                 continue
                
    #             templates[current_category][line] = line
    #             total_patterns += 1
    #             self.logger.debug(f"Added pattern to '{current_category}': {line[:50]}...")
                
    #         elif line and not current_category:
    #             self.logger.warning(f"Pattern outside category at line {line_num}: {line[:50]}...")
    #             skipped_lines += 1
        
    #     # Log summary statistics
    #     self.logger.info(f"Text template parsing complete:")
    #     self.logger.info(f"  - Categories: {len(templates)}")
    #     self.logger.info(f"  - Total patterns: {total_patterns}")
    #     self.logger.info(f"  - Skipped lines: {skipped_lines}")
        
    #     # Log category breakdown
    #     for category, patterns in templates.items():
    #         self.logger.verbose(f"Category '{category}': {len(patterns)} patterns")
        
    #     if not templates:
    #         self.logger.error("No templates were parsed from text file")
        
    #     self.templates_by_category = templates
    #     return templates