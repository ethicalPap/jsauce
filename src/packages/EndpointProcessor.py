# src/packages/EndpointProcessor.py
import re
import json
import os
import config

class EndpointProcessor:
    def __init__(self):
        self.templates_by_category = {}
        self.categorized_results = {}
        self.detailed_results = {}  # Store results with context
    
    def parse_templates_by_category(self, template_lines):
        """Parse template file and organize regex patterns by category"""
        templates_by_category = {}
        current_category = None
        orphaned_patterns = []
        
        for line_num, line in enumerate(template_lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # Check if this line is a category header
            if line.startswith('#') and line.endswith(']'):
                current_category = line[2:-1]  # Remove brackets
                templates_by_category[current_category] = {}
                print(f"Found category: {current_category}")  # Debug
            elif current_category and line:
                # Add regex pattern to current category
                templates_by_category[current_category][line] = line
            elif line and not current_category:
                # This is an orphaned pattern without a category
                orphaned_patterns.append((line_num, line))
                print(f"Warning: Orphaned pattern at line {line_num}: {line[:50]}...")
            elif line and current_category is None:
                # Skip patterns that don't have a valid category
                print(f"Warning: Skipping pattern without category found at line {line_num}: {line[:50]}...") #debugging only
        
        # Handle orphaned patterns by putting them in a default category
        if orphaned_patterns:
            print(f"Found {len(orphaned_patterns)} orphaned patterns, putting them in 'misc_patterns' category")
            templates_by_category['misc_patterns'] = {}
            for line_num, pattern in orphaned_patterns:
                templates_by_category['misc_patterns'][pattern] = pattern
        
        print(f"Total categories parsed: {len(templates_by_category)}")  # Debug
        
        # Debug: Print first few categories
        for i, (cat, templates) in enumerate(templates_by_category.items()):
            if i < 5:  # Only show first 5
                print(f"Category {i+1}: {cat} ({len(templates)} patterns)")
        
        # Validate categories
        valid_categories = {}
        for category, patterns in templates_by_category.items():
            # Skip categories that look like regex patterns
            if any(char in category for char in ['(', ')', '\\', '+', '*', '?', '[', ']']) and category != 'misc_patterns':
                # print(f"Warning: Skipping invalid category name: {category[:50]}...")
                continue
            if len(category) > 100:
                print(f"Warning: Skipping overly long category name: {category[:50]}...")
                continue
            valid_categories[category] = patterns
        
        self.templates_by_category = valid_categories
        return valid_categories
    
    def search_js_content_by_category_with_context(self, js_content, js_url, source_url, templates_by_category=None):
        """Search JS content for patterns organized by category with full context"""
        if templates_by_category is None:
            templates_by_category = self.templates_by_category
            
        results_by_category = {}
        
        for category, templates in templates_by_category.items():
            category_matches = []
            
            # Debug: Skip invalid category names
            if category.startswith('[') or len(category) > 50:
                continue
            
            for template, regex in templates.items():
                try:
                    matches = re.findall(regex, js_content, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        # Handle tuples from regex groups
                        if matches and isinstance(matches[0], tuple):
                            flat_matches = []
                            for match in matches:
                                if isinstance(match, tuple):
                                    for group in match:
                                        if group and group.strip():
                                            flat_matches.append(group.strip())
                                            break
                                else:
                                    flat_matches.append(str(match).strip())
                            matches = flat_matches
                        else:
                            matches = [str(match).strip() for match in matches if str(match).strip()]
                        
                        # Filter out false positives
                        filtered_matches = self._filter_false_positives(matches, category)
                        category_matches.extend(filtered_matches)
                        
                except re.error as e:
                    print(f"Invalid regex '{regex}' in category '{category}': {e}")
                    continue
                except Exception as e:
                    print(f"Error processing regex '{regex}' in category '{category}': {e}")
                    continue
            
            if category_matches:
                unique_matches = list(dict.fromkeys(category_matches))
                results_by_category[category] = unique_matches
        
        # Store detailed results with context
        if js_url not in self.detailed_results:
            self.detailed_results[js_url] = {
                'source_url': source_url,
                'js_url': js_url,
                'categories': {}
            }
        
        for category, matches in results_by_category.items():
            if category not in self.detailed_results[js_url]['categories']:
                self.detailed_results[js_url]['categories'][category] = []
            self.detailed_results[js_url]['categories'][category].extend(matches)
            # Remove duplicates
            self.detailed_results[js_url]['categories'][category] = list(dict.fromkeys(
                self.detailed_results[js_url]['categories'][category]
            ))
        
        return results_by_category
    
    def search_js_content_by_category(self, js_content, templates_by_category=None):
        """Search JS content for patterns organized by category"""
        if templates_by_category is None:
            templates_by_category = self.templates_by_category
            
        results_by_category = {}
        
        for category, templates in templates_by_category.items():
            category_matches = []
            
            # Debug: Print category being processed
            if category.startswith('[') or len(category) > 50:
                print(f"Warning: Invalid category name detected: {category[:50]}...")
                continue
            
            for template, regex in templates.items():
                try:
                    matches = re.findall(regex, js_content, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        # Handle tuples from regex groups
                        if matches and isinstance(matches[0], tuple):
                            # Flatten tuples and remove empty strings
                            flat_matches = []
                            for match in matches:
                                if isinstance(match, tuple):
                                    # Take the first non-empty group from the tuple
                                    for group in match:
                                        if group and group.strip():
                                            flat_matches.append(group.strip())
                                            break
                                else:
                                    flat_matches.append(str(match).strip())
                            matches = flat_matches
                        else:
                            # Clean up string matches
                            matches = [str(match).strip() for match in matches if str(match).strip()]
                        
                        # Filter out obvious false positives
                        filtered_matches = self._filter_false_positives(matches, category)
                        category_matches.extend(filtered_matches)
                        
                except re.error as e:
                    print(f"Invalid regex '{regex}' in category '{category}': {e}")
                    continue
                except Exception as e:
                    print(f"Error processing regex '{regex}' in category '{category}': {e}")
                    continue
            
            if category_matches:
                # Remove duplicates while preserving order
                unique_matches = list(dict.fromkeys(category_matches))
                results_by_category[category] = unique_matches
        
        return results_by_category
    
    def _filter_false_positives(self, matches, category):
        """Filter out obvious false positives based on category"""
        filtered = []
        
        for match in matches:
            match = str(match).strip()
            if not match:
                continue
                
            # Skip obviously bad matches - common false positives
            skip_patterns = [
                'facebook.com/legal/license',
                'w3.org',
                'adobe.com',
                'macromedia.com',
                'xmlns',
                'xap/1.0',
                'Math/MathML',
                'xlink',
                'namespace',
                'http://www.w3.org',
                'https://www.w3.org',
                'xml:lang',
                'xmlns:',
                'errors/',
                'react.dev/errors',
                'invariant/',
                'selfxss'
            ]
            
            if any(bad in match.lower() for bad in skip_patterns):
                continue
            
            # Skip very long URLs that are likely false positives
            if len(match) > 200:
                continue
                
            # Category-specific filtering
            if category == 'websockets':
                if not (match.startswith('ws://') or match.startswith('wss://') or 
                       'websocket' in match.lower() or 'socket.io' in match.lower() or
                       '/ws/' in match.lower()):
                    continue
            elif category == 'api_endpoints':
                if not ('api' in match.lower() or match.startswith('/v') or 
                       'rest' in match.lower() or 'graphql' in match.lower() or
                       '/rpc/' in match.lower() or 'webhook' in match.lower()):
                    continue
            elif category == 'api_keys_tokens':
                if len(match) < 10:  # Skip very short matches for auth tokens
                    continue
            elif category == 'external_api_domains':
                # Only keep actual API domains
                if not any(api_domain in match.lower() for api_domain in [
                    'api.', 'graph.', 'maps.googleapis', 'youtube.googleapis'
                ]):
                    continue
            
            filtered.append(match)
        
        return filtered
    
    def merge_categorized_results(self, new_results):
        """Merge new categorized results into existing results"""
        for category, matches in new_results.items():
            if category not in self.categorized_results:
                self.categorized_results[category] = []
            
            # Since new_results now contains lists of matches per category
            if isinstance(matches, list):
                self.categorized_results[category].extend(matches)
            elif isinstance(matches, dict):
                # Handle old format for backwards compatibility
                for template, template_matches in matches.items():
                    self.categorized_results[category].extend(template_matches)
    
    def flatten_endpoints_by_category(self, categorized_results=None):
        """Flatten categorized results to get unique endpoints per category"""
        if categorized_results is None:
            categorized_results = self.categorized_results
            
        endpoints_by_category = {}
        
        for category, matches in categorized_results.items():
            if isinstance(matches, list):
                # New format - already flattened
                unique_endpoints = list(dict.fromkeys(matches))
            else:
                # Old format - need to flatten from templates
                all_endpoints = []
                for template, template_matches in matches.items():
                    all_endpoints.extend(template_matches)
                unique_endpoints = list(dict.fromkeys(all_endpoints))
            
            if unique_endpoints:
                endpoints_by_category[category] = unique_endpoints
        
        return endpoints_by_category
    
    def get_all_endpoints_flat(self, categorized_results=None):
        """Get all endpoints as a flat list"""
        endpoints_by_category = self.flatten_endpoints_by_category(categorized_results)
        all_endpoints = []
        
        for endpoints in endpoints_by_category.values():
            all_endpoints.extend(endpoints)
        
        return list(set(all_endpoints))  # Remove duplicates
    
    # output endpoints to txt
    def save_endpoints_to_txt(self, endpoints, output_file):
        os.makedirs(f"{config.OUTPUT_DIR}", exist_ok=True)
        with open(f"{config.OUTPUT_DIR}{output_file}", 'w') as file:
            for endpoint in endpoints:
                file.write(endpoint + '\n')
    
    def save_detailed_results_to_json(self, output_file):
        """Save detailed results with context to clean JSON file for database import"""
        os.makedirs(f"{config.OUTPUT_DIR}", exist_ok=True)
        
        # Organize results by source URL
        results_by_source = {}
        all_endpoints_by_category = {}
        
        for js_url, details in self.detailed_results.items():
            source_url = details['source_url']
            
            if source_url not in results_by_source:
                results_by_source[source_url] = {
                    'source_url': source_url,
                    'js_files': {}
                }
            
            results_by_source[source_url]['js_files'][js_url] = {
                'js_url': js_url,
                'categories': details['categories']
            }
            
            # Also build flat summary by category
            for category, endpoints in details['categories'].items():
                if category not in all_endpoints_by_category:
                    all_endpoints_by_category[category] = set()
                all_endpoints_by_category[category].update(endpoints)
        
        # Convert sets to lists for JSON serialization
        for category in all_endpoints_by_category:
            all_endpoints_by_category[category] = list(all_endpoints_by_category[category])
        
        # Create clean JSON structure
        json_data = {
            'metadata': {
                'total_sources': len(results_by_source),
                'total_js_files': sum(len(source['js_files']) for source in results_by_source.values()),
                'total_endpoints': sum(len(endpoints) for endpoints in all_endpoints_by_category.values()),
                'extraction_date': self._get_current_timestamp()
            },
            'endpoints_by_source': results_by_source,
            'endpoints_summary': all_endpoints_by_category
        }
        
        with open(f"{config.OUTPUT_DIR}{output_file}", 'w', encoding='utf-8') as file:
            json.dump(json_data, file, indent=2)
        
        return json_data


    def save_flat_endpoints_for_db(self, output_file):
        """Save endpoints in a flat structure optimized for database import"""
        os.makedirs(f"{config.OUTPUT_DIR}", exist_ok=True)
        
        flat_endpoints = []
        endpoint_id = 1
        
        for js_url, details in self.detailed_results.items():
            source_url = details['source_url']
            
            for category, endpoints in details['categories'].items():
                for endpoint in endpoints:
                    flat_endpoints.append({
                        'id': endpoint_id,
                        'endpoint': endpoint,
                        'category': category,
                        'source_url': source_url,
                        'js_url': js_url,
                        'extraction_date': self._get_current_timestamp()
                    })
                    endpoint_id += 1
        
        # Create database-ready structure
        db_data = {
            'metadata': {
                'total_records': len(flat_endpoints),
                'extraction_date': self._get_current_timestamp(),
                'schema_version': '1.0'
            },
            'endpoints': flat_endpoints
        }
        
        with open(f"{config.OUTPUT_DIR}{output_file}", 'w', encoding='utf-8') as file:
            json.dump(db_data, file, indent=2)
        
        return db_data

    def save_summary_stats_json(self, output_file):
        """Save summary statistics in JSON format"""
        os.makedirs(f"{config.OUTPUT_DIR}", exist_ok=True)
        
        # Calculate statistics
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
            
            # Initialize source stats if not exists
            if source_url not in stats['sources']:
                stats['sources'][source_url] = {
                    'js_files_count': 0,
                    'total_endpoints': 0,
                    'categories': {}
                }
            
            stats['sources'][source_url]['js_files_count'] += 1
            
            for category, endpoints in details['categories'].items():
                endpoint_count = len(endpoints)
                
                # Update source stats
                stats['sources'][source_url]['total_endpoints'] += endpoint_count
                if category not in stats['sources'][source_url]['categories']:
                    stats['sources'][source_url]['categories'][category] = 0
                stats['sources'][source_url]['categories'][category] += endpoint_count
                
                # Update category totals
                if category not in category_totals:
                    category_totals[category] = 0
                category_totals[category] += endpoint_count
                
                # Add to unique endpoints set
                all_unique_endpoints.update(endpoints)
        
        # Finalize stats
        stats['categories'] = category_totals
        stats['overall']['total_sources'] = len(stats['sources'])
        stats['overall']['total_js_files'] = sum(source['js_files_count'] for source in stats['sources'].values())
        stats['overall']['total_endpoints'] = sum(category_totals.values())
        stats['overall']['unique_endpoints'] = len(all_unique_endpoints)
        stats['metadata'] = {
            'extraction_date': self._get_current_timestamp(),
            'top_categories': sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        }
        
        with open(f"{config.OUTPUT_DIR}{output_file}", 'w', encoding='utf-8') as file:
            json.dump(stats, file, indent=2)
        
        return stats

    def _get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_category_stats(self, categorized_results=None):
        """Get statistics about categories"""
        if categorized_results is None:
            categorized_results = self.categorized_results
            
        endpoints_by_category = self.flatten_endpoints_by_category(categorized_results)
        
        stats = {
            'total_categories': len(endpoints_by_category),
            'total_endpoints': sum(len(endpoints) for endpoints in endpoints_by_category.values()),
            'categories': {}
        }
        
        for category, endpoints in endpoints_by_category.items():
            stats['categories'][category] = {
                'count': len(endpoints),
                'endpoints': endpoints
            }
        
        return stats