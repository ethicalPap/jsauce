from setuptools import setup, find_packages
import os

def read_requirements():
    try:
        with open('requirements.txt', 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        return []

def read_readme():
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "JS Endpoint Extractor - A Python tool for discovering and extracting API endpoints from JavaScript files"

setup(
    name="jsauce",
    version="0.1.0",
    author="Van Perry",
    author_email="ethicalpap@gmail.com",
    description="A Python tool for discovering and extracting API endpoints from JavaScript files found on websites",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/ethicalPap/jsauce",
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires='>=3.6',
    
    # Include additional files
    include_package_data=True,
    package_data={
        'jsauce': ['templates/*.txt'],
    },
    
    # Entry points for CLI usage
    entry_points={
        'console_scripts': [
            'jsauce=main:main',
        ],
    },
    
    # Classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Security",
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP",
    ],
    
    # Keywords for PyPI search
    keywords="javascript, endpoint, extraction, security, web, api, pentesting",
    
    # Additional metadata
    project_urls={
        "Bug Reports": "https://github.com/ethicalPap/jsauce/issues",
        "Source": "https://github.com/ethicalPap/jsauce",
        "Documentation": "https://github.com/ethicalPap/jsauce#readme",
    },
)