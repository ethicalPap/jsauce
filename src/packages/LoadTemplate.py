# Load template files that are used as search strings (regex)

import os
import yaml
import time
from src.utils.Logger import get_logger

class LoadTemplate:

    # init a list of files or single fiel (YAML)
    def __init__(self, template_paths, banner, category_processor):
        if isinstance(template_paths, str):
            self.template_paths = [template_paths]
        else:
            self.template_paths = template_paths
        
        self.banner = banner
        self.category_processor = category_processor
        self.logger = get_logger()
        
        self.logger.debug(f"Initializing LoadTemplate with {len(self.template_paths)} template files")
        for path in self.template_paths:
            self.logger.debug(f"Template path: {path}")

    # load patterns from templates
    def load_patterns(self):
        self.logger.debug("Starting pattern loading process for multiple templates")
        
        all_templates = {}
        loaded_files = 0
        failed_files = 0
        total_patterns = 0
        
        for template_path in self.template_paths:
            self.logger.debug(f"Loading template file: {template_path}")
            
            if not os.path.exists(template_path):
                self.logger.warning(f"Template file not found: {template_path}")
                failed_files += 1
                continue
            
            templates = self.load_patterns_from_yaml(template_path)
            
            if templates:
                # Merge templates with conflict resolution
                for category, patterns in templates.items():
                    if category in all_templates:
                        # Merge patterns for existing category
                        all_templates[category].update(patterns)
                        self.logger.debug(f"Merged {len(patterns)} patterns into existing category '{category}'")
                    else:
                        # New category
                        all_templates[category] = patterns
                        self.logger.debug(f"Added new category '{category}' with {len(patterns)} patterns")
                
                file_pattern_count = sum(len(patterns) for patterns in templates.values())
                total_patterns += file_pattern_count
                loaded_files += 1
                
                self.logger.success(f"Loaded {len(templates)} categories, {file_pattern_count} patterns from {os.path.basename(template_path)}")
            else:
                self.logger.error(f"Failed to load patterns from {template_path}")
                failed_files += 1
        
        # Log summary
        self.logger.info(f"Template loading summary:")
        self.logger.info(f"  - Files loaded: {loaded_files}")
        self.logger.info(f"  - Files failed: {failed_files}")
        self.logger.info(f"  - Total categories: {len(all_templates)}")
        self.logger.info(f"  - Total patterns: {total_patterns}")
        
        if not all_templates:
            self.logger.error("No templates were loaded successfully")
            self.banner.show_error("No templates were loaded successfully")
            return {}, self.category_processor
        
        self.logger.success(f"Successfully loaded {len(all_templates)} template categories from {loaded_files} files")
        self.banner.add_status(f"Loaded {len(all_templates)} categories from {loaded_files} template files")
        
        return all_templates, self.category_processor
    
    # load regex patterns from YAML
    def load_patterns_from_yaml(self, yaml_file_path):
        """Load regex patterns from a single YAML file"""
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
            
            if not data:
                self.logger.warning(f"Empty or invalid YAML file: {yaml_file_path}")
                return {}
            
            if not isinstance(data, dict):
                self.logger.warning(f"Invalid YAML structure in {yaml_file_path}: expected dict, got {type(data)}")
                return {}
            
            templates = {}
            file_patterns = 0
            
            # Process template data
            for category, cat_data in data.items():
                # Skip metadata sections
                if category in ['info', 'id', 'variables', 'requests']:
                    self.logger.debug(f"Skipping metadata section: {category}")
                    continue
                
                # Only process valid pattern categories
                if isinstance(cat_data, dict) and 'patterns' in cat_data:
                    pattern_count = len(cat_data['patterns'])
                    templates[category] = {p: p for p in cat_data['patterns']}
                    file_patterns += pattern_count
                    
                    self.logger.verbose(f"Loaded category '{category}': {pattern_count} patterns")
                    
                    # Log category description if available
                    if 'description' in cat_data:
                        self.logger.debug(f"Category '{category}' description: {cat_data['description']}")
                    
                    # Log sensitive flag if present
                    if cat_data.get('sensitive', False):
                        self.logger.debug(f"Category '{category}' marked as sensitive")
                else:
                    # Only warn about unexpected categories (not metadata)
                    if category not in ['info', 'id', 'variables', 'requests']:
                        self.logger.warning(f"Skipping invalid category '{category}': missing 'patterns' key or invalid structure")
                    else:
                        self.logger.debug(f"Skipping known metadata section: {category}")
            
            self.logger.verbose(f"Loaded {len(templates)} categories with {file_patterns} patterns from {os.path.basename(yaml_file_path)}")
            return templates
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAML parsing error in {yaml_file_path}: {e}")
            return {}
        except FileNotFoundError:
            self.logger.error(f"YAML file not found: {yaml_file_path}")
            return {}
        except PermissionError:
            self.logger.error(f"Permission denied reading YAML file: {yaml_file_path}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error loading YAML {yaml_file_path}: {e}")
            return {}
    
    def _parse_template(self, data, file_path):
        """Parse nuclei-style template format"""
        self.logger.debug(f"Parsing nuclei-style template: {file_path}")
        
        templates = {}
        info = data.get('info', {})
        
        # Get template info
        template_name = info.get('name', os.path.basename(file_path).replace('.yaml', ''))
        template_category = info.get('tags', ['misc'])[0] if info.get('tags') else 'misc'
        
        # Extract patterns from requests
        patterns = []
        requests = data.get('requests', [])
        
        for request in requests:
            # Look for patterns in different places
            if 'matchers' in request:
                for matcher in request['matchers']:
                    if matcher.get('type') == 'regex':
                        patterns.extend(matcher.get('regex', []))
                    elif matcher.get('type') == 'word':
                        # Convert word matchers to regex patterns
                        words = matcher.get('words', [])
                        for word in words:
                            # Escape special regex characters and create pattern
                            escaped_word = word.replace('.', '\\.').replace('/', '\\/')
                            patterns.append(f"[\\'\"``]({escaped_word})[\\'\"``]")
        
        if patterns:
            templates[template_category] = {p: p for p in patterns}
            self.logger.debug(f"Nuclei template '{template_name}' -> category '{template_category}': {len(patterns)} patterns")
        
        return templates
    
    def get_template_info(self):
        """Get information about loaded templates"""
        info = {
            'total_files': len(self.template_paths),
            'files': []
        }
        
        for path in self.template_paths:
            file_info = {
                'path': path,
                'exists': os.path.exists(path),
                'size': os.path.getsize(path) if os.path.exists(path) else 0,
                'basename': os.path.basename(path)
            }
            info['files'].append(file_info)
        
        return info