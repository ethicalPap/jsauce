
# handle input files
class InputFileHandler:
    def __init__(self, webrequests):
        self.webrequests = webrequests

    def get_input_urls(self, input_file):
        """Read URLs from input file"""
        urls = []
        try:
            with open(input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.endswith('.js'): #skip .js for now
                        urls.append(self.webrequests.add_protocol_if_missing(line))
                        # print(line)
        except Exception as e:
            print(f"Error reading input file: {e}")
            exit(1)
        return urls