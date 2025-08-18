# JS Endpoint Extractor

A Python tool for discovering and extracting API endpoints, authentication URLs, and other interesting patterns from JavaScript files found on websites. This tool is designed for security researchers, penetration testers, and developers who need to map web application endpoints.

## Features

- **Automated JS Discovery**: Extracts JavaScript file URLs from target websites
- **Pattern-Based Extraction**: Uses regex templates to find various types of endpoints
- **Categorized Results**: Organizes findings into logical categories (API endpoints, auth endpoints, etc.)
- **Multiple Output Formats**: Supports TXT, JSON, and structured database-ready formats
- **Domain-Aware Processing**: Handles multiple domains and tracks source relationships

## Installation

### Prerequisites
- Python 3.6+
- pip

### Setup
1. Clone or download this repository
2. Install dependencies:
```bash
python3 setup.py
```

3. Create necessary directories:
```bash
mkdir -p data/js_files data/url_content output
```

## Usage

### Basic Usage
```bash
python main.py input_file.txt
```

Where `input_file.txt` contains one URL per line:
```
https://example.com
https://target-site.com
subdomain.example.org
```

### Example
```bash
# Create input file
echo "https://facebook.com" > targets.txt

# Run the tool
python main.py targets.txt
```

## Output Files

The tool generates several output files in the `./output/` directory:

### 1. Flat Endpoint List
- `{domain}_endpoints_found.txt` - Simple list of all discovered endpoints

### 2. Detailed JSON Report
- `{domain}_endpoints_detailed.json` - Complete results with source tracking
- `{domain}_endpoints_for_db.json` - Database-ready flat structure
- `{domain}_endpoint_stats.json` - Summary statistics

### 3. Categorized Results
Results are organized into categories such as:
- API endpoints (`/api/`, `/v1/`, etc.)
- Authentication (`/auth/`, `/login`, `/oauth/`)
- Admin interfaces (`/admin/`, `/dashboard/`)
- Payment systems (`/payment/`, `/stripe/`)
- And many more...

## Configuration

Edit `config.py` to customize:

```python
# Timeout for web requests (seconds)
REQUEST_TIMEOUT = 10

# User agent for requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."

# Output and data directories
OUTPUT_DIR = "./output/"
DATA_DIR = "./data/"
```

## Endpoint Categories

The tool searches for endpoints in these categories:

| Category | Description | Examples |
|----------|-------------|----------|
| `ajax_endpoints` | AJAX call endpoints | `/ajax/`, `_ajax.php` |
| `api_endpoints` | REST API endpoints | `/api/v1/`, `/rest/` |
| `authentication_endpoints` | Auth-related URLs | `/login`, `/oauth/` |
| `payment_endpoints` | Payment processing | `/checkout/`, `/stripe/` |
| `admin_endpoints` | Administrative interfaces | `/admin/`, `/dashboard/` |
| `websockets` | WebSocket connections | `ws://`, `/socket.io/` |
| `external_api_domains` | Third-party APIs | `api.stripe.com` |
| `cloud_services` | Cloud service URLs | `.amazonaws.com` |
| And 20+ more categories... | | |

## Template System

Endpoint patterns are defined in `templates/endpoints.txt`. Each category starts with `#[category_name]` followed by regex patterns:

```
#[api_endpoints]
['"`](\/api\/[\w\d\/\-_.?=&%]+)['"`]
['"`](\/v\d+\/[\w\d\/\-_.?=&%]+)['"`]

#[authentication_endpoints]
['"`](\/auth\/[\w\d\/\-_.?=&%]+)['"`]
['"`](\/login)['"`]
```

### Adding Custom Patterns
1. Edit `templates/endpoints.txt`
2. Add a new category: `#[my_category]`
3. Add regex patterns below it
4. Run the tool

## Architecture

### Core Components

- **`main.py`** - Entry point and orchestration
- **`EndpointProcessor`** - Regex matching and categorization
- **`JsProcessor`** - JavaScript file extraction and processing
- **`WebRequests`** - HTTP client with error handling
- **`DomainHandler`** - URL parsing and domain extraction
- **`LoadTemplate`** - Template file parsing

### Data Flow

1. **URL Input** → Parse target URLs from input file
2. **HTML Fetch** → Download HTML content from each URL
3. **JS Discovery** → Extract JavaScript file URLs from HTML
4. **JS Analysis** → Download and analyze each JS file
5. **Pattern Matching** → Apply regex templates to find endpoints
6. **Categorization** → Organize results by endpoint type
7. **Output Generation** → Create multiple output formats

## Security Considerations

**Important Notes:**

- This tool is intended for authorized security testing only
- Always obtain proper permission before testing websites
- Respect robots.txt and rate limiting
- Be mindful of the target's server resources
- Use responsibly and ethically

## Troubleshooting

### Common Issues

**No JavaScript files found:**
- Check if the target site uses JavaScript
- Verify the site is accessible
- Check for redirect issues

**Empty results:**
- Verify templates file exists and is properly formatted
- Check if JS files are accessible (not behind authentication)
- Review regex patterns for your specific use case

**Connection timeouts:**
- Increase `REQUEST_TIMEOUT` in config.py
- Check network connectivity
- Some sites may block automated requests

### Debug Mode

Add print statements in `main.py` to see processing details:
```python
print(f"Processing URL: {url}")
print(f"Found {len(js_links)} JS links")
```

## Sample Output

```
Processing 1 URLs...
Processing URL: https://example.com
  Found 15 JS links.
Total JS links to process: 15

Processing JS links...
Processing JS Link 1/15: https://example.com/static/js/main.js
Processing JS Link 2/15: https://example.com/api/client.js

==================================================
SAVING RESULTS...
All endpoints saved to: ./output/example.com_endpoints_found.txt (47 endpoints)
Categorized endpoints saved to: ./output/example.com_endpoints_by_category.js
Summary statistics saved to: ./output/example.com_endpoint_stats.json

==================================================
Total Categories: 12
Total Endpoints: 47
Processing completed successfully!
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add new endpoint patterns to `templates/endpoints.txt`
4. Test with various websites
5. Submit a pull request

### Adding New Categories

To add a new endpoint category:
1. Add the category to `templates/endpoints.txt`
2. Include relevant regex patterns
3. Test the patterns work correctly
4. Update this README with the new category

## License

MIT License - see LICENSE file for details.

## Disclaimer

This tool is for educational and authorized security testing purposes only. Users are responsible for complying with applicable laws and obtaining proper authorization before testing any systems they do not own or have explicit permission to test.