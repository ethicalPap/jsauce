from src.packages.WebRequests import WebRequests

# Initialize processors
webrequests = WebRequests()


class InputFileHandler:
    def __init__(self):
        pass

    def get_input_urls(self, input_file):
        """Read URLs from input file"""
        urls = []
        try:
            with open(input_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.endswith('.js'):
                        urls.append(webrequests.add_protocol_if_missing(line))
                        # print(line)
        except Exception as e:
            print(f"Error reading input file: {e}")
            exit(1)
        return urls