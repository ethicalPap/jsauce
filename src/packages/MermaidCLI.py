import subprocess
import platform

class MermaidCLI:
    def __init__(self):
        pass
    
    def render(self, input_file, output_file):
        try:
            # On Windows, use shell=True to access PATH properly
            subprocess.run(
                ['mmdc', '-i', input_file, '-o', output_file, '-t', 'dark'],
                check=True,
                shell=True if platform.system() == 'Windows' else False
            )
        except subprocess.CalledProcessError as e:
            print(f"Error rendering Mermaid file: {e}")
            raise