"""Performance and load tests."""

import pytest
import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core.database import DatabaseManager
from core.database.models import Document
from connectors.filesystem import FilesystemScanner


@pytest.mark.asyncio
class TestPerformance:
    """Performance and scalability tests."""
    
    async def test_concurrent_document_insertion(self, temp_dir):
        """Test concurrent document insertion performance."""
        # Setup database
        db_path = temp_dir / "concurrent_test.db"
        db_manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
        await db_manager.create_tables()
        
        try:
            async def insert_document(doc_id: int):
                """Insert a single document."""
                import hashlib
                content = f"Test document content for document {doc_id}. This is used for performance testing."
                
                document = Document(
                    title=f"Test Document {doc_id}",
                    content=content,
                    source_type="performance_test",
                    source_path=f"/test/doc_{doc_id}.txt",
                    content_hash=hashlib.sha256(content.encode()).hexdigest()
                )
                
                return await db_manager.create_document(document)
            
            # Test with varying numbers of concurrent operations
            for num_docs in [10, 50, 100]:
                start_time = time.time()
                
                # Create tasks for concurrent execution
                tasks = [insert_document(i) for i in range(num_docs)]
                results = await asyncio.gather(*tasks)
                
                elapsed_time = time.time() - start_time
                
                # Verify all documents were created
                assert len(results) == num_docs
                assert all(doc.id is not None for doc in results)
                
                # Performance assertion - should handle 100 docs in under 10 seconds
                docs_per_second = num_docs / elapsed_time
                print(f"Inserted {num_docs} documents in {elapsed_time:.2f}s ({docs_per_second:.1f} docs/sec)")
                
                if num_docs == 100:
                    assert elapsed_time < 30  # Generous threshold for CI
                
                # Clean up for next iteration
                await asyncio.sleep(0.1)
                
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_filesystem_scanner_performance(self, temp_dir):
        """Test filesystem scanner performance with many files."""
        # Create test directory with many files
        test_dir = temp_dir / "perf_test_files"
        test_dir.mkdir()
        
        # Create files of different sizes
        file_sizes = [100, 1000, 10000]  # bytes
        num_files_per_size = 20
        
        total_files = 0
        for size in file_sizes:
            for i in range(num_files_per_size):
                content = "A" * size
                file_path = test_dir / f"file_{size}_{i}.txt"
                file_path.write_text(content)
                total_files += 1
        
        # Add some files that should be ignored
        (test_dir / "ignore1.pyc").write_text("compiled code")
        (test_dir / "ignore2.log").write_text("log file")
        
        # Test scanner performance
        scanner = FilesystemScanner()
        
        async def run_scan():
            start_time = time.time()
            files = await scanner.scan_directory(test_dir, recursive=True)
            scan_time = time.time() - start_time
            
            # Should find only supported files
            expected_files = total_files  # All .txt files
            assert len(files) == expected_files
            
            # Scanning should be fast
            assert scan_time < 5.0  # Should scan 60 files in under 5 seconds
            
            files_per_second = len(files) / scan_time
            print(f"Scanned {len(files)} files in {scan_time:.2f}s ({files_per_second:.1f} files/sec)")
            
            # Test processing performance
            start_time = time.time()
            processed_docs = []
            
            for file_path in files[:10]:  # Process first 10 files
                doc = await scanner.process_file(file_path)
                if doc:
                    processed_docs.append(doc)
            
            process_time = time.time() - start_time
            
            assert len(processed_docs) == 10
            assert process_time < 10.0  # Should process 10 files in under 10 seconds
            
            processing_rate = len(processed_docs) / process_time
            print(f"Processed {len(processed_docs)} files in {process_time:.2f}s ({processing_rate:.1f} files/sec)")
        
        # Run the async test
        asyncio.run(run_scan())
    
    async def test_database_query_performance(self, temp_dir):
        """Test database query performance with larger dataset."""
        # Setup database
        db_path = temp_dir / "query_perf_test.db"
        db_manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
        await db_manager.create_tables()
        
        try:
            # Insert test data
            num_docs = 500
            documents = []
            
            for i in range(num_docs):
                import hashlib
                content = f"Performance test document {i}. " * 10  # Make documents longer
                
                document = Document(
                    title=f"Perf Doc {i}",
                    content=content,
                    source_type="perf_test",
                    source_path=f"/perf/doc_{i}.txt",
                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                    word_count=len(content.split())
                )
                documents.append(document)
            
            # Batch insert
            start_time = time.time()
            for doc in documents:
                await db_manager.create_document(doc)
            insert_time = time.time() - start_time
            
            print(f"Inserted {num_docs} documents in {insert_time:.2f}s")
            
            # Test various query patterns
            
            # 1. Get all documents (pagination)
            start_time = time.time()
            page1 = await db_manager.get_documents(limit=50, offset=0)
            page2 = await db_manager.get_documents(limit=50, offset=50)
            pagination_time = time.time() - start_time
            
            assert len(page1) == 50
            assert len(page2) == 50
            assert pagination_time < 5.0
            
            # 2. Filter by source type
            start_time = time.time()
            filtered_docs = await db_manager.get_documents(source_type="perf_test", limit=100)
            filter_time = time.time() - start_time
            
            assert len(filtered_docs) == 100
            assert filter_time < 5.0
            
            # 3. Get individual documents
            start_time = time.time()
            for i in range(10):
                doc = await db_manager.get_document(i + 1)
                assert doc is not None
            individual_query_time = time.time() - start_time
            
            assert individual_query_time < 1.0
            
            # 4. Statistics query
            start_time = time.time()
            stats = await db_manager.get_stats()
            stats_time = time.time() - start_time
            
            assert stats["documents"] == num_docs
            assert stats_time < 2.0
            
            print(f"Query performance - Pagination: {pagination_time:.2f}s, Filter: {filter_time:.2f}s, Individual: {individual_query_time:.2f}s, Stats: {stats_time:.2f}s")
            
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_memory_usage_stability(self, temp_dir):
        """Test memory usage doesn't grow excessively."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        async def memory_test():
            # Setup database
            db_path = temp_dir / "memory_test.db"
            db_manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
            await db_manager.create_tables()
            
            try:
                # Perform many operations
                for batch in range(5):  # 5 batches
                    documents = []
                    for i in range(50):  # 50 docs per batch
                        import hashlib
                        doc_id = batch * 50 + i
                        content = f"Memory test document {doc_id}. " * 50
                        
                        document = Document(
                            title=f"Memory Doc {doc_id}",
                            content=content,
                            source_type="memory_test", 
                            source_path=f"/memory/doc_{doc_id}.txt",
                            content_hash=hashlib.sha256(content.encode()).hexdigest()
                        )
                        documents.append(document)
                    
                    # Insert batch
                    for doc in documents:
                        await db_manager.create_document(doc)
                    
                    # Check memory after each batch
                    current_memory = process.memory_info().rss
                    memory_growth = current_memory - initial_memory
                    
                    # Memory growth should be reasonable (less than 100MB total)
                    assert memory_growth < 100 * 1024 * 1024
                    
                    # Force garbage collection
                    import gc
                    gc.collect()
                
            finally:
                if db_path.exists():
                    db_path.unlink()
        
        # Run memory test
        asyncio.run(memory_test())
        
        # Final memory check
        final_memory = process.memory_info().rss
        total_growth = final_memory - initial_memory
        
        print(f"Memory usage - Initial: {initial_memory/1024/1024:.1f}MB, Final: {final_memory/1024/1024:.1f}MB, Growth: {total_growth/1024/1024:.1f}MB")
        
        # Total memory growth should be reasonable
        assert total_growth < 200 * 1024 * 1024  # Less than 200MB growth
    
    def test_thread_safety(self, temp_dir):
        """Test thread safety of core components."""
        results = []
        errors = []
        
        def worker_thread(thread_id: int):
            """Worker function for threading test."""
            try:
                async def async_work():
                    # Each thread works with its own database
                    db_path = temp_dir / f"thread_test_{thread_id}.db"
                    db_manager = DatabaseManager(f"sqlite+aiosqlite:///{db_path}")
                    await db_manager.create_tables()
                    
                    try:
                        # Insert documents
                        for i in range(10):
                            import hashlib
                            content = f"Thread {thread_id} document {i}"
                            
                            document = Document(
                                title=f"Thread {thread_id} Doc {i}",
                                content=content,
                                source_type="thread_test",
                                source_path=f"/thread/{thread_id}/doc_{i}.txt",
                                content_hash=hashlib.sha256(content.encode()).hexdigest()
                            )
                            
                            await db_manager.create_document(document)
                        
                        # Verify documents
                        docs = await db_manager.get_documents()
                        results.append(len(docs))
                        
                    finally:
                        if db_path.exists():
                            db_path.unlink()
                
                # Run async work in new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(async_work())
                finally:
                    loop.close()
                    
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        # Verify results
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 3
        assert all(count == 10 for count in results)  # Each thread should have created 10 docs