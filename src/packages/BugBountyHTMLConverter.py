import json
import os
from datetime import datetime
from typing import Dict, List, Any
from src import config
from src.utils.Logger import get_logger
import glob

class BugBountyHTMLConverter:
    """HTML converter specifically for bug bounty analysis files"""
    
    def __init__(self, banner, domain_handler, template_name):
        self.banner = banner
        self.domain_handler = domain_handler
        self.template_name = template_name
        self.logger = get_logger()
        
        self.logger.debug(f"Initialized BugBountyHTMLConverter for template: {template_name}")

    def generate_bug_bounty_html_reports(self, urls: List[str]) -> bool:
        """Generate HTML reports for all bug bounty analysis JSON files"""
        self.logger.info("Starting Bug Bounty HTML report generation")
        self.banner.add_status("GENERATING BUG BOUNTY HTML REPORTS...")
        
        reports_generated = 0
        reports_failed = 0
        
        for url in urls:
            domain = self.domain_handler.extract_domain(url)
            if not domain:
                continue
                
            try:
                # Look for all JSON files in the domain directory
                domain_dir = f"{config.OUTPUT_DIR}/{domain}"
                if not os.path.exists(domain_dir):
                    self.logger.debug(f"Domain directory doesn't exist: {domain_dir}")
                    continue
                
                # Find all JSON files for this domain
                json_files = glob.glob(f"{domain_dir}/*.json")
                self.logger.debug(f"Found {len(json_files)} JSON files for {domain}")
                
                for json_file in json_files:
                    filename = os.path.basename(json_file)
                    
                    # Generate HTML for different types of JSON files
                    if "bug_bounty_analysis" in filename:
                        success = self._generate_bug_bounty_analysis_html(domain, json_file)
                    elif "detailed" in filename:
                        success = self._generate_detailed_findings_html(domain, json_file)
                    elif "stats" in filename:
                        success = self._generate_stats_html(domain, json_file)
                    elif "for_db" in filename:
                        success = self._generate_database_html(domain, json_file)
                    else:
                        success = self._generate_generic_json_html(domain, json_file)
                    
                    if success:
                        reports_generated += 1
                        self.banner.add_status(f"HTML report generated: {filename}", "success")
                    else:
                        reports_failed += 1
                        
            except Exception as e:
                self.logger.error(f"Failed to generate HTML reports for {domain}: {e}")
                reports_failed += 1
        
        self.logger.info(f"Bug Bounty HTML generation complete: {reports_generated} generated, {reports_failed} failed")
        return reports_generated > 0
    
    def _generate_bug_bounty_analysis_html(self, domain: str, json_file: str) -> bool:
        """Generate HTML for bug bounty analysis JSON"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both single analysis and list of analyses
            if isinstance(data, list) and len(data) > 0:
                data = data[0]  # Take the first analysis
            
            timestamp = data.get('timestamp', datetime.now().isoformat())
            model_used = data.get('model_used', 'Unknown')
            sections = data.get('sections', {})
            raw_response = data.get('raw_response', '')
            
            html_content = self._create_bug_bounty_html_report(domain, data, timestamp, model_used, sections, raw_response)
            
            # Save HTML file
            html_file = json_file.replace('.json', '_report.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            file_size = os.path.getsize(html_file)
            self.logger.success(f"Generated Bug Bounty HTML report: {html_file} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating bug bounty HTML for {domain}: {e}")
            return False
    
    def _create_bug_bounty_html_report(self, domain: str, data: Dict, timestamp: str, model_used: str, sections: Dict, raw_response: str) -> str:
        """Create comprehensive bug bounty HTML report"""
        
        formatted_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%B %d, %Y at %I:%M %p')
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎯 Bug Bounty Analysis Report - {domain}</title>
    <style>
        {self._get_bug_bounty_css()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_bug_bounty_header(domain, formatted_date, model_used)}
        
        {self._generate_executive_summary_section(sections)}
        
        {self._generate_priority_targets_section(sections)}
        
        {self._generate_verification_section(sections)}
        
        {self._generate_exploitation_section(sections)}
        
        {self._generate_testing_methodology_section(sections)}
        
        {self._generate_reporting_section(sections)}
        
        {self._generate_quick_wins_section(sections)}
        
        {self._generate_follow_up_section(sections)}
        
        {self._generate_raw_analysis_section(raw_response)}
        
        {self._generate_bug_bounty_footer()}
    </div>
    
    <script>
        {self._get_bug_bounty_javascript()}
    </script>
</body>
</html>"""
        
        return html_content
    
    def _get_bug_bounty_css(self) -> str:
        """CSS for bug bounty reports"""
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0;
            background: white;
            box-shadow: 0 0 30px rgba(0,0,0,0.3);
            border-radius: 15px;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }
        
        .header::before {
            content: '🎯';
            position: absolute;
            top: 20px;
            left: 30px;
            font-size: 2em;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header .subtitle {
            font-size: 1.3em;
            opacity: 0.95;
            margin-bottom: 5px;
        }
        
        .header .meta {
            font-size: 1em;
            opacity: 0.8;
            margin-top: 10px;
        }
        
        .section {
            margin: 0;
            padding: 40px;
            border-bottom: 1px solid #eee;
        }
        
        .section:last-child {
            border-bottom: none;
        }
        
        .section h2 {
            color: #333;
            border-left: 5px solid #ff416c;
            padding-left: 15px;
            margin-bottom: 25px;
            font-size: 1.8em;
            display: flex;
            align-items: center;
        }
        
        .section h2::before {
            margin-right: 10px;
            font-size: 1.2em;
        }
        
        .priority-targets h2::before { content: '🎯'; }
        .verification h2::before { content: '🔍'; }
        .exploitation h2::before { content: '💰'; }
        .methodology h2::before { content: '🛠️'; }
        .reporting h2::before { content: '📝'; }
        .quick-wins h2::before { content: '⚡'; }
        .follow-up h2::before { content: '🔄'; }
        .raw-analysis h2::before { content: '🤖'; }
        
        .section h3 {
            color: #555;
            margin: 25px 0 15px 0;
            font-size: 1.4em;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 8px;
        }
        
        .alert {
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 5px solid;
        }
        
        .alert-critical {
            background: #fff5f5;
            border-left-color: #e53e3e;
            color: #742a2a;
        }
        
        .alert-high {
            background: #fffaf0;
            border-left-color: #dd6b20;
            color: #7c2d12;
        }
        
        .alert-medium {
            background: #f0fff4;
            border-left-color: #38a169;
            color: #22543d;
        }
        
        .alert-info {
            background: #ebf8ff;
            border-left-color: #3182ce;
            color: #2a4365;
        }
        
        .priority-card {
            background: #fafafa;
            border-left: 4px solid #ff416c;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            transition: transform 0.2s;
        }
        
        .priority-card:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .priority-card h4 {
            color: #ff416c;
            margin-bottom: 10px;
            font-size: 1.2em;
        }
        
        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            margin: 3px;
            text-transform: uppercase;
        }
        
        .badge-critical {
            background: #e53e3e;
            color: white;
        }
        
        .badge-high {
            background: #dd6b20;
            color: white;
        }
        
        .badge-medium {
            background: #38a169;
            color: white;
        }
        
        .code-block {
            background: #1a202c;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
            border-left: 4px solid #ff416c;
        }
        
        .code-block pre {
            margin: 0;
            white-space: pre-wrap;
        }
        
        .step-list {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
        }
        
        .step-list ol {
            margin-left: 20px;
        }
        
        .step-list li {
            margin: 10px 0;
            padding: 8px;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #ff416c;
        }
        
        .collapsible {
            cursor: pointer;
            padding: 15px;
            background: #f1f3f4;
            border-radius: 8px;
            margin: 10px 0;
            user-select: none;
            transition: background 0.3s;
        }
        
        .collapsible:hover {
            background: #e8eaed;
        }
        
        .collapsible::before {
            content: "▶ ";
            display: inline-block;
            transition: transform 0.3s;
            color: #ff416c;
            font-weight: bold;
        }
        
        .collapsible.active::before {
            transform: rotate(90deg);
        }
        
        .collapsible-content {
            display: none;
            padding: 20px 0;
            animation: slideDown 0.3s ease-out;
        }
        
        .collapsible-content.active {
            display: block;
        }
        
        @keyframes slideDown {
            from { opacity: 0; max-height: 0; }
            to { opacity: 1; max-height: 500px; }
        }
        
        .footer {
            text-align: center;
            padding: 30px;
            background: #f8f9fa;
            color: #666;
            border-top: 3px solid #ff416c;
        }
        
        .raw-content {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #666;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            max-height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }
            
            .header {
                padding: 30px 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .section {
                padding: 30px 20px;
            }
        }
        """
    
    def _generate_bug_bounty_header(self, domain: str, formatted_date: str, model_used: str) -> str:
        """Generate header for bug bounty report"""
        return f"""
        <div class="header">
            <h1>Bug Bounty Analysis Report</h1>
            <div class="subtitle">AI-Powered Security Assessment</div>
            <div class="subtitle">Target: <strong>{domain}</strong></div>
            <div class="meta">Generated: {formatted_date}</div>
            <div class="meta">AI Model: {model_used}</div>
        </div>
        """
    
    def _generate_executive_summary_section(self, sections: Dict) -> str:
        """Generate executive summary section"""
        summary_content = sections.get('executive_summary', sections.get('highest_priority_targets', 'Executive summary not available'))
        
        return f"""
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="alert alert-info">
                <strong>🎯 Bug Bounty Assessment Overview</strong><br>
                This report provides AI-powered analysis of JavaScript findings with focus on bug bounty opportunities.
            </div>
            <div class="raw-content">
{summary_content}
            </div>
        </div>
        """
    
    def _generate_priority_targets_section(self, sections: Dict) -> str:
        """Generate priority targets section"""
        targets_content = sections.get('highest_priority_targets', 'Priority targets analysis not available')
        
        return f"""
        <div class="section priority-targets">
            <h2>🎯 Highest Priority Targets</h2>
            <div class="alert alert-critical">
                <strong>⚠️ Critical Security Findings</strong><br>
                These targets have the highest potential for bug bounty payouts and should be investigated immediately.
            </div>
            
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View Detailed Priority Analysis
            </div>
            <div class="collapsible-content">
                <div class="raw-content">
{targets_content}
                </div>
            </div>
        </div>
        """
    
    def _generate_verification_section(self, sections: Dict) -> str:
        """Generate verification section"""
        verification_content = sections.get('true_positive_verification', 'Verification instructions not available')
        
        return f"""
        <div class="section verification">
            <h2>🔍 True Positive Verification</h2>
            <div class="alert alert-high">
                <strong>Verification Required</strong><br>
                Follow these steps to verify if findings are exploitable vulnerabilities.
            </div>
            
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View Verification Instructions
            </div>
            <div class="collapsible-content">
                <div class="raw-content">
{verification_content}
                </div>
            </div>
        </div>
        """
    
    def _generate_exploitation_section(self, sections: Dict) -> str:
        """Generate exploitation section"""
        exploitation_content = sections.get('exploitation_techniques', 'Exploitation techniques not available')
        
        return f"""
        <div class="section exploitation">
            <h2>💰 Exploitation Techniques</h2>
            <div class="alert alert-critical">
                <strong>⚡ High-Value Attack Vectors</strong><br>
                Detailed exploitation methods for maximum impact and bug bounty rewards.
            </div>
            
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View Exploitation Techniques
            </div>
            <div class="collapsible-content">
                <div class="raw-content">
{exploitation_content}
                </div>
            </div>
        </div>
        """
    
    def _generate_testing_methodology_section(self, sections: Dict) -> str:
        """Generate testing methodology section"""
        methodology_content = sections.get('testing_methodology', 'Testing methodology not available')
        
        return f"""
        <div class="section methodology">
            <h2>🛠️ Testing Methodology</h2>
            <div class="alert alert-medium">
                <strong>Practical Testing Approach</strong><br>
                Tools, configurations, and methodologies for systematic security testing.
            </div>
            
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View Testing Methodology
            </div>
            <div class="collapsible-content">
                <div class="raw-content">
{methodology_content}
                </div>
            </div>
        </div>
        """
    
    def _generate_reporting_section(self, sections: Dict) -> str:
        """Generate reporting section"""
        reporting_content = sections.get('bug_bounty_reporting', 'Reporting guidelines not available')
        
        return f"""
        <div class="section reporting">
            <h2>📝 Bug Bounty Reporting</h2>
            <div class="alert alert-info">
                <strong>Professional Report Writing</strong><br>
                Guidelines for writing high-quality bug bounty reports that get accepted.
            </div>
            
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View Reporting Guidelines
            </div>
            <div class="collapsible-content">
                <div class="raw-content">
{reporting_content}
                </div>
            </div>
        </div>
        """
    
    def _generate_quick_wins_section(self, sections: Dict) -> str:
        """Generate quick wins section"""
        quick_wins_content = sections.get('quick_wins', 'Quick wins not available')
        
        return f"""
        <div class="section quick-wins">
            <h2>⚡ Quick Wins</h2>
            <div class="alert alert-medium">
                <strong>Low-Hanging Fruit</strong><br>
                Easy-to-test vulnerabilities that are often overlooked but can yield quick rewards.
            </div>
            
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View Quick Win Opportunities
            </div>
            <div class="collapsible-content">
                <div class="raw-content">
{quick_wins_content}
                </div>
            </div>
        </div>
        """
    
    def _generate_follow_up_section(self, sections: Dict) -> str:
        """Generate follow-up section"""
        follow_up_content = sections.get('follow_up_testing', 'Follow-up testing not available')
        
        return f"""
        <div class="section follow-up">
            <h2>🔄 Follow-Up Testing</h2>
            <div class="alert alert-info">
                <strong>Extended Testing Opportunities</strong><br>
                Additional attack surface and escalation paths to explore after initial findings.
            </div>
            
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View Follow-Up Testing Strategy
            </div>
            <div class="collapsible-content">
                <div class="raw-content">
{follow_up_content}
                </div>
            </div>
        </div>
        """
    
    def _generate_raw_analysis_section(self, raw_response: str) -> str:
        """Generate raw analysis section"""
        return f"""
        <div class="section raw-analysis">
            <h2>🤖 Complete AI Analysis</h2>
            <div class="alert alert-info">
                <strong>Full AI Response</strong><br>
                Complete unprocessed analysis from the AI security expert.
            </div>
            
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View Complete Analysis
            </div>
            <div class="collapsible-content">
                <div class="raw-content">
{raw_response}
                </div>
            </div>
        </div>
        """
    
    def _generate_bug_bounty_footer(self) -> str:
        """Generate footer for bug bounty report"""
        return f"""
        <div class="footer">
            <p><strong>🎯 Bug Bounty Analysis Report</strong></p>
            <p>Generated by JSauce AI Security Analyzer</p>
            <p>Report generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><em>⚠️ This analysis is for authorized security testing only. Always verify findings manually and ensure proper authorization before testing.</em></p>
            <p>🔒 <strong>Responsible Disclosure:</strong> Report findings through proper channels and respect scope limitations.</p>
        </div>
        """
    
    def _get_bug_bounty_javascript(self) -> str:
        """JavaScript for interactive features"""
        return """
        function toggleCollapsible(element) {
            element.classList.toggle('active');
            var content = element.nextElementSibling;
            if (content.classList.contains('collapsible-content')) {
                content.classList.toggle('active');
            }
        }
        
        // Auto-expand first section for better UX
        document.addEventListener('DOMContentLoaded', function() {
            const firstCollapsible = document.querySelector('.collapsible');
            if (firstCollapsible) {
                toggleCollapsible(firstCollapsible);
            }
        });
        
        // Add smooth scrolling for internal links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                document.querySelector(this.getAttribute('href')).scrollIntoView({
                    behavior: 'smooth'
                });
            });
        });
        """
    
    def _generate_detailed_findings_html(self, domain: str, json_file: str) -> bool:
        """Generate HTML for detailed findings JSON"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle list format
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            # Create basic detailed findings HTML
            html_content = self._create_basic_findings_html(domain, data, "Detailed Findings")
            
            html_file = json_file.replace('.json', '_report.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.success(f"Generated detailed findings HTML: {html_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating detailed findings HTML for {domain}: {e}")
            return False
    
    def _generate_stats_html(self, domain: str, json_file: str) -> bool:
        """Generate HTML for stats JSON"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            html_content = self._create_basic_findings_html(domain, data, "Statistics Report")
            
            html_file = json_file.replace('.json', '_report.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.success(f"Generated stats HTML: {html_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating stats HTML for {domain}: {e}")
            return False
    
    def _generate_database_html(self, domain: str, json_file: str) -> bool:
        """Generate HTML for database format JSON"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            html_content = self._create_basic_findings_html(domain, data, "Database Export")
            
            html_file = json_file.replace('.json', '_report.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.success(f"Generated database HTML: {html_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating database HTML for {domain}: {e}")
            return False
    
    def _generate_generic_json_html(self, domain: str, json_file: str) -> bool:
        """Generate HTML for any JSON file"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            filename = os.path.basename(json_file)
            html_content = self._create_basic_findings_html(domain, data, f"Report: {filename}")
            
            html_file = json_file.replace('.json', '_report.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.success(f"Generated generic HTML: {html_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating generic HTML for {domain}: {e}")
            return False
    
    def _create_basic_findings_html(self, domain: str, data: Any, report_title: str) -> str:
        """Create basic HTML for any JSON data"""
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title} - {domain}</title>
    <style>
        {self._get_bug_bounty_css()}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{report_title}</h1>
            <div class="subtitle">Domain: <strong>{domain}</strong></div>
            <div class="meta">Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
        </div>
        
        <div class="section">
            <h2>📊 Data Analysis</h2>
            <div class="collapsible" onclick="toggleCollapsible(this)">
                View JSON Data
            </div>
            <div class="collapsible-content">
                <div class="code-block">
                    <pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>
                </div>
            </div>
        </div>
        
        {self._generate_bug_bounty_footer()}
    </div>
    
    <script>
        {self._get_bug_bounty_javascript()}
    </script>
</body>
</html>"""
        
        return html_content