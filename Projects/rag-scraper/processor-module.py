"""Content processing for RAG Scraper."""

import html2text
import re
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from loguru import logger
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import ProcessorConfig


class ContentProcessor:
    """Process HTML content into clean text for embedding generation."""

    def __init__(self, config: ProcessorConfig):
        """Initialize the content processor.
        
        Args:
            config: Processor configuration
        """
        self.config = config
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = self.config.remove_urls
        self.html_converter.ignore_images = True
        self.html_converter.ignore_tables = not self.config.extract_tables
        self.html_converter.body_width = 0  # No wrapping
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        
        logger.info("Content processor initialized")

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract metadata from HTML.
        
        Args:
            soup: BeautifulSoup object
            url: URL of the page
            
        Returns:
            Dict: Metadata dictionary
        """
        metadata = {"url": url}
        
        # Extract title
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.get_text().strip()
            
        # Extract description
        description_tag = soup.find("meta", attrs={"name": "description"})
        if description_tag and description_tag.get("content"):
            metadata["description"] = description_tag.get("content").strip()
            
        # Extract publish date
        date_tag = soup.find("meta", attrs={"property": "article:published_time"})
        if date_tag and date_tag.get("content"):
            metadata["published_date"] = date_tag.get("content")
            
        return metadata

    def _clean_text(self, text: str) -> str:
        """Clean text by removing unwanted patterns and normalizing whitespace.
        
        Args:
            text: Text to clean
            
        Returns:
            str: Cleaned text
        """
        # Remove email addresses if configured
        if self.config.remove_emails:
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
            
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove very short lines (likely navigation or footer text)
        lines = text.split('\n')
        filtered_lines = [line for line in lines if len(line.strip()) > self.config.min_content_length]
        
        return '\n'.join(filtered_lines)

    def process_html(self, html_content: str, url: str) -> Tuple[List[str], Dict]:
        """Process HTML content into clean text chunks.
        
        Args:
            html_content: HTML content
            url: URL of the page
            
        Returns:
            Tuple[List[str], Dict]: List of text chunks and metadata
        """
        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Extract metadata
        metadata = self._extract_metadata(soup, url)
        
        # Remove unwanted elements
        for element in soup.select('nav, footer, .sidebar, .ads, .comments, script, style'):
            element.extract()
            
        # Convert to markdown/text
        text = self.html_converter.handle(str(soup))
        
        # Clean the text
        cleaned_text = self._clean_text(text)
        
        # Skip if content is too short
        if len(cleaned_text) < self.config.min_content_length:
            logger.debug(f"Content too short: {url}")
            return [], metadata
            
        # Split into chunks
        chunks = self.text_splitter.split_text(cleaned_text)
        
        logger.debug(f"Processed {url}: {len(chunks)} chunks")
        return chunks, metadata

    def process_content(self, content_map: Dict[str, Path]) -> Dict[str, Tuple[List[str], Dict]]:
        """Process all HTML content files.
        
        Args:
            content_map: Dictionary mapping URLs to content file paths
            
        Returns:
            Dict[str, Tuple[List[str], Dict]]: Dictionary mapping URLs to chunks and metadata
        """
        results = {}
        
        for url, file_path in content_map.items():
            try:
                html_content = file_path.read_text(encoding="utf-8")
                chunks, metadata = self.process_html(html_content, url)
                
                if chunks:
                    results[url] = (chunks, metadata)
                    
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                
        logger.info(f"Processing complete: {len(results)} pages processed")
        return results