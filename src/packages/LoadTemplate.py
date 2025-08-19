# Load template files that are used as search strings (regex)

from src import config
import os
from src.packages.EndpointProcessor import EndpointProcessor
from src.utils.Banner import Banner

jsauce_banner = Banner()

class LoadTemplate:
    def __init__(self, file_path):
        self.file_path = file_path
        self.lines = []
        self.read_file()

    def read_file(self):
        with open(self.file_path, 'r') as file:
            self.lines = file.readlines()

    def get_lines(self):
        return self.lines
    
    def load_patterns(self):
        """Load patterns from YAML or text format"""
        processor = EndpointProcessor()
        yaml_path = config.DEFAULT_TEMPLATE.replace('.txt', '.yaml')
        
        if os.path.exists(yaml_path):
            jsauce_banner.add_status(f"Loading YAML: {yaml_path}")
            templates = processor.load_patterns_from_yaml(yaml_path)
            if templates:
                return templates, processor
        
        loader = LoadTemplate(config.DEFAULT_TEMPLATE)
        templates = processor.parse_templates_by_category(loader.get_lines())
        return templates, processor