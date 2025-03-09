"""Test script for the interactive scraper."""

import sys
import asyncio
from pathlib import Path

# Import the modules directly
import importlib.util

def import_module_from_file(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import modules
config_module = import_module_from_file("config-module.py", "config_module")
interactive_scraper_module = import_module_from_file("interactive-scraper-module.py", "interactive_scraper_module")

# Get the necessary classes/functions
load_config = config_module.load_config
InteractiveWebScraper = interactive_scraper_module.InteractiveWebScraper

async def main():
    # Example domain
    domain = "example.com"
    output_dir = Path("./data")
    
    # Load config
    config = load_config(domain, str(output_dir))
    
    # Create interactive scraper
    scraper = InteractiveWebScraper(config.scraper, output_dir / "html")
    
    # Skip the interactive part and directly run the scraping
    # First discover pages
    print("Discovering pages...")
    discovered_pages = await scraper.discover_pages(max_pages=5)
    print(f"Found {len(discovered_pages)} pages")
    
    # Select all pages automatically
    all_urls = list(discovered_pages.keys())
    print(f"Selected {len(all_urls)} pages")
    
    # Scrape them
    print("Scraping selected pages...")
    content_map = scraper.scrape_selected_pages(all_urls)
    
    # Print results
    print(f"Scraped {len(content_map)} pages")
    for url, path in content_map.items():
        print(f"- {url} -> {path}")

if __name__ == "__main__":
    asyncio.run(main())