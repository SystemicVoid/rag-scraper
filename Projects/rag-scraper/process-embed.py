#!/usr/bin/env python
"""Process and embed already scraped content."""

import click
from pathlib import Path
import importlib.util
import glob
import os

def import_module_from_file(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import necessary modules
config_module = import_module_from_file("config-module.py", "config_module")
processor_module = import_module_from_file("processor-module.py", "processor_module")
embeddings_module = import_module_from_file("embeddings-module.py", "embeddings_module")
storage_module = import_module_from_file("storage-module.py", "storage_module")

@click.command()
@click.option("--domain", required=True, help="Domain used for scraping")
@click.option("--input-dir", required=True, help="Directory containing scraped HTML files")
@click.option("--output-dir", default=None, help="Directory to save output files")
def main(domain, input_dir, output_dir):
    """Process and embed previously scraped HTML content."""
    input_path = Path(input_dir)
    
    # Load configuration
    config = config_module.load_config(domain, output_dir)
    
    # Initialize components
    processor = processor_module.ContentProcessor(config.processor)
    embedding_generator = embeddings_module.EmbeddingGenerator(config.embedding)
    storage = storage_module.VectorStorage(config.storage)
    
    # Create a content map from existing HTML files
    content_map = {}
    html_files = glob.glob(str(input_path / "*.html"))
    
    if not html_files:
        click.echo(f"No HTML files found in {input_path}")
        return
    
    # Use filenames to reconstruct URLs or just use placeholders
    for idx, html_file in enumerate(html_files):
        file_path = Path(html_file)
        # Since we don't have the original URLs, we can use filenames as identifiers
        # In a real scenario, you might want to store URL info with the files
        url_key = f"{domain}/{os.path.basename(html_file)}"
        content_map[url_key] = file_path
    
    click.echo(f"Found {len(content_map)} HTML files to process")
    
    # Step 1: Process content
    click.echo("Processing content...")
    processed_content = processor.process_content(content_map)
    
    # Step 2: Generate embeddings
    click.echo("Generating embeddings...")
    embeddings_data = embedding_generator.generate_embeddings(processed_content)
    
    # Step 3: Save to storage
    click.echo("Saving to storage...")
    storage.save(embeddings_data)
    
    click.echo(f"Processing complete!")
    click.echo(f"Processed {len(processed_content)} pages with content")
    click.echo(f"Generated embeddings for all processed content")
    click.echo(f"Data saved to {config.output_dir}")

if __name__ == "__main__":
    main()