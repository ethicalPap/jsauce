import json
import os
from datetime import datetime
from typing import Dict, List, Any
from src import config
from src.utils.Logger import get_logger

class HTMLReportConverter:
    """Convert JSauce JSON output to formatted HTML reports"""
    
    def __init__(self, banner, domain_handler, template_name):
        self.banner = banner
        self.domain_handler = domain_handler
        self.template_name = template_name
        self.logger = get_logger()
        
        # Priority categories for styling
        self.critical_categories = {
            'admin_endpoints', 'authentication_endpoints', 'api_keys_tokens',
            'payment_endpoints', 'oauth_endpoints', 'security_endpoints'
        }
        
        self.high_categories = {
            'api_endpoints', 'user_management', 'webhooks_callbacks',
            'file_operations', 'external_apis', 'command_execution_sinks'
        }
        
        self.sensitive_categories = {
            'api_keys_tokens', 'authentication_endpoints', 'oauth_endpoints',
            'csrf_sinks', 'xss_sinks', 'sql_injection_sinks'
        }
        
        self.logger.debug(f"Initialized HTMLReportConverter for template: {template_name}")

    def generate_html_reports(self, urls: List[str]) -> bool:
        """Generate HTML reports for all processed URLs"""
        self.logger.info("Starting HTML report generation")
        self.banner.add_status("GENERATING HTML REPORTS...")
        
        reports_generated = 0
        reports_failed = 0
        
        for url in urls:
            domain = self.domain_handler.extract_domain(url)
            if not domain:
                continue
                
            try:
                success = self._generate_domain_html_report(domain)
                if success:
                    reports_generated += 1
                    self.banner.add_status(f"HTML report generated for {domain}", "success")
                else:
                    reports_failed += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to generate HTML report for {domain}: {e}")
                reports_failed += 1
        
        self.logger.info(f"HTML report generation complete: {reports_generated} generated, {reports_failed} failed")
        return reports_generated > 0
    
    def _generate_domain_html_report(self, domain: str) -> bool:
        """Generate HTML report for a specific domain"""
        # Load the detailed JSON data
        json_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_detailed.json"
        stats_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_stats.json"
        
        if not os.path.exists(json_file):
            self.logger.debug(f"No detailed JSON file found for {domain}")
            return False
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                detailed_data = json.load(f)
            
            # Try to load stats data
            stats_data = {}
            if os.path.exists(stats_file):
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats_data = json.load(f)
            
            # Generate the HTML report
            html_content = self._create_html_report(domain, detailed_data, stats_data)
            
            # Save the HTML file
            html_file = f"{config.OUTPUT_DIR}/{domain}/{domain}_{self.template_name}_report.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            file_size = os.path.getsize(html_file)
            self.logger.success(f"Generated HTML report: {html_file} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating HTML report for {domain}: {e}")
            return False
    
    def _create_html_report(self, domain: str, detailed_data: Dict, stats_data: Dict) -> str:
        """Create the complete HTML report"""
        
        # Extract metadata
        metadata = detailed_data.get('metadata', {})
        contents_summary = detailed_data.get('contents_summary', {})
        contents_by_source = detailed_data.get('contents_by_source', {})
        
        # Calculate statistics
        total_endpoints = metadata.get('total_endpoints', 0)
        total_js_files = metadata.get('total_js_files', 0)
        total_sources = metadata.get('total_sources', 0)
        extraction_date = metadata.get('extraction_date', datetime.now().isoformat())
        
        # Build the HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSauce Security Analysis Report - {domain}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_header(domain, total_endpoints, total_js_files, total_sources, extraction_date)}
        
        {self._generate_executive_summary(contents_summary, stats_data)}
        
        {self._generate_security_highlights(contents_summary)}
        
        {self._generate_category_breakdown(contents_summary)}
        
        {self._generate_detailed_findings(contents_by_source)}
        
        {self._generate_source_analysis(contents_by_source)}
        
        {self._generate_recommendations(contents_summary)}
        
        {self._generate_footer()}
    </div>
    
    <script>
        {self._get_javascript()}
    </script>
