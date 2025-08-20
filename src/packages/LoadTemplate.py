# Load template files that are used as search strings (regex)

import os
import yaml
import time

class LoadTemplate:
    def __init__(self, file_path, banner, category_processor):
        self.file_path = file_path
        self.lines = []
        self.read_file()
        self.banner = banner
        self.category_processor = category_processor

    def read_file(self):
        with open(self.file_path, 'r') as file:
            self.lines = file.readlines()

    def get_lines(self):
        return self.lines
    
    def load_patterns(self):
        """Load patterns from YAML or text format"""
        yaml_path = self.file_path.replace('.txt', '.yaml')
        
        if os.path.exists(yaml_path):
            self.banner.add_status(f"Loading YAML: {yaml_path}")
            templates = self.load_patterns_from_yaml(yaml_path)
            if templates:
                return templates, self.category_processor
        
        loader = LoadTemplate(self.file_path)
        templates = self.category_processor.parse_templates_by_category(loader.get_lines())
        return templates, self.category_processor
    
    def load_patterns_from_yaml(self, yaml_file_path):
        """Load regex patterns from YAML file"""
        try:
            with open(yaml_file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or not isinstance(data, dict):
                self.banner.show_error(f"Warning: Invalid YAML file {yaml_file_path}")
                time.sleep(2)
                return {}
            
            templates = {}
            for category, cat_data in data.items():
                if isinstance(cat_data, dict) and 'patterns' in cat_data:
                    templates[category] = {p: p for p in cat_data['patterns']}
            
            self.templates_by_category = templates
            self.banner.add_status(f"Total categories: {len(templates)}")
            return templates
            
        except Exception as e:
            self.banner.show_error(f"Error loading YAML: {e}")
            time.sleep(2)
            return {}
    
    def parse_templates_by_category(self, template_lines):
        """Legacy text file parser"""
        templates = {}
        current_category = None
        
        for line_num, line in enumerate(template_lines, 1):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#[') and line.endswith(']'):
                current_category = line[2:-1]
                templates[current_category] = {}
            elif current_category and line:
                templates[current_category][line] = line
        
        self.templates_by_category = templates
        return templates