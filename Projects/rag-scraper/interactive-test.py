#!/usr/bin/env python
"""Interactive RAG Scraper CLI."""

import asyncio
import click
from pathlib import Path
import importlib.util

def import_module_from_file(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import config and interactive scraper modules
config_module = import_module_from_file("config-module.py", "config_module")
interactive_scraper_module = import_module_from_file("interactive-scraper-module.py", "interactive_scraper_module")

async def run_interactive_scraper(domain, output_dir, max_pages):
    """Run the interactive web scraper for RAG systems."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load configuration
    config = config_module.load_config(domain, output_dir)
    config.scraper.max_pages = max_pages
    
    # Initialize interactive scraper
    scraper = interactive_scraper_module.InteractiveWebScraper(
        config.scraper, 
        output_path / "html"
    )
    
    # Run the interactive scraping process
    content_map = await scraper.interactive_scrape()
    
    if content_map:
        click.echo(f"\nSuccessfully scraped {len(content_map)} pages.")
        click.echo(f"Content saved to {output_path / 'html'}")
    else:
        click.echo("No pages were selected for scraping.")
    
    return content_map

@click.command()
@click.option("--domain", required=True, help="Domain to scrape (e.g., example.com)")
@click.option("--output-dir", default="./data", help="Directory to save scraped data")
@click.option("--max-pages", default=100, type=int, help="Maximum pages to discover")
def main(domain, output_dir, max_pages):
    """Interactive web scraper for RAG systems."""
    asyncio.run(run_interactive_scraper(domain, output_dir, max_pages))

if __name__ == "__main__":
    main()