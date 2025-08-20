import subprocess
import platform

class MermaidCLI:
    def __init__(self, banner):
        self.banner = banner
    
    def render(self, input_file, output_file):
        try:
            # On Windows, use shell=True to access PATH properly
            subprocess.run(
                ['mmdc', '-i', input_file, '-o', output_file, '-t', 'dark'],
                check=True,
                shell=True if platform.system() == 'Windows' else False
            )
        except subprocess.CalledProcessError as e:
            self.banner.show_error(f"Error rendering Mermaid file: {e}")
            raise

    def is_available(self):
        try:
            subprocess.run(['mmdc', '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True if platform.system() == 'Windows' else False)
            return True
        except:
            return False