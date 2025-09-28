"""Integration tests for search functionality."""

import pytest
import numpy as np
from pathlib import Path

from core.database import DatabaseManager
from core.database.models import Document
from core.embeddings import EmbeddingGenerator, SimilaritySearch


@pytest.mark.asyncio
class TestSearchIntegration:
    """Integration tests for search functionality."""
    
    async def test_vector_search_workflow(self, temp_dir):
        """Test complete vector search workflow."""
        # Setup database
        db_path = temp_dir / "vector_search_test.db"
        db_manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
        await db_manager.create_tables()
        
        try:
            # Create test documents
            documents = [
                "Machine learning algorithms can learn patterns from data automatically.",
                "Python is a popular programming language for data science and AI development.",
                "Neural networks are inspired by biological neurons in the brain.",
                "Database systems store and organize information for efficient retrieval."
            ]
            
            stored_docs = []
            for i, content in enumerate(documents):
                import hashlib
                doc = Document(
                    title=f"Document {i+1}",
                    content=content,
                    source_type="test",
                    source_path=f"/test/doc{i+1}.txt",
                    content_hash=hashlib.sha256(content.encode()).hexdigest()
                )
                stored_doc = await db_manager.create_document(doc)
                stored_docs.append(stored_doc)
            
            # Test similarity search setup
            similarity_search = SimilaritySearch(embedding_dimension=384)
            
            # Create mock embeddings (in real scenario, these would be generated)
            mock_embeddings = []
            for i in range(len(documents)):
                # Create distinctive embeddings for each document
                embedding = np.random.rand(384).astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)  # Normalize
                mock_embeddings.append(embedding)
                
                # Add to similarity search index
                similarity_search.add_embedding(
                    content_id=stored_docs[i].id,
                    embedding=embedding,
                    content_text=documents[i]
                )
            
            # Test similarity search
            query_embedding = mock_embeddings[0] + np.random.normal(0, 0.1, 384).astype(np.float32)
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            
            results = similarity_search.search(query_embedding, k=3, threshold=0.1)
            
            # Should find similar documents
            assert len(results) > 0
            assert all(isinstance(result.content_id, int) for result in results)
            assert all(0 <= result.score <= 1 for result in results)
            
            # Test database embedding storage
            await db_manager.update_document_embedding(stored_docs[0].id, mock_embeddings[0])
            
            # Retrieve and verify
            retrieved_doc = await db_manager.get_document(stored_docs[0].id)
            assert retrieved_doc.embedding_vector is not None
            
            retrieved_embedding = np.frombuffer(retrieved_doc.embedding_vector, dtype=np.float32)
            np.testing.assert_array_almost_equal(mock_embeddings[0], retrieved_embedding)
            
        finally:
            if db_path.exists():
                db_path.unlink()
    
    async def test_hybrid_search_simulation(self, temp_dir):
        """Simulate hybrid search combining full-text and vector search."""
        # Setup database
        db_path = temp_dir / "hybrid_search_test.db" 
        db_manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
        await db_manager.create_tables()
        
        try:
            # Create documents with searchable content
            test_docs = [
                {
                    "title": "AI Introduction",
                    "content": "Artificial intelligence and machine learning are revolutionizing technology. AI systems can process data and make decisions.",
                },
                {
                    "title": "Python Programming",
                    "content": "Python is excellent for machine learning development. Libraries like scikit-learn and TensorFlow make AI accessible.",
                },
                {
                    "title": "Database Systems",
                    "content": "Modern databases handle big data efficiently. NoSQL and SQL databases serve different use cases in data management.",
                },
                {
                    "title": "Web Development",
                    "content": "Full-stack web development involves frontend and backend technologies. JavaScript frameworks are popular for modern web apps.",
                }
            ]
            
            stored_docs = []
            for doc_data in test_docs:
                import hashlib
                doc = Document(
                    title=doc_data["title"],
                    content=doc_data["content"],
                    source_type="test",
                    source_path=f"/test/{doc_data['title'].lower().replace(' ', '_')}.txt",
                    content_hash=hashlib.sha256(doc_data["content"].encode()).hexdigest()
                )
                stored_doc = await db_manager.create_document(doc)
                stored_docs.append(stored_doc)
            
            # Test vector search component
            similarity_search = SimilaritySearch()
            
            for i, doc in enumerate(stored_docs):
                # Mock embedding based on content keywords
                embedding = np.random.rand(384).astype(np.float32)
                if "machine learning" in doc.content.lower():
                    embedding[:10] = 0.9  # High values for ML-related content
                elif "python" in doc.content.lower():
                    embedding[10:20] = 0.9  # High values for Python content  
                elif "database" in doc.content.lower():
                    embedding[20:30] = 0.9  # High values for database content
                
                embedding = embedding / np.linalg.norm(embedding)
                
                similarity_search.add_embedding(
                    content_id=doc.id,
                    embedding=embedding,
                    content_text=doc.content,
                    metadata={"title": doc.title, "source": doc.source_type}
                )
            
            # Test query for "machine learning"
            ml_query = np.zeros(384, dtype=np.float32)
            ml_query[:10] = 0.9  # Match ML-related pattern
            ml_query = ml_query / np.linalg.norm(ml_query)
            
            ml_results = similarity_search.search(ml_query, k=2, threshold=0.3)
            
            # Should prioritize ML-related documents
            assert len(ml_results) >= 1
            top_result = ml_results[0]
            assert "machine learning" in top_result.content.lower() or "AI" in top_result.content
            
            # Test metadata filtering
            test_results = similarity_search.search(
                ml_query, 
                k=5,
                threshold=0.1,
                filter_metadata={"source": "test"}
            )
            
            assert all(result.metadata["source"] == "test" for result in test_results)
            
        finally:
            if db_path.exists():
                db_path.unlink()
    
    async def test_search_performance_baseline(self, temp_dir):
        """Test search performance with larger dataset."""
        import time
        
        # Setup database
        db_path = temp_dir / "performance_test.db"
        db_manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
        await db_manager.create_tables()
        
        try:
            # Create larger dataset
            num_docs = 100
            documents = []
            
            base_contents = [
                "Machine learning algorithms process data to find patterns and make predictions.",
                "Python programming language offers excellent libraries for data science applications.",
                "Database systems manage information storage and retrieval for applications.",
                "Web development frameworks enable rapid creation of interactive applications.",
                "Artificial intelligence systems can automate complex decision-making processes."
            ]
            
            for i in range(num_docs):
                content = base_contents[i % len(base_contents)] + f" Document variation {i}."
                import hashlib
                doc = Document(
                    title=f"Performance Test Doc {i}",
                    content=content,
                    source_type="performance_test",
                    source_path=f"/test/perf_{i}.txt",
                    content_hash=hashlib.sha256(content.encode()).hexdigest()
                )
                documents.append(doc)
            
            # Measure insertion time
            start_time = time.time()
            stored_docs = []
            for doc in documents:
                stored_doc = await db_manager.create_document(doc)
                stored_docs.append(stored_doc)
            
            insertion_time = time.time() - start_time
            
            # Should be reasonably fast (less than 1 second for 100 docs)
            assert insertion_time < 10.0  # Generous threshold for CI environments
            
            # Test vector search performance
            similarity_search = SimilaritySearch()
            
            # Add embeddings
            start_time = time.time()
            for doc in stored_docs:
                embedding = np.random.rand(384).astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)
                similarity_search.add_embedding(doc.id, embedding, doc.content)
            
            indexing_time = time.time() - start_time
            assert indexing_time < 5.0  # Should be fast
            
            # Test search performance
            query_embedding = np.random.rand(384).astype(np.float32)
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            
            start_time = time.time()
            results = similarity_search.search(query_embedding, k=10)
            search_time = time.time() - start_time
            
            # Search should be very fast
            assert search_time < 1.0
            assert len(results) == 10
            
            # Test database retrieval performance
            start_time = time.time()
            all_docs = await db_manager.get_documents(limit=50)
            retrieval_time = time.time() - start_time
            
            assert retrieval_time < 1.0
            assert len(all_docs) == 50
            
        finally:
            if db_path.exists():
                db_path.unlink()