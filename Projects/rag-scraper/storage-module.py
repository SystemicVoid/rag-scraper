"""Vector storage for RAG Scraper."""

import faiss
import json
import numpy as np
from loguru import logger
from pathlib import Path
from typing import Dict, List, Tuple, Union

from .config import StorageConfig


class VectorStorage:
    """Vector storage for RAG Scraper."""

    def __init__(self, config: StorageConfig):
        """Initialize the vector storage.
        
        Args:
            config: Storage configuration
        """
        self.config = config
        self.config.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Vector storage initialized with type: {config.storage_type}")

    def save(
        self,
        embeddings_data: Dict[str, Tuple[List[str], List[np.ndarray], Dict]],
    ) -> None:
        """Save embeddings and metadata to storage.
        
        Args:
            embeddings_data: Dictionary mapping URLs to chunks, embeddings, and metadata
        """
        # Flatten all data
        all_chunks = []
        all_embeddings = []
        all_metadata = []
        
        for url, (chunks, chunk_embeddings, metadata) in embeddings_data.items():
            for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                all_chunks.append(chunk)
                all_embeddings.append(embedding)
                
                # Create individual metadata for each chunk
                chunk_metadata = metadata.copy()
                chunk_metadata["chunk_id"] = i
                chunk_metadata["chunk_text"] = chunk[:100] + "..." if len(chunk) > 100 else chunk
                all_metadata.append(chunk_metadata)
        
        # Convert embeddings to numpy array
        embeddings_array = np.array(all_embeddings).astype(np.float32)
        
        # Create and save FAISS index
        dimension = embeddings_array.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        
        logger.info(f"Saving index with {len(all_chunks)} vectors to {self.config.index_path}")
        faiss.write_index(index, str(self.config.index_path))
        
        # Save metadata
        metadata_obj = {
            "chunks": all_chunks,
            "metadata": all_metadata,
        }
        
        logger.info(f"Saving metadata to {self.config.metadata_path}")
        with open(self.config.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_obj, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Storage complete: {len(all_chunks)} vectors stored")

    def load(self) -> Tuple[faiss.Index, List[str], List[Dict]]:
        """Load embeddings and metadata from storage.
        
        Returns:
            Tuple[faiss.Index, List[str], List[Dict]]: 
                FAISS index, chunks, and metadata
        """
        if not self.config.index_path.exists() or not self.config.metadata_path.exists():
            logger.error("Index or metadata file not found")
            raise FileNotFoundError("Index or metadata file not found")
            
        # Load FAISS index
        logger.info(f"Loading index from {self.config.index_path}")
        index = faiss.read_index(str(self.config.index_path))
        
        # Load metadata
        logger.info(f"Loading metadata from {self.config.metadata_path}")
        with open(self.config.metadata_path, "r", encoding="utf-8") as f:
            metadata_obj = json.load(f)
            
        chunks = metadata_obj["chunks"]
        metadata = metadata_obj["metadata"]
        
        logger.info(f"Loaded {len(chunks)} vectors from storage")
        return index, chunks, metadata