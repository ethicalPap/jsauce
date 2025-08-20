import argparse
from src import config

class ArgumentHandler:
    def __init__(self):
        self.parser = None
        self.args = None

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
            python3 jsauce.py -i <inputfile>.txt -t <template> 
        Examples:
            python3 jsauce.py -i url_list.txt -t endpoints
            ''' # syntax maybe -i for input file and -t for template
        )

        parser.add_argument(
            '-i', '--input',
            help='Text file containing URLs to scan (one URL per line)'
        )

        parser.add_argument(
            '-t', '--template',
            choices=['endpoints', 'security', 'custom'], # need to add logic to allow for these, maybe folder based like nuclei? (i.e templates/endpoints/*)
            default='endpoint',
            help='Template to use for content discovery (default: endpoints)'
        )

        parser.add_argument(
            '-tf', '--templatefile',
            help='Path to custom YAML Template file'
        )

        self.parser = parser
        self.args = parser.parse_args()
        return self.args

    # get specified templates based on args
    def get_templates(self, args):
        # if -tf is specified, return the exact file specified after that
        if self.args.templatefile:
            return args.templatefile
        
        # else handle other cases
        elif self.args.template.lower().rstrip('/') == 'security':
            return config.SECURITY_TEMPLATES
        elif self.args.template.lower().rstrip('/') == 'endpoints':
            return config.ENDPOINTS_TEMPLATES
        elif self.args.template.lower().rstrip('/') == 'custom':
            return config.CUSTOM_TEMPLATES # need to add logic for scanning a folder for templates
        else:
            return config.ENDPOINTS_TEMPLATES # if nothing specified, default to Endpoint Template