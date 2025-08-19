# JSauce - JavaScript Endpoint Grabber

A Python tool for discovering and extracting API endpoints, authentication URLs, and security-sensitive patterns from JavaScript files found on websites. JSauce is designed for security researchers, penetration testers, and developers who need to comprehensively map web application attack surfaces.

## Features

- **Automated JS Discovery**: Intelligently extracts JavaScript file URLs from target websites
- **Advanced Pattern Matching**: Uses comprehensive YAML-based regex templates for endpoint discovery
- **Security-Focused Categories**: Organizes findings into 40+ security-relevant categories including:
  - API endpoints and authentication systems
  - Payment processing and admin interfaces  
  - API keys, tokens, and sensitive credentials
  - Cloud services and external integrations
  - Framework-specific patterns and debug endpoints
- **Multiple Output Formats**: Generates TXT, JSON, and visual Mermaid flowcharts
- **Visual Reporting**: Creates interactive flowchart diagrams showing endpoint relationships
- **Domain-Aware Processing**: Handles multiple domains with organized output structure
- **Prioritized Results**: Focuses on high-impact security findings first

## Prerequisites

- Python 3.6+
- pip package manager
- Mermaid CLI for diagram rendering

## Installation

### Quick Setup
```bash
# Clone the repository
git clone https://github.com/ethicalPap/jsauce.git
cd jsauce

# Create necessary directories
mkdir -p data/{js_files,url_content} output

# Install
pip install .

# Run directly
jsauce input_file.txt
```

## Usage

### Basic Usage
```bash
python jsauce.py input_file.txt
```

### Input File Format
Create a text file with one URL per line:
```
https://example.com
https://target-site.com
subdomain.example.org
walmart.com
facebook.com
```

### Example Workflow
```bash
# Create your target list
echo -e "https://facebook.com\nhttps://walmart.com" > targets.txt

# Run JSauce
python jsauce.py targets.txt

# View results
ls output/facebook.com/
# facebook.com_endpoints_found.txt
# facebook.com_endpoints_detailed.json
# facebook.com_flowchart.svg
# facebook.com_flowchart.png
```

## Output Files

JSauce generates results in the `./output/{domain}/` directory:

### 1. Quick Reference
- `{domain}_endpoints_found.txt` - Clean list of all discovered endpoints

### 2. Detailed Analysis
- `{domain}_endpoints_detailed.json` - Complete results with source tracking and categorization
- `{domain}_endpoints_for_db.json` - Flat structure optimized for database import
- `{domain}_endpoint_stats.json` - Summary statistics and category breakdowns

### 3. Visual Reports
- `{domain}_flowchart.mmd` - Mermaid diagram source
- `{domain}_flowchart.svg` - Vector graphic flowchart
- `{domain}_flowchart.png` - Raster image flowchart

## Security Categories

JSauce categorizes findings into security-focused groups:

| Category | Security Impact | Examples |
|----------|----------------|----------|
| **admin_endpoints** | Critical | `/admin/`, `/dashboard/`, `/config/` |
| **authentication_endpoints** | Critical | `/login`, `/oauth/`, `/sso/` |
| **api_keys_tokens** | Critical | API keys, JWT tokens, AWS credentials |
| **payment_endpoints** | Critical | `/checkout/`, `/stripe/`, `/billing/` |
| **security_endpoints** | High | `/2fa/`, `/password/`, `/verify/` |
| **api_endpoints** | High | `/api/v1/`, `/rest/`, `/graphql/` |
| **user_management** | High | `/users/`, `/profile/`, `/roles/` |
| **external_apis** | Medium | Third-party API integrations |
| **websockets** | Medium | Real-time communication endpoints |
| **file_operations** | Medium | `/upload/`, `/download/`, file handling |

## Configuration

### Template Customization
Edit `templates/default_template.yaml` to add custom patterns:

```yaml
custom_endpoints:
  description: "My custom endpoint patterns"
  flags: "gi"
  patterns:
    - "[\\'\"``](/my-api/[\\w\\d/-_.?=&%]+)[\\'\"``]"
    - "[\\'\"``](/custom/[\\w\\d/-_.?=&%]+)[\\'\"``]"
```

### Settings
Modify `src/config.py` for custom behavior:

