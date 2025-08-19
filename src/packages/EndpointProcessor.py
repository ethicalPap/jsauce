# src/packages/EndpointProcessor.py
import re
import json
import os
import yaml
from src import config
from datetime import datetime
from src.utils.Banner import Banner
import time

jsauce_banner = Banner()

class EndpointProcessor:
    def __init__(self):
        self.templates_by_category = {}
        self.categorized_results = {}
        self.detailed_results = {}
    
    def load_patterns_from_yaml(self, yaml_file_path):
        """Load regex patterns from YAML file"""
        try:
            with open(yaml_file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or not isinstance(data, dict):
                jsauce_banner.update_status(f"Warning: Invalid YAML file {yaml_file_path}")
                time.sleep(2)
                return {}
            
            templates = {}
            for category, cat_data in data.items():
                if isinstance(cat_data, dict) and 'patterns' in cat_data:
                    templates[category] = {p: p for p in cat_data['patterns']}
            
            self.templates_by_category = templates
            jsauce_banner.update_status(f"Total categories: {len(templates)}")
            return templates
            
        except Exception as e:
            jsauce_banner.update_status(f"Error loading YAML: {e}")
            time.sleep(2)
            return {}
    
    def parse_templates_by_category(self, template_lines):
        """Legacy text file parser"""
        templates = {}
        current_category = None
        
        for line_num, line in enumerate(template_lines, 1):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('#[') and line.endswith(']'):
                current_category = line[2:-1]
                templates[current_category] = {}
            elif current_category and line:
                templates[current_category][line] = line
        
        self.templates_by_category = templates
        return templates
    
    def search_js_content_by_category_with_context(self, js_content, js_url, source_url, templates_by_category=None):
        """Search JS content with context"""
        templates = templates_by_category or self.templates_by_category
        results = {}
        
        for category, patterns in templates.items():
            matches = []
            for pattern in patterns:
                try:
                    flags = re.MULTILINE if any(k in category.lower() for k in ['token', 'key', 'secret', 'auth']) else re.IGNORECASE | re.MULTILINE
                    found = re.findall(pattern, js_content, flags)
                    
                    # Handle tuples from capture groups
                    if found and isinstance(found[0], tuple):
                        found = [next((g for g in match if g and g.strip()), '') for match in found]
                    
                    matches.extend([m.strip() for m in found if m and m.strip()])
                except:
                    continue
            
            if matches:
                filtered = [m for m in matches if not self._is_false_positive(m, category)]
                if filtered:
                    results[category] = list(dict.fromkeys(filtered))
        
        # Store results
        if js_url not in self.detailed_results:
            self.detailed_results[js_url] = {'source_url': source_url, 'js_url': js_url, 'categories': {}}
        
        for category, matches in results.items():
            if category not in self.detailed_results[js_url]['categories']:
                self.detailed_results[js_url]['categories'][category] = []
            self.detailed_results[js_url]['categories'][category].extend(matches)
            self.detailed_results[js_url]['categories'][category] = list(dict.fromkeys(
                self.detailed_results[js_url]['categories'][category]
            ))
        
        return results
    
    def search_js_content_by_category(self, js_content, templates_by_category=None):
        """Search JS content by category"""
        templates = templates_by_category or self.templates_by_category
        results = {}
        
        for category, patterns in templates.items():
            matches = []
            for pattern in patterns:
                try:
                    flags = re.MULTILINE if any(k in category.lower() for k in ['token', 'key', 'secret', 'auth']) else re.IGNORECASE | re.MULTILINE
                    found = re.findall(pattern, js_content, flags)
                    
                    if found and isinstance(found[0], tuple):
                        found = [next((g for g in match if g and g.strip()), '') for match in found]
                    
                    matches.extend([m.strip() for m in found if m and m.strip()])
                except:
                    continue
            
            if matches:
                filtered = [m for m in matches if not self._is_false_positive(m, category)]
                if filtered:
                    results[category] = list(dict.fromkeys(filtered))
        
        return results
    
    def _is_false_positive(self, match, category):
        """Check if match is a false positive"""
        if not match or len(match) > 200:
            return True
        
        bad_patterns = ['facebook.com/legal', 'w3.org', 'adobe.com', 'xmlns', 'namespace', 'react.dev/errors']
        if any(bad in match.lower() for bad in bad_patterns):
            return True
        
        # Category-specific checks
        if category == 'websockets':
            return not any(x in match.lower() for x in ['ws://', 'wss://', 'websocket', 'socket.io'])
        elif category == 'api_endpoints':
            return not any(x in match.lower() for x in ['api', 'rest', 'graphql', 'webhook']) and not match.startswith('/v')
        elif category == 'api_keys_tokens':
            return len(match) < 10
        elif category == 'external_api_domains':
            return not any(x in match.lower() for x in ['api.', 'graph.', 'googleapis'])
        
        return False
    
    def merge_categorized_results(self, new_results):
        """Merge new results"""
        for category, matches in new_results.items():
            if category not in self.categorized_results:
                self.categorized_results[category] = []
            
            if isinstance(matches, list):
                self.categorized_results[category].extend(matches)
            else:
                for template_matches in matches.values():
                    self.categorized_results[category].extend(template_matches)
    
    def flatten_endpoints_by_category(self, categorized_results=None):
        """Flatten results by category"""
        results = categorized_results or self.categorized_results
        flattened = {}
        
        for category, matches in results.items():
            if isinstance(matches, list):
                endpoints = list(dict.fromkeys(matches))
            else:
                all_endpoints = []
                for template_matches in matches.values():
                    all_endpoints.extend(template_matches)
                endpoints = list(dict.fromkeys(all_endpoints))
            
            if endpoints:
                flattened[category] = endpoints
        
        return flattened
    
    def get_all_endpoints_flat(self, categorized_results=None):
        """Get all endpoints as flat list"""
        flattened = self.flatten_endpoints_by_category(categorized_results)
        all_endpoints = []
        for endpoints in flattened.values():
            all_endpoints.extend(endpoints)
        return list(set(all_endpoints))
    
    def save_endpoints_to_txt(self, endpoints, output_file):
        """Save endpoints to text file"""
        file_path = f"{config.OUTPUT_DIR}/{output_file}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a+') as f:
            for endpoint in endpoints:
                f.write(endpoint + '\n')
    
    def save_detailed_results_to_json(self, output_file):
        """Save detailed results to JSON"""
        file_path = f"{config.OUTPUT_DIR}/{output_file}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        results_by_source = {}
        all_endpoints_by_category = {}
        
        for js_url, details in self.detailed_results.items():
            source_url = details['source_url']
            
            if source_url not in results_by_source:
                results_by_source[source_url] = {'source_url': source_url, 'js_files': {}}
            
            results_by_source[source_url]['js_files'][js_url] = {
                'js_url': js_url, 'categories': details['categories']
            }
            
            for category, endpoints in details['categories'].items():
                if category not in all_endpoints_by_category:
                    all_endpoints_by_category[category] = set()
                all_endpoints_by_category[category].update(endpoints)
        
        for category in all_endpoints_by_category:
            all_endpoints_by_category[category] = list(all_endpoints_by_category[category])
        
        json_data = {
            'metadata': {
                'total_sources': len(results_by_source),
                'total_js_files': sum(len(source['js_files']) for source in results_by_source.values()),
                'total_endpoints': sum(len(endpoints) for endpoints in all_endpoints_by_category.values()),
                'extraction_date': datetime.now().isoformat()
            },
            'endpoints_by_source': results_by_source,
            'endpoints_summary': all_endpoints_by_category
        }
        
        with open(file_path, 'a+', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        
        return json_data
    
    def save_flat_endpoints_for_db(self, output_file):
        """Save flat endpoints for database"""
        file_path = f"{config.OUTPUT_DIR}/{output_file}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        flat_endpoints = []
        endpoint_id = 1
        
        for js_url, details in self.detailed_results.items():
            for category, endpoints in details['categories'].items():
                for endpoint in endpoints:
                    flat_endpoints.append({
                        'id': endpoint_id,
                        'endpoint': endpoint,
                        'category': category,
                        'source_url': details['source_url'],
                        'js_url': js_url,
                        'extraction_date': datetime.now().isoformat()
                    })
                    endpoint_id += 1
        
        db_data = {
            'metadata': {
                'total_records': len(flat_endpoints),
                'extraction_date': datetime.now().isoformat(),
                'schema_version': '1.0'
            },
            'endpoints': flat_endpoints
        }
        
        with open(file_path, 'a+', encoding='utf-8') as f:
            json.dump(db_data, f, indent=2)
        
        return db_data
    
    def save_summary_stats_json(self, output_file):
        """Save summary statistics"""
        file_path = f"{config.OUTPUT_DIR}/{output_file}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        stats = {'sources': {}, 'categories': {}, 'overall': {'total_sources': 0, 'total_js_files': 0, 'total_endpoints': 0, 'unique_endpoints': 0}}
        all_unique_endpoints = set()
        category_totals = {}
        
        for js_url, details in self.detailed_results.items():
            source_url = details['source_url']
            
            if source_url not in stats['sources']:
                stats['sources'][source_url] = {'js_files_count': 0, 'total_endpoints': 0, 'categories': {}}
            
            stats['sources'][source_url]['js_files_count'] += 1
            
            for category, endpoints in details['categories'].items():
                endpoint_count = len(endpoints)
                stats['sources'][source_url]['total_endpoints'] += endpoint_count
                stats['sources'][source_url]['categories'][category] = stats['sources'][source_url]['categories'].get(category, 0) + endpoint_count
                category_totals[category] = category_totals.get(category, 0) + endpoint_count
                all_unique_endpoints.update(endpoints)
        
        stats['categories'] = category_totals
        stats['overall'] = {
            'total_sources': len(stats['sources']),
            'total_js_files': sum(s['js_files_count'] for s in stats['sources'].values()),
            'total_endpoints': sum(category_totals.values()),
            'unique_endpoints': len(all_unique_endpoints)
        }
        stats['metadata'] = {
            'extraction_date': datetime.now().isoformat(),
            'top_categories': sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        }
        
        with open(file_path, 'a+', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        
        return stats
    
    def _get_current_timestamp(self):
        """Get current timestamp"""
        return datetime.now().isoformat()
    
    def get_category_stats(self, categorized_results=None):
        """Get category statistics"""
        endpoints_by_category = self.flatten_endpoints_by_category(categorized_results)
        
        return {
            'total_categories': len(endpoints_by_category),
            'total_endpoints': sum(len(endpoints) for endpoints in endpoints_by_category.values()),
            'categories': {
                category: {'count': len(endpoints), 'endpoints': endpoints}
                for category, endpoints in endpoints_by_category.items()
            }
        }