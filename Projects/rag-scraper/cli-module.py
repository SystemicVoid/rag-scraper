"""Command-line interface for RAG Scraper."""

import click
from loguru import logger
import sys
from pathlib import Path
from typing import Optional
import asyncio

# Adjust imports for direct module execution
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Use importlib to import modules with hyphens in their names
import importlib.util

# Function to import a module from a file path
def import_module_from_file(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import modules
config_module = import_module_from_file("config-module.py", "config_module")
scraper_module = import_module_from_file("scraper-module.py", "scraper_module")
processor_module = import_module_from_file("processor-module.py", "processor_module")
embeddings_module = import_module_from_file("embeddings-module.py", "embeddings_module")
storage_module = import_module_from_file("storage-module.py", "storage_module")
interactive_scraper_module = import_module_from_file("interactive-scraper-module.py", "interactive_scraper_module")

# Get the necessary classes/functions
load_config = config_module.load_config
WebScraper = scraper_module.WebScraper
InteractiveWebScraper = interactive_scraper_module.InteractiveWebScraper
ContentProcessor = processor_module.ContentProcessor
EmbeddingGenerator = embeddings_module.EmbeddingGenerator
VectorStorage = storage_module.VectorStorage


def setup_logger(log_level: str) -> None:
    """Setup logger configuration.
    
    Args:
        log_level: Logging level
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )


@click.command()
@click.option(
    "--domain",
    required=True,
    help="Domain to scrape (without protocol, e.g., example.com)",
)
@click.option(
    "--output-dir",
    default=None,
    help="Directory to save output files",
    type=click.Path(),
)
@click.option(
    "--max-pages",
    default=None,
    help="Maximum number of pages to scrape",
    type=int,
)
@click.option(
    "--respect-robots",
    is_flag=True,
    default=None,
    help="Respect robots.txt file",
)
@click.option(
    "--log-level",
    default=None,
    help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
)
@click.option(
    "--interactive",
    is_flag=True,
    default=False,
    help="Enable interactive page selection",
)
def main(
    domain: str,
    output_dir: Optional[str] = None,
    max_pages: Optional[int] = None,
    respect_robots: Optional[bool] = None,
    log_level: Optional[str] = None,
    interactive: bool = False,
) -> None:
    """Scrape a web domain and generate embeddings for RAG systems."""
    # Load configuration
    config = load_config(domain, output_dir)
    
    # Override config with command-line arguments if provided
    if max_pages is not None:
        config.scraper.max_pages = max_pages
    if respect_robots is not None:
        config.scraper.respect_robots_txt = respect_robots
    if log_level is not None:
        config.log_level = log_level
        
    # Setup logger
    setup_logger(config.log_level)
    
    logger.info(f"Starting RAG Scraper for domain: {domain}")
    
    # Initialize components
    processor = ContentProcessor(config.processor)
    embedding_generator = EmbeddingGenerator(config.embedding)
    storage = VectorStorage(config.storage)
    
    try:
        # Step 1: Scrape web pages (interactive or standard)
        logger.info("Step 1: Scraping web pages")
        
        if interactive:
            # Use interactive scraper
            scraper = InteractiveWebScraper(config.scraper, config.output_dir / "html")
            
            # Run the interactive scraping process in asyncio event loop
            loop = asyncio.get_event_loop()
            content_map = loop.run_until_complete(scraper.interactive_scrape())
        else:
            # Use standard scraper
            scraper = WebScraper(config.scraper, config.output_dir / "html")
            content_map = scraper.scrape()
        
        if not content_map:
            logger.warning("No pages were scraped or selected. Exiting.")
            return
        
        # Step 2: Process content
        logger.info("Step 2: Processing content")
        processed_content = processor.process_content(content_map)
        
        # Step 3: Generate embeddings
        logger.info("Step 3: Generating embeddings")
        embeddings_data = embedding_generator.generate_embeddings(processed_content)
        
        # Step 4: Save to storage
        logger.info("Step 4: Saving to storage")
        storage.save(embeddings_data)
        
        logger.success(f"RAG Scraper completed successfully!")
        logger.info(f"Scraped {len(content_map)} pages")
        logger.info(f"Processed {len(processed_content)} pages with content")
        logger.info(f"Generated embeddings for all processed content")
        logger.info(f"Data saved to {config.output_dir}")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
