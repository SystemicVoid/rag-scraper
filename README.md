# RAG Scraper

A Python utility for scraping web domains, processing the content, and generating embeddings suitable for Retrieval-Augmented Generation (RAG) systems. Features both automatic and interactive scraping modes.

## Overview

This tool is designed to enhance the capabilities of Large Language Models by providing domain-specific knowledge through RAG techniques. It works by:

1. Crawling and scraping pages within a specified web domain (with interactive selection option)
2. Processing and cleaning the HTML content into usable text
3. Generating high-quality embeddings from the processed content
4. Storing these embeddings in a vector database ready for RAG applications

Think of it as building a specialized knowledge library that LLMs can reference when answering questions about specific domains.

## Installation

Using pip:
```bash
pip install rag-scraper
```

Using uv (recommended):
```bash
uv pip install rag-scraper
```

For development:
```bash
git clone https://github.com/yourusername/rag-scraper.git
cd rag-scraper
uv pip install -e ".[dev]"
```

## Usage

### Standard Scraping Mode

Automatically crawls and scrapes an entire domain:

```bash
# Using the package
rag-scraper --domain example.com --output-dir ./data

# Using the module directly
python cli-module.py --domain example.com --output-dir ./data
```

### Interactive Scraping Mode

Discovers pages and lets you interactively select which ones to scrape:

```bash
# Using the package
rag-scraper --domain example.com --output-dir ./data --interactive

# Using the interactive script directly
python interactive-test.py --domain example.com --output-dir ./data --max-pages 100
```

In interactive mode, you'll be presented with a list of discovered pages and options to:
- Select all pages
- Select specific pages by index (e.g., 1,3,5-7)
- Filter pages by keyword
- Select none (cancel operation)

### Process Existing HTML

If you've already scraped content and just want to process and embed it:

```bash
python process-embed.py --domain example.com --input-dir ./data/html --output-dir ./data
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--domain` | Domain to scrape (required) | None |
| `--output-dir` | Directory to save output files | ./data |
| `--max-pages` | Maximum number of pages to scrape | 1000 |
| `--respect-robots` | Respect robots.txt file | True |
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `--interactive` | Enable interactive page selection | False |

You can also create a .env file based on the provided .env.example to configure your scraping parameters and API keys.

## Project Structure

```
rag-scraper/
├── cli-module.py                    # Main command-line interface
├── config-module.py                 # Configuration management
├── interactive-scraper-module.py    # Interactive scraping functionality
├── scraper-module.py                # Standard web scraper
├── processor-module.py              # Content processing
├── embeddings-module.py             # Embedding generation
├── storage-module.py                # Vector storage
├── interactive-test.py              # Standalone interactive scraper script
└── process-embed.py                 # Standalone processing script
```

## Advanced Features

- **Interactive Page Selection**: Browse and select specific pages to scrape
- **Two Scraping Modes**: 
  - Standard mode for comprehensive crawling
  - Interactive mode for selective scraping
- Respects robots.txt and site crawling policies
- Intelligent rate limiting to avoid overloading servers
- Content deduplication
- Customizable content processors
- Support for multiple embedding models
- Optional separate processing pipeline for pre-scraped content

## How It Works

The system works like a library cataloging service:

1. **Discovery and Collection**:
   - **Standard Mode**: Like a librarian collecting all books from a specific publisher
   - **Interactive Mode**: Like a librarian carefully selecting specific titles from a publisher's catalog

2. **Processing**: Converting raw HTML into clean, usable text chunks with appropriate metadata

3. **Embedding Generation**: Creating semantic vector representations that capture the meaning of each text chunk

4. **Vector Storage**: Organizing these embeddings in a searchable database for quick retrieval

When an LLM needs to answer a domain-specific question, it can quickly retrieve and reference the most relevant content.

## Example Workflow

### Basic Scraping and Embedding
```bash
# Scrape a domain and process the content
python cli-module.py --domain docs.example.com --output-dir ./data
```

### Interactive Scraping
```bash
# Discover and interactively select pages
python interactive-test.py --domain docs.example.com --output-dir ./data --max-pages 50

# Process the scraped HTML files
python process-embed.py --domain docs.example.com --input-dir ./data/html --output-dir ./data
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
