import os
import time

# JSAUCE ASCII banner with color
class Banner:
    def __init__(self):
        # ANSI color codes
        self.RED = "\033[31m"
        self.GREEN = "\033[32m"
        self.CYAN = "\033[36m"
        self.RESET = "\033[0m"
        
        # Store banner content for reuse
        self.banner = r"""
        ██╗███████╗ █████╗ ██╗   ██╗ ██████╗███████╗
        ██║██╔════╝██╔══██╗██║   ██║██╔════╝██╔════╝
        ██║███████╗███████║██║   ██║██║     █████╗  
  ██   ██║╚════██║██╔══██║██║   ██║██║     ██╔══╝  
  ╚█████╔╝███████║██║  ██║╚██████╔╝╚██████╗███████╗
    ╚════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝
                      JSauce: .js Content Mapping Tool
      """
        self.tagline = "                By Papv2 (ethicalPap)"
    
    def print_jsauce_banner(self):
        """Print the banner once (original method)"""
        print(self.RED + self.banner + self.RESET)
        print(self.CYAN + self.tagline + self.RESET)
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_frozen_banner(self, status_message="", progress=None):
        """
        Clear screen and print banner at top with status message
        This creates a 'frozen pane' effect
        """
        self.clear_screen()
        
        # Print banner at top
        print(self.RED + self.banner + self.RESET)
        print(self.CYAN + self.tagline + self.RESET)
        print("=" * 80)
        
        # Print status information below banner
        if progress:
            print(f"Progress: {progress}")
        if status_message:
            print(f"Status: {status_message}")
        if progress or status_message:
            print("-" * 80)
    
    def update_status(self, message, progress=None, delay=0):
        """
        Update the frozen banner with new status message
        Optional delay for visual effect
        """
        self.print_frozen_banner(message, progress)
        if delay > 0:
            time.sleep(delay)
    
    def show_completion(self, total_processed, details=None):
        """
        Show completion message with banner
        """
        self.clear_screen()
        print(self.RED + self.banner + self.RESET)
        print(self.CYAN + self.tagline + self.RESET)
        print("=" * 80)
        print(f"{self.GREEN}✓ ALL PROCESSING COMPLETED!{self.RESET}")
        print(f"Processed {total_processed} items total")
        
        if details:
            for detail in details:
                print(f"✓ {detail}")
        
        print("=" * 80)