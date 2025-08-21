import json
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from collections import defaultdict
import os
from src import config
import time
import shutil
from src.utils.Logger import get_logger

class JSONToMermaidConverter:
    def __init__(self, domain_handler, banner, mermaid_cli, template, max_edges=450, max_text_size=50000):
        self.used_ids = set()
        self.max_edges = max_edges
        self.max_text_size = max_text_size
        self.edge_count = 0
        self.text_size = 0
        self.domain_handler = domain_handler
        self.banner = banner
        self.mermaid_cli = mermaid_cli
        self.template = template
        self.logger = get_logger()
        
        self.logger.debug(f"Initializing JSONToMermaidConverter with template: {template}")
        self.logger.debug(f"Limits: max_edges={max_edges}, max_text_size={max_text_size}")
        
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
        
        self.logger.verbose(f"Priority categories defined: {len(self.high_priority_categories)} high, {len(self.medium_priority_categories)} medium, {len(self.low_priority_categories)} low")
   
    def sanitize_text(self, text: str) -> str:
        """Sanitize text for Mermaid compatibility"""
        original_text = text
        text = re.sub(r'[^\w\s-]', '_', text)
        text = re.sub(r'\s+', '_', text)
        
        if original_text != text:
            self.logger.debug(f"Sanitized text: '{original_text}' -> '{text}'")
        
        return text
    
    # clean json files after append
    def clean_json_files(self, urls):
        """Clean up malformed JSON files - improved version"""
        self.logger.info("Starting JSON file cleanup process")
        self.banner.add_status("CLEANING UP JSON FILES...")
        
        processed_files = 0
        fixed_files = 0
        skipped_files = 0
        error_files = 0
        
        for url in urls:
            domain = self.domain_handler.extract_domain(url)
            if not domain:
                self.logger.debug(f"Skipping URL with no domain: {url}")
                continue
            
            self.logger.debug(f"Processing JSON cleanup for domain: {domain}")
            
            # Define the files that need cleaning
            json_suffixes = [f'{self.template}_detailed', f'{self.template}_content_for_db', f'{self.template}_content_stats']
            
            for suffix in json_suffixes:
                json_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{suffix}.json"
                processed_files += 1
                
                if not os.path.exists(json_file):
                    self.logger.debug(f"Skipping non-existent file: {json_file}")
                    self.banner.add_status(f"Skipping {json_file} - file doesn't exist")
                    skipped_files += 1
                    continue
                    
                file_size = os.path.getsize(json_file)
                if file_size == 0:
                    self.logger.debug(f"Skipping empty file: {json_file}")
                    self.banner.add_status(f"Skipping {json_file} - file is empty")
                    skipped_files += 1
                    continue
                
                self.logger.verbose(f"Processing JSON file: {json_file} ({file_size} bytes)")
                
                try:
                    # Create backup before processing
                    backup_file = f"{json_file}.backup"
                    shutil.copy2(json_file, backup_file)
                    self.logger.debug(f"Created backup: {backup_file}")
                    
                    with open(json_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    if not content:
                        self.logger.debug(f"File has no content after strip: {json_file}")
                        self.banner.add_status(f"Skipping {json_file} - no content after strip")
                        if backup_file and os.path.exists(backup_file):
                            os.remove(backup_file)
                        skipped_files += 1
                        continue
                        
                    # Check if it's already valid JSON
                    try:
                        parsed_data = json.loads(content)
                        self.logger.debug(f"File already contains valid JSON: {json_file}")
                        self.banner.add_status(f"{json_file} already valid JSON")

                        # Rewrite with proper formatting
                        with open(json_file, 'w', encoding='utf-8') as f:
                            json.dump(parsed_data, f, indent=2, ensure_ascii=False)
                        
                        if backup_file and os.path.exists(backup_file):
                            os.remove(backup_file)
                        
                        self.logger.debug(f"Reformatted valid JSON file: {json_file}")
                        continue

                    except json.JSONDecodeError as e:
                        self.logger.warning(f"JSON decode error in {json_file}: {e}")
                        self.logger.debug(f"Attempting to fix malformed JSON")
                    
                    # Fix the JSON structure
                    fixed_content = self._fix_malformed_json(content, json_file)
                    
                    if fixed_content:
                        # Validate the fixed content before writing
                        try:
                            parsed_data = json.loads(fixed_content)
                            
                            # Write the fixed content
                            with open(json_file, 'w', encoding='utf-8') as f:
                                json.dump(parsed_data, f, indent=2, ensure_ascii=False)
                            
                            fixed_files += 1
                            self.logger.success(f"Successfully fixed malformed JSON: {json_file}")
                            self.banner.add_status(f"Fixed {json_file}")        
                            
                            if backup_file and os.path.exists(backup_file):
                                os.remove(backup_file)
                            
                        except json.JSONDecodeError as e:
                            error_files += 1
                            self.logger.error(f"Failed to validate fixed JSON for {json_file}: {e}")
                            self.banner.show_error(f"Failed to validate fixed JSON for {json_file}: {e}")
                            # Restore from backup
                            shutil.move(backup_file, json_file)
                            
                    else:
                        error_files += 1
                        self.logger.error(f"Could not fix malformed JSON: {json_file}")
                        self.banner.show_error(f"Could not fix malformed JSON: {json_file}")
                        # Keep backup, mark original as problematic
                        os.rename(json_file, f"{json_file}.corrupted")
                        shutil.move(backup_file, json_file)
                        
                except Exception as e:
                    error_files += 1
                    self.logger.error(f"Error processing {json_file}: {e}")
                    self.banner.show_error(f"Error processing {json_file}: {e}")
                    # Restore backup if it exists
                    backup_file = f"{json_file}.backup"
                    if os.path.exists(backup_file):
                        try:
                            shutil.move(backup_file, json_file)
                            self.logger.debug(f"Restored backup for {json_file}")
                        except Exception as restore_error:
                            self.logger.error(f"Failed to restore backup: {restore_error}")
        
        # Log cleanup summary
        self.logger.info(f"JSON cleanup completed:")
        self.logger.info(f"  - Processed: {processed_files} files")
        self.logger.info(f"  - Fixed: {fixed_files} files")
        self.logger.info(f"  - Skipped: {skipped_files} files")
        self.logger.info(f"  - Errors: {error_files} files")

    def _fix_malformed_json(self, content, filename):
        """Fix malformed JSON content from append operations"""
        self.logger.debug(f"Attempting to fix malformed JSON in {filename}")
        
        try:
            # Remove any trailing commas or incomplete structures
            content = content.rstrip().rstrip(',')
            self.logger.debug(f"Content length after cleanup: {len(content)} characters")
            
            # Handle case where content starts with valid JSON array
            if content.startswith('[') and content.endswith(']'):
                self.logger.debug("Content appears to be a valid JSON array")
                return content
            
            # Handle multiple JSON objects appended together
            if content.startswith('{'):
                self.logger.debug("Content starts with JSON object, attempting concatenation fix")
                # This is the main case - multiple JSON objects like: {}{}{}
                
                # Method 1: Try simple replacement
                if '}{' in content:
                    self.logger.debug("Found concatenated objects pattern '}{', trying simple fix")
                    fixed = '[' + content.replace('}{', '},{') + ']'
                    # Quick validation
                    try:
                        json.loads(fixed)
                        self.logger.debug("Simple concatenation fix successful")
                        return fixed
                    except Exception as e:
                        self.logger.debug(f"Simple fix failed: {e}")
                
                # Method 2: More robust parsing for complex cases
                self.logger.debug("Trying robust JSON object parsing")
                fixed = self._parse_concatenated_json_objects(content)
                if fixed:
                    self.logger.debug("Robust parsing successful")
                    return fixed
            
            # Handle case where content is a single object
            if content.startswith('{') and content.endswith('}'):
                self.logger.debug("Content is a single JSON object, wrapping in array")
                return '[' + content + ']'
            
            # If all else fails, try to salvage what we can
            self.logger.warning(f"Complex JSON structure in {filename}, attempting recovery...")
            self.banner.show_warning(f"Complex JSON structure in {filename}, attempting recovery...")
            return self._attempt_json_recovery(content)
            
        except Exception as e:
            self.logger.error(f"Error in _fix_malformed_json: {e}")
            self.banner.show_error(f"Error in _fix_malformed_json: {e}")
            return None

    def _parse_concatenated_json_objects(self, content):
        """Parse concatenated JSON objects more robustly"""
        self.logger.debug("Starting robust JSON object parsing")
        
        try:
            objects = []
            decoder = json.JSONDecoder()
            idx = 0
            
            while idx < len(content):
                content_remaining = content[idx:].lstrip()
                if not content_remaining:
                    break
                    
                try:
                    obj, end_idx = decoder.raw_decode(content_remaining)
                    objects.append(obj)
                    idx += len(content[idx:]) - len(content_remaining) + end_idx
                    self.logger.debug(f"Successfully parsed object {len(objects)}")
                except json.JSONDecodeError as e:
                    self.logger.debug(f"JSON decode error at position {idx}: {e}")
                    break
            
            if objects:
                result = json.dumps(objects)
                self.logger.debug(f"Successfully parsed {len(objects)} JSON objects")
                return result
            else:
                self.logger.warning("No valid JSON objects found during parsing")
            
        except Exception as e:
            self.logger.error(f"Error parsing concatenated objects: {e}")
            self.banner.show_error(f"Error parsing concatenated objects: {e}")
        
        return None

    def _attempt_json_recovery(self, content):
        """Last resort JSON recovery"""
        self.logger.debug("Attempting last resort JSON recovery")
        
        try:
            # Try to find complete JSON objects using regex
            import re
            
            # Find JSON object patterns
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, content)
            
            self.logger.debug(f"Found {len(matches)} potential JSON objects via regex")
            
            valid_objects = []
            for i, match in enumerate(matches):
                try:
                    obj = json.loads(match)
                    valid_objects.append(obj)
                    self.logger.debug(f"Regex match {i+1} is valid JSON")
                except Exception as e:
                    self.logger.debug(f"Regex match {i+1} is invalid: {e}")
                    continue
            
            if valid_objects:
                result = json.dumps(valid_objects)
                self.logger.warning(f"JSON recovery successful: salvaged {len(valid_objects)} objects")
                return result
            else:
                self.logger.error("JSON recovery failed: no valid objects found")
                
        except Exception as e:
            self.logger.error(f"JSON recovery failed: {e}")
            self.banner.show_error(f"JSON recovery failed: {e}")
        
        return None

    def generate_unique_id(self, base_name: str) -> str:
        """Generate unique IDs to avoid conflicts"""
        clean_name = re.sub(r'[^\w]', '_', base_name)
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        
        if clean_name not in self.used_ids:
            self.used_ids.add(clean_name)
            self.logger.debug(f"Generated unique ID: {clean_name}")
            return clean_name
        
        counter = 1
        while f"{clean_name}_{counter}" in self.used_ids:
            counter += 1
        
        unique_id = f"{clean_name}_{counter}"
        self.used_ids.add(unique_id)
        self.logger.debug(f"Generated unique ID with counter: {unique_id}")
        return unique_id
    
    # def extract_domain(self, url: str) -> str:
    #     """Extract domain from URL"""
    #     try:
    #         parsed = urlparse(url)
    #         domain = parsed.netloc
    #         if domain.startswith('www.'):
    #             domain = domain[4:]
    #         result = domain or "unknown_domain"
    #         self.logger.debug(f"Extracted domain from {url}: {result}")
    #         return result
    #     except Exception as e:
    #         self.logger.warning(f"Failed to extract domain from {url}: {e}")
    #         return "unknown_domain"
   
    def reorganize_data_by_hierarchy(self, data: Dict) -> Dict:
        """Reorganize data to Domain->Category->Category - no evidence/JS links"""
        self.logger.debug("Starting data reorganization by hierarchy")
        
        if not isinstance(data, dict) or 'contents_by_source' not in data:
            self.logger.warning("Invalid data structure for reorganization")
            return {}
            
        reorganized = {}
        contents_by_source = data.get('contents_by_source', {})
        
        self.logger.debug(f"Processing {len(contents_by_source)} sources")
        
        for source_url, source_data in contents_by_source.items():
            domain = self.domain_handler.extract_domain(source_url)
            
            if domain not in reorganized:
                reorganized[domain] = {
                    'source_url': source_url,
                    'categories': defaultdict(set)
                }
                self.logger.debug(f"Created new domain entry: {domain}")
            
            js_files = source_data.get('js_files', {})
            self.logger.debug(f"Processing {len(js_files)} JS files for {domain}")
            
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
        total_endpoints = 0
        for domain, domain_data in reorganized.items():
            domain_endpoints = 0
            for category in domain_data['categories']:
                category_count = len(domain_data['categories'][category])
                domain_data['categories'][category] = list(domain_data['categories'][category])
                domain_endpoints += category_count
                total_endpoints += category_count
            
            self.logger.verbose(f"Domain {domain}: {len(domain_data['categories'])} categories, {domain_endpoints} endpoints")
        
        self.logger.info(f"Data reorganization complete: {len(reorganized)} domains, {total_endpoints} total endpoints")
        return reorganized
   
    def add_edge(self, mermaid_lines, connection):
        """Add edge while tracking count and text size"""
        if self.edge_count >= self.max_edges:
            self.logger.warning(f"Reached maximum edge limit: {self.max_edges}")
            return False
        
        # Estimate text size
        estimated_size = len(connection) + 1  # +1 for newline
        if self.text_size + estimated_size > self.max_text_size:
            self.logger.warning(f"Reached maximum text size limit: {self.max_text_size}")
            return False
            
        mermaid_lines.append(connection)
        self.edge_count += 1
        self.text_size += estimated_size
        self.logger.debug(f"Added edge ({self.edge_count}/{self.max_edges}): {connection[:50]}...")
        return True
    
    def add_node(self, mermaid_lines, node_definition):
        """Add node while tracking text size"""
        estimated_size = len(node_definition) + 1  # +1 for newline
        if self.text_size + estimated_size > self.max_text_size:
            self.logger.warning(f"Reached maximum text size limit when adding node")
            return False
            
        mermaid_lines.append(node_definition)
        self.text_size += estimated_size
        self.logger.debug(f"Added node (text size: {self.text_size}/{self.max_text_size}): {node_definition[:50]}...")
        return True
    
    def get_category_priority(self, category):
        """Get priority level for a category"""
        if category in self.high_priority_categories:
            priority = 1
        elif category in self.medium_priority_categories:
            priority = 2
        else:
            priority = 3
        
        self.logger.debug(f"Category '{category}' has priority level {priority}")
        return priority
    
    def prioritize_endpoints(self, endpoints, max_endpoints=10):
        """Prioritize endpoints by security relevance"""
        self.logger.debug(f"Prioritizing {len(endpoints)} endpoints (max: {max_endpoints})")
        
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
        
        def get_content_priority(endpoint):
            """Get priority score for an endpoint"""
            content_lower = endpoint.lower()
            
            # Check high priority patterns
            for pattern in high_priority_patterns:
                if re.search(pattern, content_lower):
                    return 1
            
            # Check medium priority patterns  
            for pattern in medium_priority_patterns:
                if re.search(pattern, content_lower):
                    return 2
            
            return 3
        
        # Sort by priority, then limit
        prioritized = sorted(endpoints, key=get_content_priority)
        result = prioritized[:max_endpoints]
        
        if len(result) < len(endpoints):
            self.logger.debug(f"Prioritized {len(result)} endpoints from {len(endpoints)} total")
        
        return result

    def create_flowchart_with_proper_hierarchy(self, data: Any) -> str:
        """Create prioritized left-to-right flowchart with Domain -> Category -> Category hierarchy"""
        self.logger.info("Creating flowchart with proper hierarchy")
        
        self.used_ids = set()
        self.edge_count = 0
        self.text_size = 0
        
        # Start the flowchart with left-to-right layout
        mermaid_lines = []
        if not self.add_node(mermaid_lines, 'flowchart LR'):
            self.logger.error("Failed to add flowchart declaration")
            return "Error: Diagram too large"
        if not self.add_node(mermaid_lines, '    START([Website Map])'):
            self.logger.error("Failed to add START node")
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
        
        if not reorganized_data:
            self.logger.warning("No data available for flowchart generation")
            return "flowchart LR\n    START([No data available])\n"
        
        domain_nodes = []
        category_nodes = []
        content_nodes = []
        high_priority_nodes = []
        
        for domain, domain_data in reorganized_data.items():
            self.logger.debug(f"Processing domain: {domain}")
            
            # Create domain node
            domain_id = self.generate_unique_id(f"domain_{domain}")
            if not self.add_node(mermaid_lines, f'    {domain_id}["{domain}"]'):
                break
            if not self.add_edge(mermaid_lines, f'    START --> {domain_id}'):
                break
            domain_nodes.append(domain_id)
            
            categories = domain_data['categories']
            self.logger.debug(f"Domain {domain} has {len(categories)} categories")
            
            # Sort categories by priority
            sorted_categories = sorted(categories.items(), 
                                     key=lambda x: (self.get_category_priority(x[0]), -len(x[1])))
            
            # Limit categories based on space
            max_categories = 15 if self.text_size < self.max_text_size * 0.3 else 8
            self.logger.debug(f"Using max_categories: {max_categories} for domain {domain}")
            
            for category, endpoints in sorted_categories[:max_categories]:
                if not endpoints:
                    continue
                    
                # Skip low priority categories if we're running out of space
                if (self.text_size > self.max_text_size * 0.6 and 
                    self.get_category_priority(category) == 3):
                    self.logger.debug(f"Skipping low priority category '{category}' due to space constraints")
                    continue
                
                self.logger.debug(f"Processing category '{category}' with {len(endpoints)} endpoints")
                
                # Create category node
                cat_id = self.generate_unique_id(f"cat_{category}_{domain}")
                cat_display = category.replace('_', ' ').title()
                if not self.add_node(mermaid_lines, f'    {cat_id}["{cat_display}"]'):
                    break
                if not self.add_edge(mermaid_lines, f'    {domain_id} --> {cat_id}'):
                    break
                category_nodes.append(cat_id)
                
                # Prioritize and limit endpoints
                max_content_per_category = 8 if self.get_category_priority(category) == 1 else 5
                if self.text_size > self.max_text_size * 0.5:
                    max_content_per_category = 3
                
                prioritized_endpoints = self.prioritize_endpoints(endpoints, max_content_per_category)
                
                for endpoint in prioritized_endpoints:
                    if not endpoint:
                        continue
                        
                    # Create endpoint node
                    content_id = self.generate_unique_id(f"ep_{category}_{domain}")
                    
                    # Truncate very long endpoints for text size
                    content_clean = str(endpoint).replace('[', '').replace(']', '').replace('"', "'")
                    if len(content_clean) > 50:
                        content_clean = content_clean[:47] + "..."
                    
                    if not self.add_node(mermaid_lines, f'    {content_id}["{content_clean}"]'):
                        break
                    if not self.add_edge(mermaid_lines, f'    {cat_id} --> {content_id}'):
                        break
                    
                    # Mark high priority endpoints
                    if self.get_category_priority(category) == 1:
                        high_priority_nodes.append(content_id)
                    else:
                        content_nodes.append(content_id)
                    
                    if self.edge_count >= self.max_edges or self.text_size >= self.max_text_size:
                        self.logger.warning("Reached diagram limits while adding endpoints")
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
                self.logger.warning("Reached diagram limits while processing domains")
                break
        
        # Add warning if we hit limits
        if self.edge_count >= self.max_edges or self.text_size >= self.max_text_size:
            self.logger.warning("Diagram limits reached, showing prioritized results only")
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
        if content_nodes:
            self.add_node(mermaid_lines, f'    class {",".join(content_nodes)} endpointStyle')
        if high_priority_nodes:
            self.add_node(mermaid_lines, f'    class {",".join(high_priority_nodes)} highPriority')
        
        final_flowchart = '\n'.join(mermaid_lines)
        
        self.logger.info(f"Flowchart generation complete:")
        self.logger.info(f"  - Total lines: {len(mermaid_lines)}")
        self.logger.info(f"  - Edges used: {self.edge_count}/{self.max_edges}")
        self.logger.info(f"  - Text size: {self.text_size}/{self.max_text_size}")
        self.logger.info(f"  - Domain nodes: {len(domain_nodes)}")
        self.logger.info(f"  - Category nodes: {len(category_nodes)}")
        self.logger.info(f"  - Content nodes: {len(content_nodes)}")
        self.logger.info(f"  - High priority nodes: {len(high_priority_nodes)}")
        
        return final_flowchart
   
    def create_flowchart(self, data: Any) -> str:
        """Create a flowchart showing the structure with proper hierarchy"""
        self.logger.debug("Starting flowchart creation")
        self.used_ids = set()  # Reset IDs for each conversion
        
        # Handle your tool's detailed JSON format (contents_detailed.json)
        if isinstance(data, dict) and 'contents_by_source' in data:
            self.logger.debug("Detected detailed JSON format with 'contents_by_source'")
            return self.create_flowchart_with_proper_hierarchy(data)
        
        # Handle your tool's stats format (content_stats.json) - keep existing logic
        elif isinstance(data, dict) and 'categories' in data:
            self.logger.debug("Detected stats JSON format with 'categories'")
            return self.create_simple_stats_flowchart(data)
        
        # Handle list format
        elif isinstance(data, list) and len(data) > 0:
            self.logger.debug(f"Detected list format with {len(data)} items")
            first_item = data[0]
            if 'contents_by_source' in first_item:
                self.logger.debug("List contains detailed JSON format")
                return self.create_flowchart_with_proper_hierarchy(first_item)
            else:
                self.logger.debug("List contains simple format")
                return self.create_simple_list_flowchart(data)
        
        self.logger.warning("No valid data structure found for flowchart generation")
        return "flowchart LR\n    START([No valid data found])\n"
    
    def create_simple_stats_flowchart(self, data: Dict) -> str:
        """Create simple left-to-right flowchart for stats format"""
        self.logger.debug("Creating simple stats flowchart")
        
        mermaid = 'flowchart LR\n'
        mermaid += '    START([Website Map])\n'
        
        categories = data.get('categories', {})
        overall = data.get('overall', {})
        
        total_endpoints = overall.get('total_endpoints', 0)
        total_js = overall.get('total_js_files', 0)
        
        self.logger.debug(f"Stats overview: {total_endpoints} endpoints, {total_js} JS files")
        
        overview_id = self.generate_unique_id('overview')
        mermaid += f'    {overview_id}["Total: {total_endpoints} endpoints<br/>{total_js} JS files"]\n'
        mermaid += f'    START --> {overview_id}\n'
        
        for category, count in categories.items():
            cat_id = self.generate_unique_id(f"cat_{category}")
            cat_display = category.replace('_', ' ').title()
            mermaid += f'    {cat_id}["{cat_display}<br/>{count} endpoints"]\n'
            mermaid += f'    {overview_id} --> {cat_id}\n'
            self.logger.debug(f"Added stats category: {cat_display} ({count} endpoints)")
        
        self.logger.info(f"Simple stats flowchart created with {len(categories)} categories")
        return mermaid
    
    def create_simple_list_flowchart(self, data: List) -> str:
        """Create simple left-to-right flowchart for list format"""
        self.logger.debug(f"Creating simple list flowchart for {len(data)} items")
        
        mermaid = 'flowchart LR\n'
        mermaid += '    START([Website Map])\n'
        
        for i, item in enumerate(data):
            overall = item.get('overall', {})
            total_endpoints = overall.get('total_endpoints', 0)
            total_js = overall.get('total_js_files', 0)
           
            self.logger.debug(f"List item {i+1}: {total_endpoints} endpoints, {total_js} JS files")
           
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
                self.logger.debug(f"Added list category: {cat_clean} ({count} items)")
        
        self.logger.info(f"Simple list flowchart created for {len(data)} analyses")
        return mermaid
   
    def convert_to_flowchart(self, json_data: Any) -> str:
        """Main conversion method"""
        self.logger.debug("Starting JSON to flowchart conversion")
        
        # Parse JSON if it's a string
        if isinstance(json_data, str):
            self.logger.debug("Input is string, parsing JSON")
            try:
                data = json.loads(json_data)
                self.logger.debug("JSON parsing successful")
            except json.JSONDecodeError as e:
                error_msg = f"Error parsing JSON: {e}"
                self.logger.error(error_msg)
                return f"Error parsing JSON: {e}"
        else:
            self.logger.debug("Input is already parsed data structure")
            data = json_data
       
        result = self.create_flowchart(data)
        self.logger.info("Flowchart conversion completed successfully")
        return result
    
    def generate_mermaid(self, urls):
        """Generate Mermaid flowcharts"""
        self.logger.info("Starting Mermaid flowchart generation process")
        self.banner.add_status("CONVERTING TO MERMAID FORMAT...")
        
        # Check if Mermaid CLI is available first
        if not self.mermaid_cli.is_available():
            self.logger.warning("Mermaid CLI not available - skipping diagram generation")
            self.banner.show_warning("Mermaid CLI not available - skipping diagram generation")
            self.banner.show_warning("Install with: npm install -g @mermaid-js/mermaid-cli")
            return
        
        self.logger.debug("Mermaid CLI is available, proceeding with generation")
        
        diagrams_created = 0
        diagrams_failed = 0
        processed_urls = 0

        self.banner.update_status("CONVERTING TO MERMAID FORMAT...")
        
        for url in urls:
            processed_urls += 1
            domain = self.domain_handler.extract_domain(url)
            if not domain:
                self.logger.warning(f"Could not extract domain from URL: {url}")
                continue
            
            self.logger.debug(f"Processing Mermaid generation for domain: {domain}")
            
            json_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template}_detailed.json"
            
            if not os.path.exists(json_file):
                self.logger.debug(f"JSON file does not exist: {json_file}")
                continue
                
            if os.path.getsize(json_file) == 0:
                self.logger.debug(f"JSON file is empty: {json_file}")
                continue
            
            self.logger.verbose(f"Processing JSON file: {json_file} ({os.path.getsize(json_file)} bytes)")
            
            try:
                # Load and parse JSON data
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                self.logger.debug(f"Successfully loaded JSON data for {domain}")
                
                # Convert to Mermaid format
                mermaid_output = self.convert_to_flowchart(json_data)
                
                if mermaid_output.startswith("Error:") or "Error parsing JSON:" in mermaid_output:
                    self.logger.error(f"Flowchart conversion failed for {domain}: {mermaid_output}")
                    diagrams_failed += 1
                    continue
                
                # Save Mermaid file
                mermaid_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template}_flowchart.mmd"
                
                with open(mermaid_file, 'w', encoding='utf-8') as f:
                    f.write(mermaid_output)
                
                mermaid_size = len(mermaid_output)
                self.logger.success(f"Saved Mermaid file: {mermaid_file} ({mermaid_size} bytes)")
                self.banner.add_status(f"Mermaid saved: {mermaid_file}")
                
                time.sleep(1)
                
                # Render to SVG/PNG
                render_success = True
                for ext in ['svg', 'png']:
                    output_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template}_flowchart.{ext}"
                    
                    try:
                        self.logger.debug(f"Rendering {ext.upper()} diagram: {output_file}")
                        success = self.mermaid_cli.render(mermaid_file, output_file)
                        
                        if success and os.path.exists(output_file):
                            output_size = os.path.getsize(output_file)
                            self.logger.success(f"Successfully rendered {ext.upper()}: {output_file} ({output_size} bytes)")
                            self.banner.show_completion(f"Rendered: {output_file}")
                        else:
                            self.logger.warning(f"Failed to render {ext.upper()}: {output_file}")
                            render_success = False
                            
                    except Exception as render_error:
                        self.logger.error(f"Error rendering {ext.upper()} for {domain}: {render_error}")
                        render_success = False
                
                if render_success:
                    diagrams_created += 1
                else:
                    diagrams_failed += 1
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for {domain}: {e}")
                self.banner.add_status(f"JSON error for {domain}: {e}")
                diagrams_failed += 1
                
            except Exception as e:
                self.logger.error(f"Unexpected error processing {domain}: {e}")
                self.banner.add_status(f"Mermaid error for {domain}: {e}")
                diagrams_failed += 1
                
            time.sleep(1)

        # Log final statistics
        self.logger.info(f"Mermaid generation completed:")
        self.logger.info(f"  - URLs processed: {processed_urls}")
        self.logger.info(f"  - Diagrams created: {diagrams_created}")
        self.logger.info(f"  - Diagrams failed: {diagrams_failed}")
        
        if diagrams_created > 0:
            self.logger.success(f"Successfully created diagrams for {diagrams_created} domains")
            self.banner.show_completion(f"Diagrams created for {diagrams_created} domains")
            
        if diagrams_failed > 0:
            self.logger.warning(f"Failed to create diagrams for {diagrams_failed} domains")
            self.banner.show_completion(f"{diagrams_failed} diagrams failed to generate")
            
        time.sleep(3)