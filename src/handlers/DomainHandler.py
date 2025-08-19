import os
from urllib.parse import urlparse   


class DomainHandler:
    def __init__(self):
        pass

    def extract_domain(self, url):
        """Extract just the domain name from a URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
                
            return domain
        except:
            return None

    def get_unique_domains(self, urls):
        """Get unique domain names from a list of URLs"""
        domains = set()
        for url in urls:
            domain = self.extract_domain(url)
            if domain:
                domains.add(domain)
        return sorted(list(domains))