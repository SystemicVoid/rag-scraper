"""Configuration settings for the RAG Scraper."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# Load environment variables from .env file
load_dotenv()


class ScraperConfig(BaseModel):
    """Configuration for web scraper."""

    domain: str = Field(..., description="Domain to scrape")
    start_urls: List[str] = Field(default_factory=list, description="Starting URLs")
    max_pages: int = Field(
        default=1000, description="Maximum number of pages to scrape"
    )
    respect_robots_txt: bool = Field(
        default=True, description="Whether to respect robots.txt"
    )
    user_agent: str = Field(
        default="RAG Scraper Bot (+https://example.com/bot)",
        description="User agent to use for scraping",
    )
    delay: float = Field(default=0.5, description="Delay between requests in seconds")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_depth: Optional[int] = Field(
        default=None, description="Maximum depth to crawl (None for unlimited)"
    )
    allowed_domains: List[str] = Field(
        default_factory=list, description="Additional allowed domains"
    )

    @validator("start_urls", pre=True, always=True)
    def set_start_urls(cls, v, values):
        """Set start_urls if not provided."""
        if not v and "domain" in values:
            return [f"https://{values['domain']}"]
        return v

    @validator("allowed_domains", pre=True, always=True)
    def set_allowed_domains(cls, v, values):
        """Set allowed_domains if not provided."""
        if not v and "domain" in values:
            return [values["domain"]]
        return v


class ProcessorConfig(BaseModel):
    """Configuration for content processor."""

    min_content_length: int = Field(
        default=50, description="Minimum content length to keep"
    )
    chunk_size: int = Field(default=1000, description="Size of text chunks")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")
    remove_emails: bool = Field(default=True, description="Remove email addresses")
    remove_urls: bool = Field(default=False, description="Remove URLs")
    extract_headers: bool = Field(
        default=True, description="Extract headers for better chunking"
    )
    extract_tables: bool = Field(
        default=True, description="Extract tables as structured data"
    )


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    model_name: str = Field(
        default="all-MiniLM-L6-v2",
        description="Model name for sentence-transformers",
    )
    device: str = Field(default="cpu", description="Device to use (cpu or cuda)")
    batch_size: int = Field(default=32, description="Batch size for embedding generation")
    normalize_embeddings: bool = Field(
        default=True, description="Whether to normalize embeddings"
    )


class StorageConfig(BaseModel):
    """Configuration for vector storage."""

    storage_type: str = Field(default="faiss", description="Storage type (faiss, etc.)")
    index_path: Path = Field(default=Path("./data/index"), description="Path to index")
    metadata_path: Path = Field(
        default=Path("./data/metadata.json"), description="Path to metadata"
    )


class Config(BaseModel):
    """Main configuration for RAG Scraper."""

    scraper: ScraperConfig
    processor: ProcessorConfig = ProcessorConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    storage: StorageConfig = StorageConfig()
    output_dir: Path = Field(default=Path("./data"), description="Output directory")
    log_level: str = Field(default="INFO", description="Logging level")

    @validator("output_dir", pre=True)
    def create_output_dir(cls, v):
        """Create output directory if it doesn't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path


def load_config(domain: str, output_dir: Optional[str] = None) -> Config:
    """Load configuration from environment variables and command-line arguments."""
    scraper_config = ScraperConfig(
        domain=domain,
        max_pages=int(os.getenv("MAX_PAGES", "1000")),
        respect_robots_txt=os.getenv("RESPECT_ROBOTS_TXT", "true").lower() == "true",
        delay=float(os.getenv("DELAY", "0.5")),
    )

    processor_config = ProcessorConfig(
        min_content_length=int(os.getenv("MIN_CONTENT_LENGTH", "50")),
        chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200")),
    )

    embedding_config = EmbeddingConfig(
        model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        device=os.getenv("DEVICE", "cpu"),
        batch_size=int(os.getenv("BATCH_SIZE", "32")),
    )

    out_dir = Path(output_dir) if output_dir else Path(os.getenv("OUTPUT_DIR", "./data"))
    
    storage_config = StorageConfig(
        storage_type=os.getenv("STORAGE_TYPE", "faiss"),
        index_path=out_dir / "index",
        metadata_path=out_dir / "metadata.json",
    )

    return Config(
        scraper=scraper_config,
        processor=processor_config,
        embedding=embedding_config,
        storage=storage_config,
        output_dir=out_dir,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