```python
# HTTP request timeout
REQUEST_TIMEOUT = 10

# Custom User-Agent
USER_AGENT = "JSauce-Scanner/1.0"

# Output directories
OUTPUT_DIR = "./output"
DATA_DIR = "./data"

# Template file
DEFAULT_TEMPLATE = "templates/default_template.yaml"
```

## Architecture

### Core Components
- **`jsauce.py`** - Main entry point and orchestration
- **`EndpointProcessor`** - Pattern matching and categorization engine
- **`JsProcessor`** - JavaScript file extraction and analysis
- **`WebRequests`** - HTTP client with error handling and retry logic
- **`MermaidConverter`** - Visual diagram generation
- **`DomainHandler`** - URL parsing and domain management

### Processing Pipeline
1. **URL Input** → Parse and validate target URLs
2. **HTML Fetch** → Download main page content
3. **JS Discovery** → Extract JavaScript file references
4. **JS Analysis** → Download and analyze each JS file
5. **Pattern Matching** → Apply YAML templates to find endpoints
6. **Categorization** → Organize results by security impact
7. **Output Generation** → Create multiple report formats
8. **Visualization** → Generate Mermaid flowcharts

## Security & Ethics

**Important Security Notice:**

JSauce is intended for **authorized security testing only**. Always ensure you have:

- Explicit written permission to test target systems
- Compliance with applicable laws and regulations
- Respect for rate limiting and server resources
- Adherence to responsible disclosure practices

**Recommended Usage:**
- Bug bounty programs with explicit scope
- Internal security assessments
- Red team exercises with proper authorization
- Academic research with appropriate permissions

## Troubleshooting

### Common Issues

**No JavaScript files found:**
```bash
# Check if target uses JS and is accessible
curl -I https://target.com
# Verify no redirect issues or authentication requirements
```

**Empty endpoint results:**
```bash
# Verify template file exists and is valid
python -c "import yaml; yaml.safe_load(open('templates/default_template.yaml'))"
# Check if JS files are publicly accessible
```

**Mermaid diagrams not generating:**
```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli
# Verify installation
mmdc --version
```

**Connection timeouts:**
```python
# Increase timeout in src/config.py
REQUEST_TIMEOUT = 30
```

### Debug Mode
Enable verbose output by modifying the banner updates in the code:

```python
# In src/packages/UrlProcessor.py, uncomment debug lines:
jsauce_banner.update_status(f"Processing: {url}")
jsauce_banner.update_status(f"Found {len(js_links)} JS links")
```

## Sample Output

```
         ██╗███████╗ █████╗ ██╗   ██╗ ██████╗███████╗
         ██║██╔════╝██╔══██╗██║   ██║██╔════╝██╔════╝
         ██║███████╗███████║██║   ██║██║     █████╗  
   ██   ██║╚════██║██╔══██║██║   ██║██║     ██╔══╝  
   ╚█████╔╝███████║██║  ██║╚██████╔╝╚██████╗███████╗
     ╚════╝ ╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝╚══════╝
                       JSauce: .js Content Mapping Tool
================================================================================
✓ ALL PROCESSING COMPLETED!
Processed 2 items total
✓ All URLs processed successfully
✓ JSON files cleaned
✓ Mermaid diagrams generated
================================================================================
```

## Contributing

We welcome contributions! Here's how to help:

### Adding New Patterns
1. Fork the repository
2. Edit `templates/default_template.yaml`
3. Add new categories or patterns:
```yaml
new_category:
  description: "Description of what this finds"
  flags: "gi"
  patterns:
    - "your-regex-pattern-here"
```
4. Test with various websites
5. Submit a pull request

### Development Setup
```bash
# Clone your fork
git clone https://github.com/yourusername/jsauce.git
cd jsauce

# Create development branch
git checkout -b feature/new-patterns

# Install development dependencies
pip install -r requirements.txt

# Test your changes
python jsauce.py testing/input_test.txt
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Created by **Papv2** (ethicalPap@gmail.com)
- Inspired by the need for comprehensive JavaScript security analysis
- Built for the security research community

## Support

- **Issues**: [GitHub Issues](https://github.com/ethicalPap/jsauce/issues)
- **Documentation**: [GitHub README](https://github.com/ethicalPap/jsauce#readme)
- **Security**: Report security issues responsibly via email

---

**Disclaimer**: JSauce is for educational and authorized security testing purposes only. Users are responsible for ensuring compliance with applicable laws and obtaining proper authorization before testing any systems they do not own or have explicit permission to test.