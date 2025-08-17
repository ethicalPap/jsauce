# Load template files that are used as search strings (regex)

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