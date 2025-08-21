
# handle input files and single URLs
class InputHandler:
    def __init__(self, webrequests):
        self.webrequests = webrequests

    def get_input_urls(self, input_file=None, single_url=None):
        """Read URLs from input file or return single URL"""
        urls = []
        
        try:
            if single_url:
                # Handle single URL input
                if not single_url.strip():
                    raise ValueError("Single URL cannot be empty")
                
                # Skip .js files for single URL input too
                if single_url.strip().endswith('.js'):
                    raise ValueError("Direct .js files are not supported as input")
                    
                processed_url = self.webrequests.add_protocol_if_missing(single_url.strip())
                urls.append(processed_url)
                
            elif input_file:
                # Handle file input (existing logic)
                with open(input_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and not line.endswith('.js'): #skip .js for now
                            urls.append(self.webrequests.add_protocol_if_missing(line))
            else:
                raise ValueError("Either input_file or single_url must be provided")
                            
        except FileNotFoundError:
            print(f"Error: Input file '{input_file}' not found")
            exit(1)
        except ValueError as e:
            print(f"Error: {e}")
            exit(1)
        except Exception as e:
            print(f"Error reading input: {e}")
            exit(1)
            
        return urls