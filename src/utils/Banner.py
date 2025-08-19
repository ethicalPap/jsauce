import os
import time
from collections import deque

# JSAUCE ASCII banner with color and persistent status
class Banner:
    def __init__(self, max_status_lines=10):
        # ANSI color codes
        self.RED = "\033[31m"
        self.GREEN = "\033[32m"
        self.CYAN = "\033[36m"
        self.YELLOW = "\033[33m"
        self.RESET = "\033[0m"
        self.BOLD = "\033[1m"
        
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
        
        # Persistent status log
        self.max_status_lines = max_status_lines
        self.status_log = deque(maxlen=max_status_lines)
        self.current_progress = None
        self.is_initialized = False
        
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
    
    def initialize_persistent_display(self):
        """Initialize the persistent display with banner"""
        self.clear_screen()
        print(self.RED + self.banner + self.RESET)
        print(self.CYAN + self.tagline + self.RESET)
        print("=" * 80)
        self.is_initialized = True
        self._refresh_display()
    
    def add_status(self, message, message_type="info"):
        """
        Add a status message to the persistent log
        message_type: 'info', 'success', 'warning', 'error'
        """
        timestamp = time.strftime("%H:%M:%S")
        
        # Color coding based on message type
        color = self.RESET
        prefix = "•"
        
        if message_type == "success":
            color = self.GREEN
            prefix = "✓"
        elif message_type == "warning":
            color = self.YELLOW
            prefix = "⚠"
        elif message_type == "error":
            color = self.RED
            prefix = "✗"
        elif message_type == "info":
            color = self.CYAN
            prefix = "•"
        
        # Truncate very long error messages to prevent display corruption
        if len(message) > 120:
            message = message[:117] + "..."
        
        formatted_message = f"{color}[{timestamp}] {prefix} {message}{self.RESET}"
        self.status_log.append(formatted_message)
        
        if self.is_initialized:
            self._refresh_display()
    
    def update_progress(self, current, total, description=""):
        """Update progress information"""
        if total > 0:
            percentage = (current / total) * 100
            progress_bar = self._create_progress_bar(percentage)
            self.current_progress = f"{description} [{current}/{total}] {progress_bar} {percentage:.1f}%"
        else:
            self.current_progress = f"{description} [{current}]"
        
        if self.is_initialized:
            self._refresh_display()
    
    def _create_progress_bar(self, percentage, width=30):
        """Create a visual progress bar"""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"|{bar}|"
    
    def _refresh_display(self):
        """Refresh the entire display by completely redrawing"""
        # Instead of cursor positioning, just clear and redraw everything
        self.clear_screen()
        
        # Print banner at top
        print(self.RED + self.banner + self.RESET)
        print(self.CYAN + self.tagline + self.RESET)
        print("=" * 80)
        
        # Print current progress if available
        if self.current_progress:
            print(f"{self.BOLD}Progress:{self.RESET} {self.current_progress}")
            print("-" * 80)
        
        # Print status log header
        print(f"{self.BOLD}Status Log:{self.RESET}")
        
        # Print status messages
        if self.status_log:
            for status in self.status_log:
                print(status)
        else:
            print(f"{self.CYAN}• Waiting for status updates...{self.RESET}")
        
        # Print separator
        print("-" * 80)
        
        # Flush output to ensure immediate display
        import sys
        sys.stdout.flush()
    
    def update_status(self, message, progress=None, delay=0, message_type="info"):
        """
        Enhanced update_status that uses persistent display
        """
        if not self.is_initialized:
            self.initialize_persistent_display()
        
        self.add_status(message, message_type)
        
        if delay > 0:
            time.sleep(delay)
    
    def show_completion(self, total_processed, details=None):
        """
        Show completion message with banner and preserve status log
        """
        if not self.is_initialized:
            self.initialize_persistent_display()
        
        # Set final progress state
        self.current_progress = f"{self.GREEN}✓ COMPLETED - Processed {total_processed} items{self.RESET}"
        
        # Add completion status to log
        self.add_status("=" * 50, "info")
        self.add_status(f"PROCESSING COMPLETED!", "success")
        self.add_status(f"Processed {total_processed} items total", "success")
        
        if details:
            for detail in details:
                if "⚠️" in detail or "warning" in detail.lower():
                    self.add_status(detail, "warning")
                elif "✓" in detail or "success" in detail.lower():
                    self.add_status(detail, "success")
                else:
                    self.add_status(detail, "info")
        
        self.add_status("=" * 50, "info")
        
        # Refresh display with final progress
        self._refresh_display()
    
    def show_error(self, error_message):
        """Show error message in the persistent display"""
        if not self.is_initialized:
            self.initialize_persistent_display()
        
        self.add_status(f"ERROR: {error_message}", "error")
    
    def show_warning(self, warning_message):
        """Show warning message in the persistent display"""
        if not self.is_initialized:
            self.initialize_persistent_display()
        
        self.add_status(f"WARNING: {warning_message}", "warning")
    
    def show_success(self, success_message):
        """Show success message in the persistent display"""
        if not self.is_initialized:
            self.initialize_persistent_display()
        
        self.add_status(success_message, "success")
    
    def clear_status_log(self):
        """Clear the status log"""
        self.status_log.clear()
        if self.is_initialized:
            self._refresh_display()
    
    def set_max_status_lines(self, max_lines):
        """Change the maximum number of status lines to display"""
        self.max_status_lines = max_lines
        # Create new deque with new size, preserving existing messages
        old_log = list(self.status_log)
        self.status_log = deque(old_log[-max_lines:], maxlen=max_lines)