</body>
</html>"""
        
        return html_content
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for the HTML report"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .section {
            margin: 40px 0;
            padding: 30px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .section h2 {
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .section h3 {
            color: #555;
            margin: 20px 0 10px 0;
            font-size: 1.3em;
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        
        .alert-critical {
            background: #ffeaea;
            border-left: 5px solid #dc3545;
            color: #721c24;
        }
        
        .alert-high {
            background: #fff3cd;
            border-left: 5px solid #fd7e14;
            color: #856404;
        }
        
        .alert-medium {
            background: #d1ecf1;
            border-left: 5px solid #17a2b8;
            color: #0c5460;
        }
        
        .alert-info {
            background: #d4edda;
            border-left: 5px solid #28a745;
            color: #155724;
        }
        
        .category-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .category-card {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #6c757d;
        }
        
        .category-card.critical {
            border-left-color: #dc3545;
        }
        
        .category-card.high {
            border-left-color: #fd7e14;
        }
        
        .category-card.medium {
            border-left-color: #ffc107;
        }
        
        .category-title {
            font-weight: bold;
            margin-bottom: 10px;
            text-transform: capitalize;
        }
        
        .category-count {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }
        
        .endpoint-list {
            max-height: 200px;
            overflow-y: auto;
            background: white;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        
        .endpoint-item {
            padding: 5px 10px;
            margin: 2px 0;
            background: #e9ecef;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            word-break: break-all;
        }
        
        .endpoint-item.sensitive {
            background: #f8d7da;
            border-left: 3px solid #dc3545;
        }
        
        .source-section {
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .source-url {
            font-family: 'Courier New', monospace;
            background: #e9ecef;
            padding: 10px;
            border-radius: 5px;
            word-break: break-all;
            margin-bottom: 15px;
        }
        
        .js-file {
            margin: 15px 0;
            padding: 15px;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #28a745;
        }
        
        .js-file-url {
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #28a745;
            margin-bottom: 10px;
            word-break: break-all;
        }
        
        .collapsible {
            cursor: pointer;
            padding: 10px;
            background: #e9ecef;
            border-radius: 5px;
            margin: 10px 0;
            user-select: none;
        }
        
        .collapsible:hover {
            background: #dee2e6;
        }
        
        .collapsible::before {
            content: "▶ ";
            display: inline-block;
            transition: transform 0.3s;
        }
        
        .collapsible.active::before {
            transform: rotate(90deg);
        }
        
        .collapsible-content {
            display: none;
            padding: 15px 0;
        }
        
        .collapsible-content.active {
            display: block;
        }
        
        .recommendation {
            background: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        
        .recommendation h4 {
            color: #155724;
            margin-bottom: 10px;
        }
        
        .recommendation p {
            color: #155724;
            margin: 5px 0;
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            color: #666;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            margin: 2px;
        }
        
        .badge-critical {
            background: #dc3545;
            color: white;
        }
        
        .badge-high {
            background: #fd7e14;
            color: white;
        }
        
        .badge-medium {
            background: #ffc107;
            color: #212529;
        }
        
        .badge-info {
            background: #17a2b8;
            color: white;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .category-grid {
                grid-template-columns: 1fr;
            }
        }
        """
    
    def _generate_header(self, domain: str, total_endpoints: int, total_js_files: int, total_sources: int, extraction_date: str) -> str:
        """Generate the report header"""
        formatted_date = datetime.fromisoformat(extraction_date.replace('Z', '+00:00')).strftime('%B %d, %Y at %I:%M %p')
        
        return f"""
        <div class="header">
            <h1>🔍 JSauce Security Analysis</h1>
            <div class="subtitle">JavaScript Endpoint Discovery & Security Assessment</div>
            <div class="subtitle">Domain: <strong>{domain}</strong></div>
            <div class="subtitle">Generated: {formatted_date}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_endpoints}</div>
                <div class="stat-label">Total Endpoints</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_js_files}</div>
                <div class="stat-label">JS Files Analyzed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_sources}</div>
                <div class="stat-label">Source Pages</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{self.template_name.title()}</div>
                <div class="stat-label">Template Used</div>
            </div>
        </div>
        """
    
    def _generate_executive_summary(self, contents_summary: Dict, stats_data: Dict) -> str:
        """Generate executive summary section"""
        total_categories = len(contents_summary)
        total_endpoints = sum(len(endpoints) for endpoints in contents_summary.values())
        
        # Count by priority
        critical_count = sum(len(endpoints) for cat, endpoints in contents_summary.items() if cat in self.critical_categories)
        high_count = sum(len(endpoints) for cat, endpoints in contents_summary.items() if cat in self.high_categories)
        
        # Security assessment
        security_level = "LOW"
        alert_class = "alert-info"
        
        if critical_count > 5:
            security_level = "CRITICAL"
            alert_class = "alert-critical"
        elif critical_count > 0 or high_count > 10:
            security_level = "HIGH"
            alert_class = "alert-high"
        elif high_count > 0:
            security_level = "MEDIUM"
            alert_class = "alert-medium"
        
        return f"""
        <div class="section">
            <h2>📊 Executive Summary</h2>
            
            <div class="alert {alert_class}">
                <strong>Security Risk Level: {security_level}</strong><br>
                Analysis identified {total_endpoints} endpoints across {total_categories} categories. 
                Found {critical_count} critical security endpoints and {high_count} high-priority targets.
            </div>
            
            <h3>Key Findings:</h3>
            <ul>
                <li><strong>{total_endpoints}</strong> total endpoints discovered across <strong>{total_categories}</strong> categories</li>
                <li><strong>{critical_count}</strong> endpoints in critical security categories (admin, auth, payment)</li>
                <li><strong>{high_count}</strong> endpoints in high-priority categories (API, user management)</li>
                <li>Template focus: <strong>{self.template_name.replace('_', ' ').title()}</strong></li>
            </ul>
        </div>
        """
    
    def _generate_security_highlights(self, contents_summary: Dict) -> str:
        """Generate security highlights section"""
        highlights = []
        
        # Check for critical security categories
        for category, endpoints in contents_summary.items():
            if category in self.critical_categories and endpoints:
                severity = "CRITICAL" if len(endpoints) > 3 else "HIGH"
                badge_class = "badge-critical" if severity == "CRITICAL" else "badge-high"
                
                highlights.append({
                    'category': category.replace('_', ' ').title(),
                    'count': len(endpoints),
                    'severity': severity,
                    'badge_class': badge_class,
                    'examples': endpoints[:3]
                })
        
        if not highlights:
            return f"""
            <div class="section">
                <h2>🔒 Security Highlights</h2>
                <div class="alert alert-info">
                    <strong>No critical security endpoints detected.</strong><br>
                    This is positive - no admin panels, authentication bypasses, or payment endpoints were found in the JavaScript analysis.
                </div>
            </div>
            """
        
        highlights_html = """
        <div class="section">
            <h2>🔒 Security Highlights</h2>
            <div class="alert alert-critical">
                <strong>⚠️ Critical Security Findings Detected</strong><br>
                The following high-risk endpoint categories were discovered and should be reviewed immediately.
            </div>
        """
        
        for highlight in highlights:
            highlights_html += f"""
            <div class="alert alert-critical">
                <h4>
                    <span class="badge {highlight['badge_class']}">{highlight['severity']}</span>
                    {highlight['category']} ({highlight['count']} endpoints)
                </h4>
                <p><strong>Examples:</strong></p>
                <ul>
            """
            
            for example in highlight['examples']:
                highlights_html += f"<li><code>{example}</code></li>"
            
            highlights_html += "</ul></div>"
        
        highlights_html += "</div>"
        return highlights_html
    
    def _generate_category_breakdown(self, contents_summary: Dict) -> str:
        """Generate category breakdown section"""
        # Sort categories by priority and count
        sorted_categories = sorted(
            contents_summary.items(),
            key=lambda x: (
                0 if x[0] in self.critical_categories else 
                1 if x[0] in self.high_categories else 2,
                -len(x[1])
            )
        )
        
        category_html = """
        <div class="section">
            <h2>📂 Category Breakdown</h2>
            <div class="category-grid">
        """
        
        for category, endpoints in sorted_categories:
            if not endpoints:
                continue
                
            # Determine priority class
            priority_class = ""
            if category in self.critical_categories:
                priority_class = "critical"
            elif category in self.high_categories:
                priority_class = "high"
            else:
                priority_class = "medium"
            
            category_display = category.replace('_', ' ').title()
            
            category_html += f"""
            <div class="category-card {priority_class}">
                <div class="category-title">{category_display}</div>
                <div class="category-count">{len(endpoints)} endpoints</div>
                
                <div class="collapsible" onclick="toggleCollapsible(this)">
                    View Endpoints ({len(endpoints)})
                </div>
                <div class="collapsible-content">
                    <div class="endpoint-list">
            """
            
            for endpoint in endpoints[:20]:  # Limit display for performance
                endpoint_class = "sensitive" if category in self.sensitive_categories else ""
                category_html += f'<div class="endpoint-item {endpoint_class}">{endpoint}</div>'
            
            if len(endpoints) > 20:
                category_html += f'<div class="endpoint-item">... and {len(endpoints) - 20} more</div>'
            
            category_html += """
                    </div>
                </div>
            </div>
            """
        
        category_html += """
            </div>
        </div>
        """
        
        return category_html
    
    def _generate_detailed_findings(self, contents_by_source: Dict) -> str:
        """Generate detailed findings section"""
        findings_html = """
        <div class="section">
            <h2>🔍 Detailed Findings by Source</h2>
        """
        
        for source_url, source_data in contents_by_source.items():
            js_files = source_data.get('js_files', {})
            
            findings_html += f"""
            <div class="source-section">
                <h3>Source Page</h3>
                <div class="source-url">{source_url}</div>
                
                <div class="collapsible" onclick="toggleCollapsible(this)">
                    JavaScript Files ({len(js_files)})
                </div>
                <div class="collapsible-content">
            """
            
            for js_url, js_data in js_files.items():
                categories = js_data.get('categories', {})
                total_endpoints = sum(len(endpoints) for endpoints in categories.values())
                
                findings_html += f"""
                <div class="js-file">
                    <div class="js-file-url">{js_url}</div>
                    <p><strong>{total_endpoints}</strong> endpoints found across <strong>{len(categories)}</strong> categories</p>
                    
                    <div class="collapsible" onclick="toggleCollapsible(this)">
                        View Categories
                    </div>
                    <div class="collapsible-content">
                """
                
                for category, endpoints in categories.items():
                    if endpoints:
                        category_display = category.replace('_', ' ').title()
                        findings_html += f"""
                        <h4>{category_display} ({len(endpoints)} endpoints)</h4>
                        <div class="endpoint-list">
                        """
                        
                        for endpoint in endpoints[:10]:  # Limit for performance
                            endpoint_class = "sensitive" if category in self.sensitive_categories else ""
                            findings_html += f'<div class="endpoint-item {endpoint_class}">{endpoint}</div>'
                        
                        if len(endpoints) > 10:
                            findings_html += f'<div class="endpoint-item">... and {len(endpoints) - 10} more</div>'
                        
                        findings_html += "</div>"
                
                findings_html += """
                    </div>
                </div>
                """
            
            findings_html += """
                </div>
            </div>
            """
        
        findings_html += "</div>"
        return findings_html
    
    def _generate_source_analysis(self, contents_by_source: Dict) -> str:
        """Generate source analysis section"""
        analysis_html = """
        <div class="section">
            <h2>📈 Source Analysis</h2>
        """
        
        # Calculate source statistics
        source_stats = []
        for source_url, source_data in contents_by_source.items():
            js_files = source_data.get('js_files', {})
            total_endpoints = 0
            categories_found = set()
            
            for js_data in js_files.values():
                categories = js_data.get('categories', {})
                for category, endpoints in categories.items():
                    total_endpoints += len(endpoints)
                    categories_found.add(category)
            
            source_stats.append({
                'url': source_url,
                'js_files': len(js_files),
                'endpoints': total_endpoints,
                'categories': len(categories_found)
            })
        
        # Sort by endpoints found
        source_stats.sort(key=lambda x: x['endpoints'], reverse=True)
        
        analysis_html += """
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                    <th style="padding: 12px; text-align: left;">Source URL</th>
                    <th style="padding: 12px; text-align: center;">JS Files</th>
                    <th style="padding: 12px; text-align: center;">Endpoints</th>
                    <th style="padding: 12px; text-align: center;">Categories</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for stat in source_stats:
            analysis_html += f"""
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 12px; word-break: break-all; font-family: monospace;">{stat['url']}</td>
                <td style="padding: 12px; text-align: center;">{stat['js_files']}</td>
                <td style="padding: 12px; text-align: center; font-weight: bold; color: #667eea;">{stat['endpoints']}</td>
                <td style="padding: 12px; text-align: center;">{stat['categories']}</td>
            </tr>
            """
        
        analysis_html += """
            </tbody>
        </table>
        </div>
        """
        
        return analysis_html
    
    def _generate_recommendations(self, contents_summary: Dict) -> str:
        """Generate security recommendations"""
        recommendations = []
        
        # Check for specific security issues
        if any(cat in contents_summary for cat in ['admin_endpoints', 'authentication_endpoints']):
            recommendations.append({
                'title': 'Administrative Interface Security',
                'description': 'Administrative endpoints were discovered. Ensure these are properly protected with authentication, authorization, and IP restrictions.',
                'priority': 'HIGH'
            })
        
        if 'api_keys_tokens' in contents_summary:
            recommendations.append({
                'title': 'API Key Exposure',
                'description': 'API keys or tokens were found in JavaScript. Move sensitive credentials to server-side configuration and use environment variables.',
                'priority': 'CRITICAL'
            })
        
        if any(cat in contents_summary for cat in ['api_endpoints', 'graphql_endpoints']):
            recommendations.append({
                'title': 'API Security',
                'description': 'API endpoints discovered. Implement proper authentication, rate limiting, input validation, and consider using API gateways.',
                'priority': 'HIGH'
            })
        
        if 'payment_endpoints' in contents_summary:
            recommendations.append({
                'title': 'Payment Security',
                'description': 'Payment-related endpoints found. Ensure PCI DSS compliance, use HTTPS, implement strong authentication, and audit regularly.',
                'priority': 'CRITICAL'
            })
        
        # General recommendations
        recommendations.extend([
            {
                'title': 'JavaScript Minification',
                'description': 'Consider minifying and obfuscating JavaScript to reduce information disclosure about internal endpoints and structure.',
                'priority': 'MEDIUM'
            },
            {
                'title': 'Endpoint Auditing',
                'description': 'Regularly audit all discovered endpoints for proper authentication, authorization, and input validation.',
                'priority': 'HIGH'
            },
            {
                'title': 'Security Headers',
                'description': 'Implement security headers like CSP, HSTS, and X-Frame-Options to prevent various client-side attacks.',
                'priority': 'MEDIUM'
            }
        ])
        
        rec_html = """
        <div class="section">
            <h2>💡 Security Recommendations</h2>
        """
        
        for rec in recommendations:
            rec_html += f"""
            <div class="recommendation">
                <h4>
                    <span class="badge badge-{rec['priority'].lower()}">{rec['priority']}</span>
                    {rec['title']}
                </h4>
                <p>{rec['description']}</p>
            </div>
            """
        
        rec_html += "</div>"
        return rec_html
    
    def _generate_footer(self) -> str:
        """Generate report footer"""
        return f"""
        <div class="footer">
            <p><strong>JSauce Security Analysis Report</strong></p>
            <p>Generated by JSauce - JavaScript Content Mapping Tool</p>
            <p>Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><em>This report is for security assessment purposes only. Always verify findings manually before taking action.</em></p>
        </div>
        """
    
    def _get_javascript(self) -> str:
        """Get JavaScript for interactive features"""
        return """
        function toggleCollapsible(element) {
            element.classList.toggle('active');
            var content = element.nextElementSibling;
            if (content.classList.contains('collapsible-content')) {
                content.classList.toggle('active');
            }
        }
        
        // Auto-expand first few categories for better UX
        document.addEventListener('DOMContentLoaded', function() {
            const collapsibles = document.querySelectorAll('.collapsible');
            for (let i = 0; i < Math.min(3, collapsibles.length); i++) {
                toggleCollapsible(collapsibles[i]);
            }
        });
        """