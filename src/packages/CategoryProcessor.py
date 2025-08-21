# src/packages/CategoryProcessor.py
import json
import os
from src import config
from datetime import datetime
import time
from src.utils.Logger import get_logger



class CategoryProcessor:
    def __init__(self, banner, domain_handler):
        self.templates_by_category = {}
        self.categorized_results = {}
        self.detailed_results = {}
        self.banner = banner
        self.domain_handler = domain_handler
        self.logger = get_logger()
      
    def _is_false_positive(self, match, category):
        """Check if match is a false positive"""
        if not match or len(match) > 200:
            self.logger.debug(f"Skipping false positive: {match}")
            return True
        
        bad_patterns = ['facebook.com/legal', 'w3.org', 'adobe.com', 'xmlns', 'namespace', 'react.dev/errors']
        if any(bad in match.lower() for bad in bad_patterns):
            self.logger.debug(f"Skipping false positive: {match}")
            return True
        
        # Category-specific checks
        if category == 'websockets':
            is_false = not any(x in match.lower() for x in ['ws://', 'wss://', 'websocket', 'socket.io'])
            if is_false:
                self.logger.debug(f"False positive websocket: {match}")
            return is_false
        elif category == 'api_endpoints':
            is_false = not any(x in match.lower() for x in ['api', 'rest', 'graphql', 'webhook']) and not match.startswith('/v')
            if is_false:
                self.logger.debug(f"False positive API endpoint: {match}")
            return is_false
        elif category == 'api_keys_tokens':
            is_false = len(match) < 10
            if is_false:
                self.logger.debug(f"False positive token (too short): {match}")
            return is_false
        elif category == 'external_api_domains':
            is_false = not any(x in match.lower() for x in ['api.', 'graph.', 'googleapis'])
            if is_false:
                self.logger.debug(f"False positive external API: {match}")
            return is_false
        
        return False
    
    def reset_for_new_url(self):
        """Reset results for a new URL - call this before processing each URL"""
        self.logger.debug("Resetting for new URL")
        self.categorized_results = {}
        self.detailed_results = {}
    
    def merge_categorized_results(self, new_results):
        """Merge new results"""
        self.logger.debug(f"Merging results with {len(new_results)} new categories")

        for category, matches in new_results.items():
            if category not in self.categorized_results:
                self.categorized_results[category] = []
            
            if isinstance(matches, list):
                self.categorized_results[category].extend(matches)
                self.logger.verbose(f"Merged {len(matches)} matches for {category}")
            else:
                total_matches = 0
                for template_matches in matches.values():
                    self.categorized_results[category].extend(template_matches)
                    total_matches += len(template_matches)
                self.logger.verbose(f"Merged {total_matches} matches for {category}")
    
    def flatten_content_by_category(self, categorized_results=None):
        """Flatten results by category"""
        results = categorized_results or self.categorized_results
        flattened = {}

        self.logger.debug(f"Flattening results with {len(results)} categories")
        
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
                self.logger.verbose(f"Flattened {len(endpoints)} endpoints for {category}")
        
        self.logger.debug(f"Flattened results: {flattened}")
        return flattened
    
    def get_all_content_flat(self, categorized_results=None):
        """Get all endpoints as flat list"""
        flattened = self.flatten_content_by_category(categorized_results)
        all_endpoints = []
        for endpoints in flattened.values():
            all_endpoints.extend(endpoints)

        unique_endpoints = list(set(all_endpoints))
        self.logger.debug(f"Unique endpoints: {unique_endpoints}")
        
        return unique_endpoints
    
    def save_content_to_txt(self, endpoints, output_file):
        """Save endpoints to text file"""
        file_path = f"{config.OUTPUT_DIR}/{output_file}"
        self.logger.debug(f"Saving {len(endpoints)} endpoints to {file_path}")

        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'a+') as f:
                for endpoint in endpoints:
                    f.write(endpoint + '\n')

            self.logger.info(f"Saved {len(endpoints)} endpoints to {file_path}", "success")
        except Exception as e:
            self.logger.error(f"Error saving endpoints to {file_path}: {e}")
        
    def save_detailed_results_to_json(self, output_file):
        """Save detailed results to JSON with better error handling"""
        self.logger.debug(f"Saving detailed results to {output_file}")

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
            
            self.logger.verbose(f"Saving detailed results to {file_path}")

            # Use safe append method
            result = self._safe_append_json_data(file_path, json_data)
            if result:
                self.logger.info(f"Saved detailed results to {file_path}", "success")
            else:
                self.logger.error(f"Failed to save detailed results to {file_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in save_detailed_results_to_json: {e}")
            return None

    def save_flat_content_for_db(self, output_file):
        """Save flat endpoints for database with better error handling"""
        self.logger.debug(f"Saving flat endpoints for database to {output_file}")

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

            self.logger.verbose(f"Saving flat endpoints for database to {file_path}")

            result = self._safe_append_json_data(file_path, db_data)
            if result:
                self.logger.info(f"Saved flat endpoints for database to {file_path}", "success")
            else:
                self.logger.error(f"Failed to save flat endpoints for database to {file_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in save_flat_content_for_db: {e}")
            return None

    def save_summary_stats_json(self, output_file):
        """Save summary statistics with better error handling"""
        self.logger.debug(f"Saving summary statistics to {output_file}")

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

            self.logger.verbose(f"Saving summary statistics to {file_path}")
            self.logger.verbose(f"Total Endpoints: {stats['overall']['total_endpoints']}")
            self.logger.verbose(f"Top categories: {stats['metadata']['top_categories']}")

            result = self._safe_append_json_data(file_path, stats)
            if result:
                self.logger.info(f"Saved summary statistics to {file_path}", "success")
            else:
                self.logger.error(f"Failed to save summary statistics to {file_path}")
            return result
            
        except Exception as e:
            self.logging.error(f"Error in save_summary_stats_json: {e}")
            return None

    def _safe_append_json_data(self, file_path, json_data):
        """Safely append JSON data with error recovery"""
        self.logger.debug(f"Saving JSON data to {file_path}")
        
        # Method 1: Try simple append
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False)
            self.logger.debug(f"Simple append succeeded for {file_path}")
            return json_data
            
        except Exception as e:
            self.logger.warning(f"Simple append failed for {file_path}: {e}")
            
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
                                self.logger.debug(f"Parsed existing data as JSON array")

                            except json.JSONDecodeError:
                                # Handle concatenated JSON objects
                                self.logger.debug(f"Parsing existing data as concatenated JSON objects")
                                if content.startswith('{'):
                                    fixed_content = '[' + content.replace('}{', '},{') + ']'
                                    try:
                                        existing_data = json.loads(fixed_content)
                                        self.logger.debug(f"Parsed fixed content as JSON array")
                                    except:
                                        existing_data = []
                                        self.logger.warning(f"Failed to parse fixed content as JSON array")
                                
                    except Exception:
                        self.logger.warning(f"Failed to read existing data")
                        existing_data = []
                
                # Append new data
                existing_data.append(json_data)
                
                # Write back everything
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=2, ensure_ascii=False)
                    
                self.logger.debug(f"Appended new data to {file_path}")
                return json_data
                
            except Exception as e2:
                self.logger.warning(f"Appending failed for {file_path}: {e2}")
                
                # Method 3: Create new file with just this data
                try:
                    backup_path = f"{file_path}.corrupted_{int(time.time())}"
                    if os.path.exists(file_path):
                        os.rename(file_path, backup_path)
                        self.logger.warning(f"Renamed existing file to {backup_path}")
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump([json_data], f, indent=2, ensure_ascii=False)
                        
                    self.logger.warning(f"Created new file {file_path} with just this data")
                    return json_data
                    
                except Exception as e3:
                    self.logger.error(f"Creating new file failed for {file_path}: {e3}")
                    return None
    
    def _get_current_timestamp(self):
        """Get current timestamp"""
        return datetime.now().isoformat()
    
    def get_category_stats(self, categorized_results=None):
        """Get category statistics"""
        contents_by_category = self.flatten_content_by_category(categorized_results)

        stats = {
            'total_categories': len(contents_by_category),
            'total_endpoints': sum(len(endpoints) for endpoints in contents_by_category.values()),
            'categories': {
                category: {'count': len(endpoints), 'endpoints': endpoints}
                for category, endpoints in contents_by_category.items()
            }
        }
        
        self.logger.debug(f"Category stats: {stats['total_categories']} categories, {stats['total_endpoints']} endpoints")
        return stats