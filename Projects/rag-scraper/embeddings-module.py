"""Embedding generation for RAG Scraper."""

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from typing import Dict, List, Tuple

from .config import EmbeddingConfig


class EmbeddingGenerator:
    """Generate embeddings for processed text chunks."""

    def __init__(self, config: EmbeddingConfig):
        """Initialize the embedding generator.
        
        Args:
            config: Embedding configuration
        """
        self.config = config
        
        logger.info(f"Loading embedding model: {config.model_name}")
        self.model = SentenceTransformer(config.model_name, device=config.device)
        
        logger.info("Embedding generator initialized")

    def generate_embeddings(
        self, processed_content: Dict[str, Tuple[List[str], Dict]]
    ) -> Dict[str, Tuple[List[str], List[np.ndarray], Dict]]:
        """Generate embeddings for processed text chunks.
        
        Args:
            processed_content: Dictionary mapping URLs to chunks and metadata
            
        Returns:
            Dict[str, Tuple[List[str], List[np.ndarray], Dict]]: 
                Dictionary mapping URLs to chunks, embeddings, and metadata
        """
        results = {}
        all_chunks = []
        url_to_chunk_indices = {}
        
        # Collect all chunks for batch processing
        for url, (chunks, _) in processed_content.items():
            start_idx = len(all_chunks)
            all_chunks.extend(chunks)
            end_idx = len(all_chunks)
            url_to_chunk_indices[url] = (start_idx, end_idx)
            
        logger.info(f"Generating embeddings for {len(all_chunks)} text chunks")
        
        # Generate embeddings in batches
        embeddings = []
        for i in tqdm(range(0, len(all_chunks), self.config.batch_size)):
            batch = all_chunks[i:i + self.config.batch_size]
            batch_embeddings = self.model.encode(
                batch, 
                show_progress_bar=False,
                normalize_embeddings=self.config.normalize_embeddings
            )
            embeddings.extend(batch_embeddings)
            
        # Reorganize results by URL
        for url, (chunks, metadata) in processed_content.items():
            start_idx, end_idx = url_to_chunk_indices[url]
            chunk_embeddings = embeddings[start_idx:end_idx]
            results[url] = (chunks, chunk_embeddings, metadata)
            
        logger.info(f"Embedding generation complete: {len(embeddings)} embeddings generated")
        return results