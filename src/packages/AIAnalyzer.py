# src/packages/AISecurityAnalyzer.py
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from src import config
from src.utils.Logger import get_logger

# AI-powered security analysis for JSauce findings
class AISecurityAnalyzer:
    
    def __init__(self, banner, domain_handler, template_name):
        self.banner = banner
        self.domain_handler = domain_handler
        self.template_name = template_name
        self.logger = get_logger()
        
        # AI Configuration
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.api_url = 'https://api.anthropic.com/v1/messages'
        self.model = 'claude-opus-4-1-20250805'
        self.max_tokens = 4000
        
        # Security categories prioritization
        self.critical_categories = {
            'admin_endpoints', 'authentication_endpoints', 'api_keys_tokens',
            'payment_endpoints', 'security_endpoints', 'oauth_endpoints'
        }
        
        self.high_risk_categories = {
            'api_endpoints', 'user_management', 'webhooks_callbacks',
            'external_apis', 'file_operations', 'command_execution_sinks'
        }
        
        self.logger.debug(f"Initialized AISecurityAnalyzer with template: {template_name}")
        self.logger.debug(f"API key available: {bool(self.api_key)}")

    # Check if AI analysis is available
    def is_available(self) -> bool:
        return bool(self.api_key)

    # Analyze findings for all processed URLs
    def analyze_findings(self, urls: List[str]) -> bool:
        if not self.is_available():
            self.banner.show_warning("AI analysis unavailable - no API key found")
            self.logger.warning("Skipping AI analysis: no ANTHROPIC_API_KEY found")
            return False

        self.logger.info("Starting AI security analysis")
        self.banner.add_status("STARTING AI SECURITY ANALYSIS...")
        
        analyzed_count = 0
        failed_count = 0
        
        for url in urls:
            domain = self.domain_handler.extract_domain(url)
            if not domain:
                continue
                
            self.logger.debug(f"Processing AI analysis for domain: {domain}")
            
            # Load findings for this domain
            findings = self._load_domain_findings(domain)
            if not findings:
                self.logger.debug(f"No findings found for domain: {domain}")
                continue
            
            try:
                # Perform AI analysis
                self.banner.add_status(f"Analyzing {domain} with AI...")
                analysis = self._perform_ai_analysis(domain, findings)
                
                if analysis:
                    # Save AI analysis results
                    self._save_ai_analysis(domain, analysis)
                    
                    # Generate Burp/ZAP configurations
                    self._generate_security_configs(domain, analysis, findings)
                    
                    analyzed_count += 1
                    self.banner.add_status(f"AI analysis completed for {domain}", "success")
                    self.logger.success(f"AI analysis completed for {domain}")
                else:
                    failed_count += 1
                    self.logger.warning(f"AI analysis failed for {domain}")
                    
            except Exception as e:
                failed_count += 1
                self.logger.error(f"AI analysis error for {domain}: {e}")
                self.banner.add_status(f"AI analysis error for {domain}: {e}", "error")
            
            # Rate limiting
            time.sleep(1)
        
        # Log summary
        self.logger.info(f"AI analysis summary:")
        self.logger.info(f"  - Analyzed: {analyzed_count} domains")
        self.logger.info(f"  - Failed: {failed_count} domains")
        
        if analyzed_count > 0:
            self.banner.show_success(f"AI analysis completed for {analyzed_count} domains")
        
        return analyzed_count > 0

    def _load_domain_findings(self, domain: str) -> Optional[Dict]:
        """Load findings for a specific domain"""
        detailed_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_detailed.json"
        
        if not os.path.exists(detailed_file):
            self.logger.debug(f"Detailed findings file not found: {detailed_file}")
            return None
            
        try:
            with open(detailed_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.logger.debug(f"Loaded findings for {domain}: {len(data.get('contents_summary', {}))} categories")
            return data
            
        except Exception as e:
            self.logger.error(f"Error loading findings for {domain}: {e}")
            return None

    def _perform_ai_analysis(self, domain: str, findings: Dict) -> Optional[Dict]:
        """Perform AI analysis of security findings"""
        try:
            # Load HTML content for this domain
            html_content = self._load_html_content(domain)
            
            # Prepare the prompt with HTML content
            prompt = self._build_security_analysis_prompt(domain, findings, html_content)
            
            # Make API request
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.api_key,
                'anthropic-version': '2023-06-01'
            }
            
            payload = {
                'model': self.model,
                'max_tokens': self.max_tokens,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            }
            
            self.logger.debug(f"Sending AI analysis request for {domain} (with HTML content)")
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                analysis_text = result['content'][0]['text']
                
                # Parse the structured response
                analysis = self._parse_ai_response(analysis_text)
                
                self.logger.success(f"AI analysis successful for {domain}")
                return analysis
            else:
                self.logger.error(f"AI API error for {domain}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"AI analysis request failed for {domain}: {e}")
            return None

    # Build security analysis prompt
    def _build_security_analysis_prompt(self, domain: str, findings: Dict) -> str:
        
        # Extract key metrics
        contents_summary = findings.get('contents_summary', {})
        metadata = findings.get('metadata', {})
        total_endpoints = metadata.get('total_endpoints', 0)
        
        # Identify high-risk findings
        high_risk_findings = {}
        for category, endpoints in contents_summary.items():
            if category in self.critical_categories or category in self.high_risk_categories:
                high_risk_findings[category] = endpoints[:10]  # Limit for API
        
        # Build the prompt
        prompt = f"""You are a senior cybersecurity expert and bug bounty hunter analyzing JavaScript security findings for the domain: {domain}

SCAN RESULTS SUMMARY:
- Total endpoints found: {total_endpoints}
- Total categories: {len(contents_summary)}
- Template used: {self.template_name}

HIGH-PRIORITY SECURITY FINDINGS:
{json.dumps(high_risk_findings, indent=2) if high_risk_findings else "None"}

ALL FINDINGS BY CATEGORY:
{json.dumps(contents_summary, indent=2)}

Please provide a comprehensive security analysis in the following structured format:

## CRITICAL SECURITY RISKS
[Identify the most serious vulnerabilities with severity ratings]

## VULNERABILITY TESTING GUIDE
[Specific steps to test each finding for true positives]

## BUG BOUNTY RECOMMENDATIONS
[Actionable advice for bug bounty hunters including:]
- Priority targets for testing
- Exploitation techniques
- Common attack vectors
- Payload recommendations

## BURP/ZAP TESTING CHECKLIST
[Ready-to-use testing checklist with specific requests]

## AUTOMATED SCANNER CONFIGURATION
[Configuration details for Burp/ZAP including:]
- Custom headers to test
- Injection points
- Payload positions
- Scanner settings

Focus on practical, actionable advice. Be specific about the security implications of exposed endpoints, API keys, and authentication mechanisms. Provide ready-to-use attack payloads and scanner configurations."""

        return prompt

    # Parse AI response into structured format
    def _parse_ai_response(self, response_text: str) -> Dict:
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'model_used': self.model,
            'raw_response': response_text,
            'sections': {}
        }
        
        # Split response into sections
        sections = response_text.split('##')
        for section in sections[1:]:  # Skip first empty section
            lines = section.strip().split('\n', 1)
            if len(lines) >= 2:
                title = lines[0].strip()
                content = lines[1].strip()
                analysis['sections'][title.lower().replace(' ', '_')] = content
        
        return analysis

    # Save AI analysis results
    def _save_ai_analysis(self, domain: str, analysis: Dict):
        try:
            output_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_ai_analysis.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
            
            self.logger.success(f"AI analysis saved: {output_file}")
            
            # Also save a readable markdown version
            md_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_ai_analysis.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# AI Security Analysis for {domain}\n\n")
                f.write(f"**Generated:** {analysis['timestamp']}\n")
                f.write(f"**Model:** {analysis['model_used']}\n\n")
                f.write(analysis['raw_response'])
            
            self.logger.success(f"AI analysis markdown saved: {md_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving AI analysis for {domain}: {e}")

    # Generate Burp/ZAP configurations and payload files
    def _generate_security_configs(self, domain: str, analysis: Dict, findings: Dict):
        try:
            # Generate Burp Suite configuration
            burp_config = self._generate_burp_config(domain, findings)
            burp_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_burp_config.json"
            
            with open(burp_file, 'w', encoding='utf-8') as f:
                json.dump(burp_config, f, indent=2)
            
            # Generate ZAP configuration
            zap_config = self._generate_zap_config(domain, findings)
            zap_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_zap_config.json"
            
            with open(zap_file, 'w', encoding='utf-8') as f:
                json.dump(zap_config, f, indent=2)
            
            # Generate payload files
            payloads = self._generate_payloads(findings)
            payload_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_payloads.txt"
            
            with open(payload_file, 'w', encoding='utf-8') as f:
                for category, payload_list in payloads.items():
                    f.write(f"# {category.upper()} PAYLOADS\n")
                    for payload in payload_list:
                        f.write(f"{payload}\n")
                    f.write("\n")
            
            # Generate testing checklist
            checklist = self._generate_testing_checklist(domain, findings, analysis)
            checklist_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_testing_checklist.md"
            
            with open(checklist_file, 'w', encoding='utf-8') as f:
                f.write(checklist)
            
            self.logger.success(f"Security configurations generated for {domain}")
            
        except Exception as e:
            self.logger.error(f"Error generating security configs for {domain}: {e}")

    # Generate Burp Suite configuration
    def _generate_burp_config(self, domain: str, findings: Dict) -> Dict:
        contents_summary = findings.get('contents_summary', {})
        
        # Build target scope
        target_scope = [f"https://{domain}", f"http://{domain}"]
        
        # Build custom headers
        custom_headers = [
            {"name": "X-Forwarded-For", "value": "127.0.0.1"},
            {"name": "X-Real-IP", "value": "127.0.0.1"},
            {"name": "X-Originating-IP", "value": "127.0.0.1"},
            {"name": "X-Remote-IP", "value": "127.0.0.1"},
            {"name": "X-Client-IP", "value": "127.0.0.1"}
        ]
        
        # Build injection points based on findings
        injection_points = []
        for category, endpoints in contents_summary.items():
            for endpoint in endpoints[:5]:  # Limit for practical use
                injection_points.append({
                    "url": f"https://{domain}{endpoint}",
                    "method": "GET",
                    "category": category,
                    "parameters": ["id", "user", "token", "file", "url", "redirect"]
                })
        
        burp_config = {
            "target": {
                "scope": {
                    "include": [{"enabled": True, "url": url} for url in target_scope]
                }
            },
            "scanner": {
                "engine": {
                    "insertion_points": {
                        "url_path_filename": True,
                        "url_path_folders": True,
                        "url_parameters": True,
                        "body_parameters": True,
                        "cookies": True,
                        "headers": True
                    }
                }
            },
            "custom_headers": custom_headers,
            "injection_points": injection_points,
            "generated_by": f"JSauce v1.0 - {datetime.now().isoformat()}"
        }
        
        return burp_config

    # Generate OWASP ZAP configuration
    def _generate_zap_config(self, domain: str, findings: Dict) -> Dict:
        contents_summary = findings.get('contents_summary', {})
        
        # Build context configuration
        zap_config = {
            "context": {
                "name": f"{domain}_security_test",
                "description": f"JSauce generated context for {domain}",
                "includePaths": [f"https://{domain}/.*", f"http://{domain}/.*"],
                "excludePaths": [
                    ".*/logout.*",
                    ".*/signout.*",
                    ".*/delete.*"
                ]
            },
            "spider": {
                "maxDepth": 5,
                "maxChildren": 100,
                "parseComments": True,
                "parseRobotsTxt": True,
                "parseSitemapXml": True
            },
            "activeScan": {
                "policy": "Default Policy",
                "alertThreshold": "Low",
                "attackStrength": "Medium",
                "hostPerScan": 5,
                "threadsPerHost": 2
            },
            "endpoints_to_test": [],
            "generated_by": f"JSauce v1.0 - {datetime.now().isoformat()}"
        }
        
        # Add specific endpoints from findings
        for category, endpoints in contents_summary.items():
            for endpoint in endpoints[:10]:  # Limit for practical use
                zap_config["endpoints_to_test"].append({
                    "url": f"https://{domain}{endpoint}",
                    "category": category,
                    "test_methods": ["GET", "POST", "PUT", "DELETE"]
                })
        
        return zap_config

    # Generate testing payloads based on findings
    def _generate_payloads(self, findings: Dict) -> Dict:
        contents_summary = findings.get('contents_summary', {})
        payloads = {}
        
        # XSS payloads
        if any('xss' in cat.lower() for cat in contents_summary.keys()):
            payloads['xss'] = [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')",
                "<svg onload=alert('XSS')>",
                "'\"><script>alert('XSS')</script>"
            ]
        
        # SQL Injection payloads
        if any('sql' in cat.lower() for cat in contents_summary.keys()):
            payloads['sql_injection'] = [
                "' OR '1'='1",
                "' UNION SELECT NULL--",
                "'; DROP TABLE users--",
                "' OR 1=1#",
                "admin'--"
            ]
        
        # Command injection payloads
        if any('command' in cat.lower() for cat in contents_summary.keys()):
            payloads['command_injection'] = [
                "; ls -la",
                "&& cat /etc/passwd",
                "| whoami",
                "`id`",
                "$(cat /etc/hosts)"
            ]
        
        # Path traversal payloads
        if any('file' in cat.lower() for cat in contents_summary.keys()):
            payloads['path_traversal'] = [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
                "....//....//....//etc/passwd",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
                "..%252f..%252f..%252fetc%252fpasswd"
            ]
        
        # SSRF payloads
        if any('ssrf' in cat.lower() for cat in contents_summary.keys()):
            payloads['ssrf'] = [
                "http://127.0.0.1:80",
                "http://localhost:22",
                "http://169.254.169.254/latest/meta-data/",
                "http://metadata.google.internal/computeMetadata/v1/",
                "file:///etc/passwd"
            ]
        
        return payloads

    # Generate comprehensive testing checklist
    def _generate_testing_checklist(self, domain: str, findings: Dict, analysis: Dict) -> str:
        contents_summary = findings.get('contents_summary', {})
        
        checklist = f"""# Security Testing Checklist for {domain}

Generated by JSauce AI Analysis on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Quick Start
1. Import Burp configuration: `{domain}_{self.template_name}_burp_config.json`
2. Import ZAP configuration: `{domain}_{self.template_name}_zap_config.json`
3. Use payloads from: `{domain}_{self.template_name}_payloads.txt`

## Priority Testing Targets

"""
        
        # Add high-priority findings
        for category, endpoints in contents_summary.items():
            if category in self.critical_categories:
                checklist += f"### {category.upper()} (CRITICAL)\n"
                for endpoint in endpoints[:5]:
                    checklist += f"- [ ] Test `{endpoint}` for authentication bypass\n"
                    checklist += f"- [ ] Check `{endpoint}` for privilege escalation\n"
                    checklist += f"- [ ] Verify access controls on `{endpoint}`\n"
                checklist += "\n"
        
        # Add manual testing steps
        checklist += """## Manual Testing Steps

### 1. Authentication Testing
- [ ] Test for default credentials
- [ ] Check password policy enforcement
- [ ] Test session management
- [ ] Verify logout functionality
- [ ] Test for session fixation

### 2. Authorization Testing
- [ ] Test for horizontal privilege escalation
- [ ] Test for vertical privilege escalation
- [ ] Check direct object references
- [ ] Test API endpoint access controls

### 3. Input Validation Testing
- [ ] Test all input fields for XSS
- [ ] Check for SQL injection vulnerabilities
- [ ] Test file upload functionality
- [ ] Verify input length restrictions

### 4. Business Logic Testing
- [ ] Test payment flows (if applicable)
- [ ] Check workflow bypasses
- [ ] Test rate limiting
- [ ] Verify transaction integrity

### 5. API Security Testing
- [ ] Test API without authentication
- [ ] Check for CORS misconfigurations
- [ ] Test API versioning issues
- [ ] Verify input validation on API endpoints

## Automated Scanner Configuration

### Burp Suite Setup
1. Load target scope configuration
2. Enable all passive checks
3. Configure custom insertion points
4. Set scanner to thorough mode

### OWASP ZAP Setup
1. Import context configuration
2. Configure spider settings
3. Enable all scan policies
4. Set appropriate scan intensity

## Reporting Template

### Vulnerability Report Structure
1. **Title**: Clear, descriptive vulnerability name
2. **Severity**: Critical/High/Medium/Low
3. **Description**: Technical details of the vulnerability
4. **Impact**: Business impact and risk assessment
5. **Reproduction Steps**: Step-by-step exploitation guide
6. **Proof of Concept**: Screenshots or code samples
7. **Remediation**: Specific fix recommendations

### Evidence Collection
- [ ] Screenshot of successful exploit
- [ ] HTTP request/response showing vulnerability
- [ ] Video demonstration (for complex issues)
- [ ] Log files showing impact

## Post-Exploitation
- [ ] Document all accessed endpoints
- [ ] Check for sensitive data exposure
- [ ] Test for lateral movement possibilities
- [ ] Verify impact scope

---
*Generated by JSauce AI Security Analyzer*
"""
        
        return checklist

# Integration helper for main application
def integrate_ai_analysis(app_instance):
    """Integrate AI analysis into the main JSauce application"""
    
    # Add AI analyzer to the app instance
    app_instance.ai_analyzer = AISecurityAnalyzer(
        app_instance.banner,
        app_instance.domain_handler,
        app_instance.template_name
    )
    
    # Add AI analysis to the post-processing workflow
    original_post_process = app_instance._post_process
    
    def enhanced_post_process(urls):
        # Run original post-processing
        original_post_process(urls)
        
        # Add AI analysis if available
        if app_instance.ai_analyzer.is_available():
            app_instance.ai_analyzer.analyze_findings(urls)
        else:
            app_instance.banner.show_warning("AI analysis unavailable - set ANTHROPIC_API_KEY to enable")
    
    app_instance._post_process = enhanced_post_process