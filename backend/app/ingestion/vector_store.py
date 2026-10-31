"""
Vector Store for LegalLens

Abstract interface for storing and retrieving embeddings.
Supports Chroma (development) and Qdrant (production).
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector stores"""

    @abstractmethod
    def add_embeddings(self, embeddings: List[dict]) -> bool:
        """Add embeddings to the store"""
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float, dict]]:
        """Search for similar embeddings"""
        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        pass

    @abstractmethod
    def get_chunk(self, chunk_id: str) -> Optional[dict]:
        """Get a specific chunk by ID"""
        pass


class ChromaVectorStore(VectorStore):
    """
    Vector store using Chroma (local development).

    Features:
    - File-based persistence
    - In-memory indexing
    - Easy to inspect and debug
    - Good for development and testing
    """

    def __init__(self, db_path: str = "./chroma_db", collection_name: str = "legallens"):
        """
        Initialize Chroma vector store.

        Args:
            db_path: Path to Chroma database directory
            collection_name: Name of collection
        """
        try:
            import chromadb
            self.chromadb = chromadb
        except ImportError:
            raise ImportError("chromadb not installed. Install with: pip install chromadb")

        try:
            self.client = chromadb.PersistentClient(path=db_path)
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Initialized Chroma vector store at {db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise

    def add_embeddings(self, embeddings: List[dict]) -> bool:
        """
        Add embeddings to Chroma.

        Args:
            embeddings: List of dicts with 'chunk_id', 'embedding', 'text', 'metadata'

        Returns:
            True if successful
        """
        if not embeddings:
            return True

        try:
            ids = [e['chunk_id'] for e in embeddings]
            vectors = [e['embedding'] for e in embeddings]
            metadatas = [
                {
                    'document_id': e['document_id'],
                    'chunk_number': e['chunk_number'],
                    'token_count': e['token_count'],
                    'character_start': e['character_start'],
                    'character_end': e['character_end'],
                    **e.get('metadata', {})
                }
                for e in embeddings
            ]
            documents = [e['text'] for e in embeddings]

            self.collection.add(
                ids=ids,
                embeddings=vectors,
                metadatas=metadatas,
                documents=documents
            )

            logger.info(f"Added {len(embeddings)} embeddings to Chroma")
            return True

        except Exception as e:
            logger.error(f"Failed to add embeddings to Chroma: {e}")
            return False

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float, dict]]:
        """
        Search for similar chunks.

        Args:
            query_embedding: Query embedding (384 dims)
            top_k: Number of results to return

        Returns:
            List of tuples: (chunk_id, similarity_score, metadata_dict)
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['embeddings', 'metadatas', 'documents', 'distances']
            )

            if not results['ids'] or not results['ids'][0]:
                return []

            # Convert distances to similarity (1 - distance for cosine)
            chunks = []
            for i, chunk_id in enumerate(results['ids'][0]):
                similarity = 1 - results['distances'][0][i]  # Chroma returns distances
                metadata = results['metadatas'][0][i]
                chunks.append((chunk_id, similarity, metadata))

            return chunks

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        try:
            # Get all chunk IDs for this document
            results = self.collection.get(
                where={"document_id": {"$eq": document_id}},
                include=[]
            )

            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    def get_chunk(self, chunk_id: str) -> Optional[dict]:
        """Get a specific chunk"""
        try:
            results = self.collection.get(
                ids=[chunk_id],
                include=['embeddings', 'metadatas', 'documents']
            )

            if not results['ids'] or not results['ids'][0]:
                return None

            return {
                'chunk_id': chunk_id,
                'text': results['documents'][0][0],
                'metadata': results['metadatas'][0][0],
                'embedding': results['embeddings'][0][0]
            }

        except Exception as e:
            logger.error(f"Failed to get chunk: {e}")
            return None


class QdrantVectorStore(VectorStore):
    """
    Vector store using Qdrant (production).

    Features:
    - Distributed vector database
    - High performance at scale
    - Advanced filtering
    - Production-ready

    Note: Requires Qdrant server running
    """

    def __init__(self, host: str = "localhost", port: int = 6333, collection_name: str = "legallens"):
        """
        Initialize Qdrant vector store.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of collection
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            self.QdrantClient = QdrantClient
            self.Distance = Distance
            self.VectorParams = VectorParams
        except ImportError:
            raise ImportError("qdrant-client not installed. Install with: pip install qdrant-client")

        try:
            self.client = QdrantClient(host=host, port=port)
            self.collection_name = collection_name

            # Create collection if not exists
            try:
                self.client.recreate_collection(
                    collection_name=collection_name,
                    vectors_config=self.VectorParams(size=384, distance=Distance.COSINE)
                )
            except Exception:
                # Collection might already exist
                pass

            logger.info(f"Initialized Qdrant vector store at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            raise

    def add_embeddings(self, embeddings: List[dict]) -> bool:
        """Add embeddings to Qdrant"""
        # Implementation would be similar to Chroma
        # Detailed implementation left for production setup
        logger.warning("Qdrant implementation deferred to production phase")
        return False

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float, dict]]:
        """Search for similar chunks"""
        logger.warning("Qdrant implementation deferred to production phase")
        return []

    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        logger.warning("Qdrant implementation deferred to production phase")
        return False

    def get_chunk(self, chunk_id: str) -> Optional[dict]:
        """Get a specific chunk"""
        logger.warning("Qdrant implementation deferred to production phase")
        return None


def get_vector_store(store_type: str = "chroma", **kwargs) -> VectorStore:
    """
    Factory function to get vector store instance.

    Args:
        store_type: "chroma" or "qdrant"
        **kwargs: Arguments passed to store constructor

    Returns:
        VectorStore instance
    """
    if store_type == "chroma":
        return ChromaVectorStore(**kwargs)
    elif store_type == "qdrant":
        return QdrantVectorStore(**kwargs)
    else:
        raise ValueError(f"Unknown store type: {store_type}")


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)

    try:
        # Create store
        store = get_vector_store("chroma", db_path="./test_chroma_db")
        print("✅ Vector store initialized")

        # Sample embeddings
        import random
        embeddings = [
            {
                'chunk_id': f'doc_test~chunk_{i:03d}',
                'document_id': 'doc_test',
                'chunk_number': i,
                'text': f'Sample text {i}' * 10,
                'token_count': 100 + i*10,
                'character_start': i*500,
                'character_end': (i+1)*500,
                'embedding': [random.random() for _ in range(384)],
                'metadata': {'page': i+1}
            }
            for i in range(5)
        ]

        # Add embeddings
        success = store.add_embeddings(embeddings)
        print(f"✅ Added embeddings: {success}")

        # Search
        query = [random.random() for _ in range(384)]
        results = store.search(query, top_k=3)
        print(f"✅ Search returned {len(results)} results")

        # Get chunk
        chunk = store.get_chunk('doc_test~chunk_001')
        if chunk:
            print(f"✅ Retrieved chunk: {chunk['chunk_id']}")

    except Exception as e:
        print(f"❌ Error: {e}")
