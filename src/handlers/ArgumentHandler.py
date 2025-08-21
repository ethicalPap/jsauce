import argparse
from src import config
from src.utils.Logger import get_logger
import os
import glob

class ArgumentHandler:
    def __init__(self):
        self.parser = None
        self.args = None
        self.logger = get_logger()

    """
    arg brainstorm
    -i --input
    -t --template

    --no-diagrams? --> possible but needed?
    - add timeout?
    - add option to select output folder?
    - add ratelimit option?
    - add verbosity
    - user-agent modes [random, stealth, or none]?
    - retries?
    - d domain?


    """

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description='.js Content Mapping Tool',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
        Usage:
            python3 jsauce.py -i <inputfile>.txt -t <templates> 
            python3 jsauce.py -u <single_url> -t <templates>
        
        Template Examples:
            python3 jsauce.py -u https://example.com -t api/
            python3 jsauce.py -u https://example.com -t security/injection/
            python3 jsauce.py -u https://example.com -t templates/api/endpoints.yaml
            python3 jsauce.py -u https://example.com -t auth/
            python3 jsauce.py -u https://example.com -t admin/admin-panels.yaml
            ''' # syntax maybe -i for input file and -t for template
        )

        # mutually exclusive group for input options (mandatory)
        input_group = parser.add_mutually_exclusive_group(required=True)

        input_group.add_argument(
            '-i', '--input',
            help='Text file containing URLs to scan (one URL per line)'
        )

        input_group.add_argument(
            '-u', '--url',
            help='Single URL to scan'
        )

        parser.add_argument(
            '-t', '--template',
            default='/', # default is all templates
            help='Template path: folder (api/), subfolder (security/injection/), or specific file (api/endpoints.yaml)'
        )

        """legacy, not needed anymore"""
        # parser.add_argument(
        #     '-tf', '--templatefile',
        #     help='Path to custom YAML Template file'
        # )

        # verbose logging
        parser.add_argument(
            '-v', '--verbose',
            action='count',
            default=0,
            help='Increate verbosity level (use -v -vv -vvv for more logging detail)'
        )

        self.parser = parser
        self.args = parser.parse_args()
        return self.args

    # get template files
    def get_templates(self, template_arg):
        self.logger.debug(f"Processing template argument: {template_arg}")
        
        template_base_dir = config.TEMPLATES
        template_path = template_arg.rstrip('/')
        
        self.logger.debug(f"Template base directory: {template_base_dir}")
        self.logger.debug(f"Processed template path: {template_path}")
        
        # Handle different cases
        if template_path.endswith('.yaml') or template_path.endswith('.yml'):
            # Specific file specified
            self.logger.debug("Template path appears to be a specific YAML file")
            
            if os.path.isabs(template_path):
                self.logger.debug(f"Using absolute path: {template_path}")
                if os.path.exists(template_path):
                    self.logger.success(f"Found template file: {template_path}")
                    return [template_path]
                else:
                    self.logger.error(f"Template file not found: {template_path}")
                    return []
            else:
                full_path = os.path.join(template_base_dir, template_path)
                self.logger.debug(f"Using relative path, full path: {full_path}")
                if os.path.exists(full_path):
                    self.logger.success(f"Found template file: {full_path}")
                    return [full_path]
                else:
                    self.logger.error(f"Template file not found: {full_path}")
                    return []
        else:
            # Directory specified - scan for YAML files
            self.logger.debug("Template path appears to be a directory")
            
            if os.path.isabs(template_path):
                search_dir = template_path
                self.logger.debug(f"Using absolute directory path: {search_dir}")
            else:
                search_dir = os.path.join(template_base_dir, template_path)
                self.logger.debug(f"Using relative directory path: {search_dir}")
            
            if not os.path.exists(search_dir):
                # Fallback to default if path doesn't exist
                self.logger.warning(f"Template directory not found: {search_dir}")
                search_dir = os.path.join(template_base_dir, 'api')
                self.logger.warning(f"Falling back to default directory: {search_dir}")
            
            template_files = self._scan_directory_for_templates(search_dir)
            self.logger.info(f"Found {len(template_files)} template files in {search_dir}")
            return template_files
    
    # scan templates dir for yaml files
    def _scan_directory_for_templates(self, directory):
        self.logger.debug(f"Scanning directory for templates: {directory}")
        template_files = []
        
        if not os.path.exists(directory):
            self.logger.error(f"Directory does not exist: {directory}")
            return template_files
        
        # Search for YAML files recursively
        yaml_patterns = ['*.yaml', '*.yml']
        for pattern in yaml_patterns:
            search_pattern = os.path.join(directory, '**', pattern)
            found_files = glob.glob(search_pattern, recursive=True)
            template_files.extend(found_files)
            self.logger.debug(f"Found {len(found_files)} files matching pattern {pattern} (recursive)")
        
        # Also search in the immediate directory
        for pattern in yaml_patterns:
            search_pattern = os.path.join(directory, pattern)
            found_files = glob.glob(search_pattern)
            template_files.extend(found_files)
            self.logger.debug(f"Found {len(found_files)} files matching pattern {pattern} (immediate)")
        
        # Remove duplicates and sort
        template_files = list(set(template_files))
        template_files.sort()
        
        self.logger.debug(f"Total unique template files found: {len(template_files)}")
        for template_file in template_files:
            self.logger.debug(f"  - {template_file}")
        
        return template_files
        
    # get logging selection from args
    def get_verbosity_level(self):
        return getattr(self.args, 'verbose', 0)
    
    # list available templates
    def list_available_templates(self):
        """List all available template categories and files"""
        template_base_dir = config.TEMPLATES
        self.logger.debug(f"Listing available templates in: {template_base_dir}")
        
        if not os.path.exists(template_base_dir):
            self.logger.error(f"Template base directory does not exist: {template_base_dir}")
            return {}
        
        template_structure = {}
        
        for root, dirs, files in os.walk(template_base_dir):
            yaml_files = [f for f in files if f.endswith(('.yaml', '.yml'))]
            if yaml_files:
                rel_path = os.path.relpath(root, template_base_dir)
                if rel_path == '.':
                    rel_path = 'root'
                template_structure[rel_path] = yaml_files
                self.logger.debug(f"Found {len(yaml_files)} templates in {rel_path}: {yaml_files}")
        
        self.logger.info(f"Template structure discovered: {len(template_structure)} categories")
        return template_structure