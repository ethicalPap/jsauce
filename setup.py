from setuptools import setup, find_packages

def read_requirements():
    try:
        with open('requirements.txt', 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        return []

setup(
    name="jsauce",
    version="0.1.0",
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires='>=3.7',
    
    # Include additional files
    include_package_data=True,
    
    # Entry points if you have CLI commands
    entry_points={
        'console_scripts': [
            'jsauce=jsauce.main:main',  # Adjust as needed
        ],
    },
    
    # Metadata
    long_description="""
    # jsauce
    
    ## Installation
    
    This package requires both Python and Node.js dependencies.
    
    ### Prerequisites
    - Python 3.7+
    - Node.js (https://nodejs.org/)
    
    ### Install
    ```bash
    # Install Node.js dependency
    npm install -g @mermaid-js/mermaid-cli
    
    # Install Python package
    pip install .
    ```
    
    ### Development Install
    ```bash
    npm install -g @mermaid-js/mermaid-cli
    pip install -r requirements.txt
    pip install -e .
    ```
    """,
    long_description_content_type="text/markdown",
)