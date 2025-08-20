# src/packages/CategoryProcessor.py
import json
import os
from src import config
from datetime import datetime
import time


class CategoryProcessor:
    def __init__(self, banner, domain_handler):
        self.templates_by_category = {}
        self.categorized_results = {}
        self.detailed_results = {}
        self.banner = banner
        self.domain_handler = domain_handler
      
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
    
    def reset_for_new_url(self):
        """Reset results for a new URL - call this before processing each URL"""
        self.categorized_results = {}
        self.detailed_results = {}
    
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
    
    def flatten_content_by_category(self, categorized_results=None):
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
    
    def get_all_content_flat(self, categorized_results=None):
        """Get all endpoints as flat list"""
        flattened = self.flatten_content_by_category(categorized_results)
        all_endpoints = []
        for endpoints in flattened.values():
            all_endpoints.extend(endpoints)
        return list(set(all_endpoints))
    
    def save_content_to_txt(self, endpoints, output_file):
        """Save endpoints to text file"""
        file_path = f"{config.OUTPUT_DIR}/{output_file}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a+') as f:
            for endpoint in endpoints:
                f.write(endpoint + '\n')
    
    def save_detailed_results_to_json(self, output_file):
        """Save detailed results to JSON with better error handling"""
        try:
            file_path = f"{config.OUTPUT_DIR}/{output_file}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Build the data structure
            results_by_source = {}
            all_content_by_category = {}
            
            for js_url, details in self.detailed_results.items():
                source_url = details['source_url']
                
                if source_url not in results_by_source:
                    results_by_source[source_url] = {'source_url': source_url, 'js_files': {}}
                
                results_by_source[source_url]['js_files'][js_url] = {
                    'js_url': js_url, 'categories': details['categories']
                }
                
                for category, endpoints in details['categories'].items():
                    if category not in all_content_by_category:
                        all_content_by_category[category] = set()
                    all_content_by_category[category].update(endpoints)
            
            # Convert sets to lists
            for category in all_content_by_category:
                all_content_by_category[category] = list(all_content_by_category[category])
            
            json_data = {
                'metadata': {
                    'total_sources': len(results_by_source),
                    'total_js_files': sum(len(source['js_files']) for source in results_by_source.values()),
                    'total_endpoints': sum(len(endpoints) for endpoints in all_content_by_category.values()),
                    'extraction_date': datetime.now().isoformat()
                },
                'contents_by_source': results_by_source,
                'contents_summary': all_content_by_category
            }
            
            # Use safe append method
            return self._safe_append_json_data(file_path, json_data)
            
        except Exception as e:
            print(f"Error in save_detailed_results_to_json: {e}")
            return None

    def save_flat_content_for_db(self, output_file):
        """Save flat endpoints for database with better error handling"""
        try:
            file_path = f"{config.OUTPUT_DIR}/{output_file}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            flat_endpoints = []
            content_id = 1
            
            for js_url, details in self.detailed_results.items():
                for category, endpoints in details['categories'].items():
                    for endpoint in endpoints:
                        flat_endpoints.append({
                            'id': content_id,
                            'endpoint': endpoint,
                            'category': category,
                            'source_url': details['source_url'],
                            'js_url': js_url,
                            'extraction_date': datetime.now().isoformat()
                        })
                        content_id += 1
            
            db_data = {
                'metadata': {
                    'total_records': len(flat_endpoints),
                    'extraction_date': datetime.now().isoformat(),
                    'schema_version': '1.0'
                },
                'endpoints': flat_endpoints
            }
            
            return self._safe_append_json_data(file_path, db_data)
            
        except Exception as e:
            print(f"Error in save_flat_content_for_db: {e}")
            return None

    def save_summary_stats_json(self, output_file):
        """Save summary statistics with better error handling"""
        try:
            file_path = f"{config.OUTPUT_DIR}/{output_file}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            stats = {
                'sources': {}, 
                'categories': {}, 
                'overall': {
                    'total_sources': 0, 
                    'total_js_files': 0, 
                    'total_endpoints': 0, 
                    'unique_endpoints': 0
                }
            }
            
            all_unique_endpoints = set()
            category_totals = {}
            
            for js_url, details in self.detailed_results.items():
                source_url = details['source_url']
                
                if source_url not in stats['sources']:
                    stats['sources'][source_url] = {
                        'js_files_count': 0, 
                        'total_endpoints': 0, 
                        'categories': {}
                    }
                
                stats['sources'][source_url]['js_files_count'] += 1
                
                for category, endpoints in details['categories'].items():
                    content_count = len(endpoints)
                    stats['sources'][source_url]['total_endpoints'] += content_count
                    stats['sources'][source_url]['categories'][category] = \
                        stats['sources'][source_url]['categories'].get(category, 0) + content_count
                    category_totals[category] = category_totals.get(category, 0) + content_count
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
            
            return self._safe_append_json_data(file_path, stats)
            
        except Exception as e:
            print(f"Error in save_summary_stats_json: {e}")
            return None

    def _safe_append_json_data(self, file_path, json_data):
        """Safely append JSON data with error recovery"""
        import json
        
        # Method 1: Try simple append
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False)
            return json_data
            
        except Exception as e:
            print(f"Simple append failed for {file_path}: {e}")
            
            # Method 2: Try to read existing, append, and rewrite
            try:
                existing_data = []
                
                # Try to read existing data
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        
                        if content:
                            # Try to parse as JSON array first
                            try:
                                existing_data = json.loads(content)
                                if not isinstance(existing_data, list):
                                    existing_data = [existing_data]
                            except json.JSONDecodeError:
                                # Handle concatenated JSON objects
                                if content.startswith('{'):
                                    fixed_content = '[' + content.replace('}{', '},{') + ']'
                                    try:
                                        existing_data = json.loads(fixed_content)
                                    except:
                                        existing_data = []
                                
                    except Exception:
                        existing_data = []
                
                # Append new data
                existing_data.append(json_data)
                
                # Write back everything
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=2, ensure_ascii=False)
                    
                return json_data
                
            except Exception as e2:
                print(f"Recovery method also failed for {file_path}: {e2}")
                
                # Method 3: Create new file with just this data
                try:
                    backup_path = f"{file_path}.corrupted_{int(time.time())}"
                    if os.path.exists(file_path):
                        os.rename(file_path, backup_path)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump([json_data], f, indent=2, ensure_ascii=False)
                        
                    print(f"Created new file {file_path}, old file backed up as {backup_path}")
                    return json_data
                    
                except Exception as e3:
                    print(f"All methods failed for {file_path}: {e3}")
                    return None
    
    def _get_current_timestamp(self):
        """Get current timestamp"""
        return datetime.now().isoformat()
    
    def get_category_stats(self, categorized_results=None):
        """Get category statistics"""
        contents_by_category = self.flatten_content_by_category(categorized_results)
        
        return {
            'total_categories': len(contents_by_category),
            'total_endpoints': sum(len(endpoints) for endpoints in contents_by_category.values()),
            'categories': {
                category: {'count': len(endpoints), 'endpoints': endpoints}
                for category, endpoints in contents_by_category.items()
            }
        }