import json
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from collections import defaultdict
import os
from src import config
from src.handlers.DomainHandler import DomainHandler
import time
from src.packages.MermaidCLI import MermaidCLI
from src.utils.Banner import Banner

domain_handler = DomainHandler()
mermaid_cli = MermaidCLI()
jsauce_banner = Banner()

class JSONToMermaidConverter:
    def __init__(self, max_edges=450, max_text_size=50000):
        self.used_ids = set()
        self.max_edges = max_edges
        self.max_text_size = max_text_size
        self.edge_count = 0
        self.text_size = 0
        
        # Priority categories (most important for security)
        self.high_priority_categories = {
            'admin_endpoints', 'authentication_endpoints', 'api_keys_tokens', 
            'security_endpoints', 'payment_endpoints', 'api_endpoints',
            'user_management', 'webhooks_callbacks', 'external_apis'
        }
        
        self.medium_priority_categories = {
            'ajax_endpoints', 'http_api_calls', 'graphql_endpoints',
            'websockets', 'file_operations', 'analytics_tracking'
        }
        
        # Low priority categories get filtered out when space is limited
        self.low_priority_categories = {
            'resources_assets', 'framework_specific', 'media_endpoints',
            'social_features', 'content_management'
        }
   
    def sanitize_text(self, text: str) -> str:
        """Sanitize text for Mermaid compatibility"""
        text = re.sub(r'[^\w\s-]', '_', text)
        text = re.sub(r'\s+', '_', text)
        return text
    
    def clean_json_files(self, urls):
        """Clean up malformed JSON files"""
        jsauce_banner.update_status("CLEANING UP JSON FILES...")
        for url in urls:
            domain = domain_handler.extract_domain(url)
            if not domain:
                continue
            
            files = [f"{config.OUTPUT_DIR}/{domain}/{domain}_{suffix}.json" 
                    for suffix in ['endpoints_detailed', 'endpoints_for_db', 'endpoint_stats']]
            
            for json_file in files:
                if os.path.exists(json_file) and os.path.getsize(json_file) > 0:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        
                        if content:
                            if not content.startswith('['):
                                content = '[' + content.replace('}{', '},{') + ']'
                            
                            with open(json_file, 'w', encoding='utf-8') as f:
                                json.dump(json.loads(content), f, indent=2)
                                
                    except Exception as e:
                        jsauce_banner.update_status(f"Error cleaning {json_file}: {e}")
                        time.sleep(1)
  
    def generate_unique_id(self, base_name: str) -> str:
        """Generate unique IDs to avoid conflicts"""
        clean_name = re.sub(r'[^\w]', '_', base_name)
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        
        if clean_name not in self.used_ids:
            self.used_ids.add(clean_name)
            return clean_name
        
        counter = 1
        while f"{clean_name}_{counter}" in self.used_ids:
            counter += 1
        
        unique_id = f"{clean_name}_{counter}"
        self.used_ids.add(unique_id)
        return unique_id
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain or "unknown_domain"
        except:
            return "unknown_domain"
   
    def reorganize_data_by_hierarchy(self, data: Dict) -> Dict:
        """Reorganize data to Domain->Category->Endpoint - no evidence/JS links"""
        if not isinstance(data, dict) or 'endpoints_by_source' not in data:
            return {}
            
        reorganized = {}
        endpoints_by_source = data.get('endpoints_by_source', {})
        
        for source_url, source_data in endpoints_by_source.items():
            domain = self.extract_domain(source_url)
            
            if domain not in reorganized:
                reorganized[domain] = {
                    'source_url': source_url,
                    'categories': defaultdict(set)
                }
            
            js_files = source_data.get('js_files', {})
            
            # Reorganize: collect all endpoints by category - no JS links
            for js_url, js_data in js_files.items():
                categories = js_data.get('categories', {})
                
                for category, endpoints in categories.items():
                    if not endpoints:
                        continue
                        
                    for endpoint in endpoints:
                        # Just store the endpoint in the category set (deduplication)
                        reorganized[domain]['categories'][category].add(endpoint)
        
        # Convert sets to lists for easier iteration
        for domain, domain_data in reorganized.items():
            for category in domain_data['categories']:
                domain_data['categories'][category] = list(domain_data['categories'][category])
        
        return reorganized
   
    def add_edge(self, mermaid_lines, connection):
        """Add edge while tracking count and text size"""
        if self.edge_count >= self.max_edges:
            return False
        
        # Estimate text size
        estimated_size = len(connection) + 1  # +1 for newline
        if self.text_size + estimated_size > self.max_text_size:
            return False
            
        mermaid_lines.append(connection)
        self.edge_count += 1
        self.text_size += estimated_size
        return True
    
    def add_node(self, mermaid_lines, node_definition):
        """Add node while tracking text size"""
        estimated_size = len(node_definition) + 1  # +1 for newline
        if self.text_size + estimated_size > self.max_text_size:
            return False
            
        mermaid_lines.append(node_definition)
        self.text_size += estimated_size
        return True
    
    def get_category_priority(self, category):
        """Get priority level for a category"""
        if category in self.high_priority_categories:
            return 1
        elif category in self.medium_priority_categories:
            return 2
        else:
            return 3
    
    def prioritize_endpoints(self, endpoints, max_endpoints=10):
        """Prioritize endpoints by security relevance"""
        # Security-relevant endpoint patterns (high priority)
        high_priority_patterns = [
            r'/admin', r'/api/', r'/auth', r'/login', r'/oauth', r'/token',
            r'/payment', r'/billing', r'/stripe', r'/paypal', r'/webhook',
            r'/2fa', r'/mfa', r'/password', r'/reset', r'/verify'
        ]
        
        # Medium priority patterns
        medium_priority_patterns = [
            r'/ajax', r'/graphql', r'/rest', r'/rpc', r'/upload', r'/download',
            r'/user', r'/profile', r'/settings', r'/config'
        ]
        
        def get_endpoint_priority(endpoint):
            """Get priority score for an endpoint"""
            endpoint_lower = endpoint.lower()
            
            # Check high priority patterns
            for pattern in high_priority_patterns:
                if re.search(pattern, endpoint_lower):
                    return 1
            
            # Check medium priority patterns  
            for pattern in medium_priority_patterns:
                if re.search(pattern, endpoint_lower):
                    return 2
            
            return 3
        
        # Sort by priority, then limit
        prioritized = sorted(endpoints, key=get_endpoint_priority)
        return prioritized[:max_endpoints]

    def create_flowchart_with_proper_hierarchy(self, data: Any) -> str:
        """Create prioritized left-to-right flowchart with Domain -> Category -> Endpoint hierarchy"""
        self.used_ids = set()
        self.edge_count = 0
        self.text_size = 0
        
        # Start the flowchart with left-to-right layout
        mermaid_lines = []
        if not self.add_node(mermaid_lines, 'flowchart LR'):
            return "Error: Diagram too large"
        if not self.add_node(mermaid_lines, '    START([Website Map])'):
            return "Error: Diagram too large"
        self.add_node(mermaid_lines, '')
        
        # Add CSS classes for styling
        style_lines = [
            '    %% Styling',
            '    classDef domainStyle fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000',
            '    classDef categoryStyle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000',
            '    classDef endpointStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000',
            '    classDef highPriority fill:#ffebee,stroke:#d32f2f,stroke-width:3px,color:#000',
            ''
        ]
        
        for line in style_lines:
            if not self.add_node(mermaid_lines, line):
                break
        
        reorganized_data = self.reorganize_data_by_hierarchy(data)
        
        domain_nodes = []
        category_nodes = []
        endpoint_nodes = []
        high_priority_nodes = []
        
        for domain, domain_data in reorganized_data.items():
            # Create domain node
            domain_id = self.generate_unique_id(f"domain_{domain}")
            if not self.add_node(mermaid_lines, f'    {domain_id}["{domain}"]'):
                break
            if not self.add_edge(mermaid_lines, f'    START --> {domain_id}'):
                break
            domain_nodes.append(domain_id)
            
            categories = domain_data['categories']
            
            # Sort categories by priority
            sorted_categories = sorted(categories.items(), 
                                     key=lambda x: (self.get_category_priority(x[0]), -len(x[1])))
            
            # Limit categories based on space
            max_categories = 15 if self.text_size < self.max_text_size * 0.3 else 8
            
            for category, endpoints in sorted_categories[:max_categories]:
                if not endpoints:
                    continue
                    
                # Skip low priority categories if we're running out of space
                if (self.text_size > self.max_text_size * 0.6 and 
                    self.get_category_priority(category) == 3):
                    continue
                
                # Create category node
                cat_id = self.generate_unique_id(f"cat_{category}_{domain}")
                cat_display = category.replace('_', ' ').title()
                if not self.add_node(mermaid_lines, f'    {cat_id}["{cat_display}"]'):
                    break
                if not self.add_edge(mermaid_lines, f'    {domain_id} --> {cat_id}'):
                    break
                category_nodes.append(cat_id)
                
                # Prioritize and limit endpoints
                max_endpoints_per_category = 8 if self.get_category_priority(category) == 1 else 5
                if self.text_size > self.max_text_size * 0.5:
                    max_endpoints_per_category = 3
                
                prioritized_endpoints = self.prioritize_endpoints(endpoints, max_endpoints_per_category)
                
                for endpoint in prioritized_endpoints:
                    if not endpoint:
                        continue
                        
                    # Create endpoint node
                    endpoint_id = self.generate_unique_id(f"ep_{category}_{domain}")
                    
                    # Truncate very long endpoints for text size
                    endpoint_clean = str(endpoint).replace('[', '').replace(']', '').replace('"', "'")
                    if len(endpoint_clean) > 50:
                        endpoint_clean = endpoint_clean[:47] + "..."
                    
                    if not self.add_node(mermaid_lines, f'    {endpoint_id}["{endpoint_clean}"]'):
                        break
                    if not self.add_edge(mermaid_lines, f'    {cat_id} --> {endpoint_id}'):
                        break
                    
                    # Mark high priority endpoints
                    if self.get_category_priority(category) == 1:
                        high_priority_nodes.append(endpoint_id)
                    else:
                        endpoint_nodes.append(endpoint_id)
                    
                    if self.edge_count >= self.max_edges or self.text_size >= self.max_text_size:
                        break
                
                # Add "more" indicator if we truncated
                if len(endpoints) > len(prioritized_endpoints):
                    more_id = self.generate_unique_id(f"more_{category}_{domain}")
                    remaining = len(endpoints) - len(prioritized_endpoints)
                    if self.add_node(mermaid_lines, f'    {more_id}["...+{remaining} more"]'):
                        self.add_edge(mermaid_lines, f'    {cat_id} --> {more_id}')
                        category_nodes.append(more_id)
                
                if self.edge_count >= self.max_edges or self.text_size >= self.max_text_size:
                    break
            
            # Add "more categories" indicator if we truncated
            if len(categories) > max_categories:
                more_cat_id = self.generate_unique_id(f"more_cats_{domain}")
                remaining_cats = len(categories) - max_categories
                if self.add_node(mermaid_lines, f'    {more_cat_id}["...+{remaining_cats} more categories"]'):
                    self.add_edge(mermaid_lines, f'    {domain_id} --> {more_cat_id}')
                    category_nodes.append(more_cat_id)
            
            if self.edge_count >= self.max_edges or self.text_size >= self.max_text_size:
                break
        
        # Add warning if we hit limits
        if self.edge_count >= self.max_edges or self.text_size >= self.max_text_size:
            warning_msg = f"Showing prioritized results only"
            if self.edge_count >= self.max_edges:
                warning_msg += f"<br/>Edge limit: {self.max_edges}"
            if self.text_size >= self.max_text_size:
                warning_msg += f"<br/>Text size limit reached"
            
            if self.add_node(mermaid_lines, f'    WARNING["{warning_msg}"]'):
                self.add_edge(mermaid_lines, '    START --> WARNING')
        
        # Apply CSS classes
        self.add_node(mermaid_lines, '')
        self.add_node(mermaid_lines, '    %% Apply styles')
        if domain_nodes:
            self.add_node(mermaid_lines, f'    class {",".join(domain_nodes)} domainStyle')
        if category_nodes:
            self.add_node(mermaid_lines, f'    class {",".join(category_nodes)} categoryStyle')
        if endpoint_nodes:
            self.add_node(mermaid_lines, f'    class {",".join(endpoint_nodes)} endpointStyle')
        if high_priority_nodes:
            self.add_node(mermaid_lines, f'    class {",".join(high_priority_nodes)} highPriority')
        
        return '\n'.join(mermaid_lines)
   
    def create_flowchart(self, data: Any) -> str:
        """Create a flowchart showing the structure with proper hierarchy"""
        self.used_ids = set()  # Reset IDs for each conversion
        
        # Handle your tool's detailed JSON format (endpoints_detailed.json)
        if isinstance(data, dict) and 'endpoints_by_source' in data:
            return self.create_flowchart_with_proper_hierarchy(data)
        
        # Handle your tool's stats format (endpoint_stats.json) - keep existing logic
        elif isinstance(data, dict) and 'categories' in data:
            return self.create_simple_stats_flowchart(data)
        
        # Handle list format
        elif isinstance(data, list) and len(data) > 0:
            first_item = data[0]
            if 'endpoints_by_source' in first_item:
                return self.create_flowchart_with_proper_hierarchy(first_item)
            else:
                return self.create_simple_list_flowchart(data)
        
        return "flowchart LR\n    START([No valid data found])\n"
    
    def create_simple_stats_flowchart(self, data: Dict) -> str:
        """Create simple left-to-right flowchart for stats format"""
        mermaid = 'flowchart LR\n'
        mermaid += '    START([Website Map])\n'
        
        categories = data.get('categories', {})
        overall = data.get('overall', {})
        
        total_endpoints = overall.get('total_endpoints', 0)
        total_js = overall.get('total_js_files', 0)
        
        overview_id = self.generate_unique_id('overview')
        mermaid += f'    {overview_id}["Total: {total_endpoints} endpoints<br/>{total_js} JS files"]\n'
        mermaid += f'    START --> {overview_id}\n'
        
        for category, count in categories.items():
            cat_id = self.generate_unique_id(f"cat_{category}")
            cat_display = category.replace('_', ' ').title()
            mermaid += f'    {cat_id}["{cat_display}<br/>{count} endpoints"]\n'
            mermaid += f'    {overview_id} --> {cat_id}\n'
        
        return mermaid
    
    def create_simple_list_flowchart(self, data: List) -> str:
        """Create simple left-to-right flowchart for list format"""
        mermaid = 'flowchart LR\n'
        mermaid += '    START([Website Map])\n'
        
        for i, item in enumerate(data):
            overall = item.get('overall', {})
            total_endpoints = overall.get('total_endpoints', 0)
            total_js = overall.get('total_js_files', 0)
           
            analysis_id = self.generate_unique_id(f"Analysis_{i}")
            mermaid += f'    {analysis_id}["Analysis {i+1}<br/>{total_endpoints} endpoints<br/>{total_js} JS files"]\n'
            mermaid += f'    START --> {analysis_id}\n'
           
            # Add categories
            categories = item.get('categories', {})
            for cat, count in categories.items():
                cat_clean = cat.replace('_', ' ').title()
                cat_id = self.generate_unique_id(f"{cat}_{i}")
                mermaid += f'    {cat_id}["{cat_clean}<br/>{count}"]\n'
                mermaid += f'    {analysis_id} --> {cat_id}\n'
        
        return mermaid
   
    def convert_to_flowchart(self, json_data: Any) -> str:
        """Main conversion method"""
        # Parse JSON if it's a string
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                return f"Error parsing JSON: {e}"
        else:
            data = json_data
       
        return self.create_flowchart(data)
    
    def generate_mermaid(self, urls):
        """Generate Mermaid flowcharts"""
        jsauce_banner.update_status("CONVERTING TO MERMAID FORMAT...")
        for url in urls:
            domain = domain_handler.extract_domain(url)
            if not domain:
                continue
            
            json_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_endpoints_detailed.json"
            if not (os.path.exists(json_file) and os.path.getsize(json_file) > 0):
                continue
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                mermaid_output = self.convert_to_flowchart(json_data)
                mermaid_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_flowchart.mmd"
                
                with open(mermaid_file, 'w', encoding='utf-8') as f:
                    f.write(mermaid_output)
                
                jsauce_banner.update_status(f"Mermaid saved: {mermaid_file}")
                
                time.sleep(1)
                
                # Render to SVG/PNG
                for ext in ['svg', 'png']:
                    output_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_flowchart.{ext}"
                    mermaid_cli.render(mermaid_file, output_file)
                    jsauce_banner.update_status(f"Rendered: {output_file}")
                    
            except Exception as e:
                jsauce_banner.update_status(f"Mermaid error for {domain}: {e}")
                time.sleep(1)