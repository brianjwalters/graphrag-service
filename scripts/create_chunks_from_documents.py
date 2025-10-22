#!/usr/bin/env python3
"""
Create chunks from law.documents and insert into graph.chunks.

This script:
1. Reads documents from law.documents
2. Chunks them into 4000-character segments with 200-char overlap
3. Inserts chunks into graph.chunks
4. Prepares data for embedding generation
"""

import asyncio
import sys
import uuid
from typing import List, Dict, Any

# Add project root to path for imports
sys.path.insert(0, '/srv/luris/be/graphrag-service')

from src.clients.supabase_client import create_supabase_client


class DocumentChunker:
    """Chunk documents and insert into graph.chunks."""

    def __init__(self, chunk_size: int = 4000, overlap: int = 200):
        """Initialize chunker with SupabaseClient."""
        self.supabase = create_supabase_client(service_name="document-chunker", use_service_role=True)
        self.chunk_size = chunk_size
        self.overlap = overlap

    def create_chunks(self, text: str, document_id: str) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.

        Args:
            text: Document text to chunk
            document_id: Source document identifier

        Returns:
            List of chunk dictionaries
        """
        if not text:
            return []

        chunks = []
        start_pos = 0
        chunk_index = 0

        while start_pos < len(text):
            # Calculate end position
            end_pos = min(start_pos + self.chunk_size, len(text))

            # Extract chunk
            chunk_text = text[start_pos:end_pos]

            # Create chunk dict
            chunk = {
                "id": str(uuid.uuid4()),
                "chunk_id": f"{document_id}-chunk-{chunk_index}",
                "document_id": document_id,
                "chunk_index": chunk_index,
                "content": chunk_text,
                "start_char": start_pos,
                "end_char": end_pos,
                "token_count": len(chunk_text) // 4,  # Rough estimate
                "metadata": {
                    "chunk_size": len(chunk_text),
                    "overlap_size": self.overlap
                }
            }

            chunks.append(chunk)

            # Move to next chunk with overlap
            if end_pos >= len(text):
                break

            start_pos = end_pos - self.overlap
            chunk_index += 1

        return chunks

    async def process_documents(self, limit: int = None) -> Dict[str, Any]:
        """
        Process documents and create chunks.

        Args:
            limit: Maximum number of documents to process

        Returns:
            Processing statistics
        """
        print(f"\n🚀 Processing documents from law.documents...")

        # Get documents with content
        query = self.supabase.schema('law').table('documents') \
            .select('id, document_id, title, content_md')

        if limit:
            query = query.limit(limit)

        docs_result = await query.execute()
        documents = docs_result.data

        # Filter documents with content
        documents = [d for d in documents if d.get('content_md')]

        print(f"  📝 Found {len(documents)} documents with content")

        if not documents:
            print("  ⚠️  No documents with content found")
            return {'processed': 0, 'chunks_created': 0, 'errors': 0}

        # Process documents
        total_chunks = 0
        processed_docs = 0
        errors = 0

        for i, doc in enumerate(documents, 1):
            try:
                # Create chunks
                chunks = self.create_chunks(
                    text=doc['content_md'],
                    document_id=doc['document_id']
                )

                if not chunks:
                    continue

                # Insert chunks in batches of 100
                batch_size = 100
                for j in range(0, len(chunks), batch_size):
                    batch = chunks[j:j + batch_size]

                    await self.supabase.schema('graph').table('chunks') \
                        .insert(batch) \
                        .execute()

                total_chunks += len(chunks)
                processed_docs += 1

                if i % 100 == 0:
                    print(f"  🔄 Processed {i}/{len(documents)} documents ({total_chunks} chunks created)")

            except Exception as e:
                print(f"  ⚠️  Error processing document {doc.get('document_id', 'unknown')}: {e}")
                errors += 1
                continue

        result = {
            'processed_docs': processed_docs,
            'total_documents': len(documents),
            'chunks_created': total_chunks,
            'errors': errors,
            'avg_chunks_per_doc': round(total_chunks / processed_docs, 2) if processed_docs > 0 else 0
        }

        print(f"\n  ✅ Document processing complete!")
        print(f"  📊 Documents processed: {result['processed_docs']}/{result['total_documents']}")
        print(f"  📦 Chunks created: {result['chunks_created']}")
        print(f"  ❌ Errors: {result['errors']}")
        print(f"  📈 Average chunks/doc: {result['avg_chunks_per_doc']}")

        return result

    async def check_state(self) -> Dict[str, Any]:
        """Check current state of chunks in database."""
        print("\n🔍 Checking chunk state...")

        # Count chunks
        chunks_result = await self.supabase.schema('graph').table('chunks') \
            .select('count', count='exact') \
            .execute()

        total_chunks = chunks_result.count

        # Count chunks with embeddings
        chunks_null = await self.supabase.schema('graph').table('chunks') \
            .select('count', count='exact') \
            .is_('content_embedding', 'null') \
            .execute()

        chunks_with_embeddings = total_chunks - chunks_null.count

        state = {
            'total_chunks': total_chunks,
            'chunks_with_embeddings': chunks_with_embeddings,
            'chunks_without_embeddings': total_chunks - chunks_with_embeddings
        }

        print(f"  ✅ Total chunks: {state['total_chunks']}")
        print(f"  📊 Chunks with embeddings: {state['chunks_with_embeddings']}")
        print(f"  ⚠️  Chunks without embeddings: {state['chunks_without_embeddings']}")

        return state

    async def run(self, doc_limit: int = None):
        """Run the complete chunking process."""
        print("=" * 80)
        print("🚀 Document Chunking for GraphRAG")
        print("=" * 80)

        # Check initial state
        initial_state = await self.check_state()

        # Process documents
        result = await self.process_documents(limit=doc_limit)

        # Check final state
        print("\n" + "=" * 80)
        final_state = await self.check_state()

        # Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"\n🎯 Chunking Results:")
        print(f"  • Documents processed: {result['processed_docs']}/{result['total_documents']}")
        print(f"  • Chunks created: {result['chunks_created']}")
        print(f"  • Errors: {result['errors']}")
        print(f"  • Average chunks/doc: {result['avg_chunks_per_doc']}")

        print(f"\n📦 Chunk State:")
        print(f"  • Before: {initial_state['total_chunks']} chunks")
        print(f"  • After: {final_state['total_chunks']} chunks")
        print(f"  • New chunks: {final_state['total_chunks'] - initial_state['total_chunks']}")

        print(f"\n🎯 Ready for Embedding Generation:")
        print(f"  • Chunks without embeddings: {final_state['chunks_without_embeddings']}")

        print("\n✅ Chunking complete!")
        print("=" * 80)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Create chunks from law.documents")
    parser.add_argument('--limit', type=int, help="Limit number of documents to process (for testing)")

    args = parser.parse_args()

    chunker = DocumentChunker()
    await chunker.run(doc_limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
