#!/usr/bin/env python3
"""
Generate real vector embeddings for document chunks and community summaries using vLLM.

This script:
1. Queries existing chunks from graph.chunks
2. Generates embeddings using vLLM Embeddings service (port 8081)
3. Stores embeddings back to the database
4. Generates embeddings for community summaries if they exist

Uses: Jina Embeddings v4 (512-dimensional vectors)
"""

import asyncio
import sys
import time
from typing import List, Dict, Any
from openai import OpenAI
import json

# Add project root to path for imports
sys.path.insert(0, '/srv/luris/be/graphrag-service')

from src.clients.supabase_client import create_supabase_client


class EmbeddingGenerator:
    """Generate embeddings for graph chunks and communities."""

    def __init__(self):
        """Initialize embedding generator with clients."""
        self.supabase = create_supabase_client(service_name="embedding-generator", use_service_role=True)

        # vLLM Embeddings client (OpenAI compatible)
        self.embeddings_client = OpenAI(
            base_url="http://localhost:8081/v1",
            api_key="not-needed"  # vLLM doesn't require auth
        )

        self.model_name = "jinaai/jina-embeddings-v4-vllm-code"
        self.batch_size = 32  # vLLM can handle 32 texts per batch

    async def check_database_state(self) -> Dict[str, Any]:
        """Check current state of chunks and communities."""
        print("\n🔍 Checking database state...")

        # Check chunks
        chunks_result = await self.supabase.schema('graph').table('chunks') \
            .select('count', count='exact') \
            .execute()

        total_chunks = chunks_result.count

        # Check how many have NULL embeddings
        chunks_null = await self.supabase.schema('graph').table('chunks') \
            .select('count', count='exact') \
            .is_('content_embedding', 'null') \
            .execute()

        chunks_with_embeddings = total_chunks - chunks_null.count

        # Check communities
        communities_result = await self.supabase.schema('graph').table('communities') \
            .select('count', count='exact') \
            .execute()

        total_communities = communities_result.count

        # Check communities with NULL embeddings
        comm_null = await self.supabase.schema('graph').table('communities') \
            .select('count', count='exact') \
            .is_('summary_embedding', 'null') \
            .execute()

        communities_with_embeddings = total_communities - comm_null.count

        state = {
            'total_chunks': total_chunks,
            'chunks_with_embeddings': chunks_with_embeddings,
            'chunks_without_embeddings': total_chunks - chunks_with_embeddings,
            'total_communities': total_communities,
            'communities_with_embeddings': communities_with_embeddings,
            'communities_without_embeddings': total_communities - communities_with_embeddings
        }

        print(f"  ✅ Total chunks: {state['total_chunks']}")
        print(f"  📊 Chunks with embeddings: {state['chunks_with_embeddings']}")
        print(f"  ⚠️  Chunks without embeddings: {state['chunks_without_embeddings']}")
        print(f"  ✅ Total communities: {state['total_communities']}")
        print(f"  📊 Communities with embeddings: {state['communities_with_embeddings']}")
        print(f"  ⚠️  Communities without embeddings: {state['communities_without_embeddings']}")

        return state

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts using vLLM service."""
        try:
            response = self.embeddings_client.embeddings.create(
                model=self.model_name,
                input=texts
            )

            # Extract embeddings from response
            embeddings = [emb.embedding for emb in response.data]
            return embeddings

        except Exception as e:
            print(f"  ❌ Error generating embeddings: {e}")
            raise

    async def generate_chunk_embeddings(self, limit: int = None) -> Dict[str, Any]:
        """Generate embeddings for chunks without embeddings."""
        print("\n🚀 Generating chunk embeddings...")

        # Get chunks without embeddings
        query = self.supabase.schema('graph').table('chunks') \
            .select('id, chunk_id, content, enhanced_content') \
            .is_('content_embedding', 'null')

        if limit:
            query = query.limit(limit)

        chunks_result = await query.execute()
        chunks = chunks_result.data

        if not chunks:
            print("  ℹ️  No chunks without embeddings found")
            return {'processed': 0, 'errors': 0}

        print(f"  📝 Found {len(chunks)} chunks without embeddings")

        # Process in batches
        processed = 0
        errors = 0
        start_time = time.time()

        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(chunks) + self.batch_size - 1) // self.batch_size

            print(f"  🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

            try:
                # Prepare texts (use enhanced_content if available, else content)
                texts = [
                    chunk['enhanced_content'] if chunk.get('enhanced_content') else chunk['content']
                    for chunk in batch
                ]

                # Generate embeddings
                embeddings = self.generate_embeddings_batch(texts)

                # Update database
                for chunk, embedding in zip(batch, embeddings):
                    try:
                        await self.supabase.schema('graph').table('chunks') \
                            .update({
                                'content_embedding': embedding,
                                'embedding_model': self.model_name
                            }) \
                            .eq('id', chunk['id']) \
                            .execute()

                        processed += 1

                    except Exception as e:
                        print(f"  ⚠️  Error updating chunk {chunk['chunk_id']}: {e}")
                        errors += 1

                print(f"  ✅ Batch {batch_num} complete ({processed} total)")

            except Exception as e:
                print(f"  ❌ Error processing batch {batch_num}: {e}")
                errors += len(batch)
                continue

        elapsed = time.time() - start_time

        result = {
            'processed': processed,
            'errors': errors,
            'elapsed_seconds': round(elapsed, 2),
            'chunks_per_second': round(processed / elapsed, 2) if elapsed > 0 else 0
        }

        print(f"\n  ✅ Chunk embedding generation complete!")
        print(f"  📊 Processed: {result['processed']}")
        print(f"  ❌ Errors: {result['errors']}")
        print(f"  ⏱️  Time: {result['elapsed_seconds']}s")
        print(f"  🚀 Speed: {result['chunks_per_second']} chunks/sec")

        return result

    async def generate_community_embeddings(self) -> Dict[str, Any]:
        """Generate embeddings for community summaries."""
        print("\n🚀 Generating community embeddings...")

        # Get communities without embeddings (summary_embedding IS NULL AND summary IS NOT NULL)
        # We'll filter for non-null summary in Python since PostgREST syntax is tricky
        communities_result = await self.supabase.schema('graph').table('communities') \
            .select('id, community_id, summary, summary_embedding') \
            .execute()

        # Filter: has summary but no embedding
        communities = [
            c for c in communities_result.data
            if c.get('summary') is not None and c.get('summary_embedding') is None
        ]

        if not communities:
            print("  ℹ️  No communities without embeddings found")
            return {'processed': 0, 'errors': 0}

        print(f"  📝 Found {len(communities)} communities without embeddings")

        # Process in batches
        processed = 0
        errors = 0
        start_time = time.time()

        for i in range(0, len(communities), self.batch_size):
            batch = communities[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(communities) + self.batch_size - 1) // self.batch_size

            print(f"  🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} communities)...")

            try:
                # Prepare summaries
                summaries = [comm['summary'] for comm in batch]

                # Generate embeddings
                embeddings = self.generate_embeddings_batch(summaries)

                # Update database
                for community, embedding in zip(batch, embeddings):
                    try:
                        await self.supabase.schema('graph').table('communities') \
                            .update({
                                'summary_embedding': embedding,
                                'embedding_model': self.model_name
                            }) \
                            .eq('id', community['id']) \
                            .execute()

                        processed += 1

                    except Exception as e:
                        print(f"  ⚠️  Error updating community {community['community_id']}: {e}")
                        errors += 1

                print(f"  ✅ Batch {batch_num} complete ({processed} total)")

            except Exception as e:
                print(f"  ❌ Error processing batch {batch_num}: {e}")
                errors += len(batch)
                continue

        elapsed = time.time() - start_time

        result = {
            'processed': processed,
            'errors': errors,
            'elapsed_seconds': round(elapsed, 2),
            'communities_per_second': round(processed / elapsed, 2) if elapsed > 0 else 0
        }

        print(f"\n  ✅ Community embedding generation complete!")
        print(f"  📊 Processed: {result['processed']}")
        print(f"  ❌ Errors: {result['errors']}")
        print(f"  ⏱️  Time: {result['elapsed_seconds']}s")
        print(f"  🚀 Speed: {result['communities_per_second']} communities/sec")

        return result

    async def get_sample_embedding(self) -> Dict[str, Any]:
        """Get a sample embedding to verify dimensions and format."""
        print("\n🔍 Fetching sample embedding...")

        # Get one chunk with embedding (check for non-null by getting all and filtering)
        result = await self.supabase.schema('graph').table('chunks') \
            .select('chunk_id, content_embedding') \
            .limit(100) \
            .execute()

        # Find first chunk with non-null embedding
        chunk_with_emb = next((c for c in result.data if c.get('content_embedding') is not None), None)

        if not chunk_with_emb:
            print("  ⚠️  No embeddings found yet")
            return None

        chunk = chunk_with_emb
        embedding = chunk['content_embedding']

        sample = {
            'chunk_id': chunk['chunk_id'],
            'embedding_dimensions': len(embedding),
            'first_10_dimensions': embedding[:10],
            'embedding_model': self.model_name
        }

        print(f"  ✅ Sample embedding retrieved")
        print(f"  📊 Dimensions: {sample['embedding_dimensions']}")
        print(f"  🔢 First 10 values: {[round(v, 6) for v in sample['first_10_dimensions']]}")

        return sample

    async def run(self, chunk_limit: int = None):
        """Run the complete embedding generation process."""
        print("=" * 80)
        print("🚀 Vector Embedding Generation for GraphRAG")
        print("=" * 80)

        # Check initial state
        initial_state = await self.check_database_state()

        # Generate chunk embeddings
        if initial_state['chunks_without_embeddings'] > 0:
            chunk_results = await self.generate_chunk_embeddings(limit=chunk_limit)
        else:
            chunk_results = {'processed': 0, 'errors': 0}
            print("\n  ℹ️  All chunks already have embeddings")

        # Generate community embeddings
        if initial_state['communities_without_embeddings'] > 0:
            community_results = await self.generate_community_embeddings()
        else:
            community_results = {'processed': 0, 'errors': 0}
            print("\n  ℹ️  All communities already have embeddings")

        # Check final state
        print("\n" + "=" * 80)
        final_state = await self.check_database_state()

        # Get sample embedding
        sample = await self.get_sample_embedding()

        # Summary
        print("\n" + "=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"\n🎯 Chunk Embeddings:")
        print(f"  • Processed: {chunk_results['processed']}")
        print(f"  • Errors: {chunk_results['errors']}")
        print(f"  • Before: {initial_state['chunks_with_embeddings']}/{initial_state['total_chunks']}")
        print(f"  • After: {final_state['chunks_with_embeddings']}/{final_state['total_chunks']}")

        print(f"\n🎯 Community Embeddings:")
        print(f"  • Processed: {community_results['processed']}")
        print(f"  • Errors: {community_results['errors']}")
        print(f"  • Before: {initial_state['communities_with_embeddings']}/{initial_state['total_communities']}")
        print(f"  • After: {final_state['communities_with_embeddings']}/{final_state['total_communities']}")

        if sample:
            print(f"\n📐 Embedding Details:")
            print(f"  • Model: {sample['embedding_model']}")
            print(f"  • Dimensions: {sample['embedding_dimensions']}")
            print(f"  • Sample values: {[round(v, 6) for v in sample['first_10_dimensions']]}")

        print("\n✅ Embedding generation complete!")
        print("=" * 80)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate vector embeddings for GraphRAG")
    parser.add_argument('--limit', type=int, help="Limit number of chunks to process (for testing)")

    args = parser.parse_args()

    generator = EmbeddingGenerator()
    await generator.run(chunk_limit=args.limit)


if __name__ == "__main__":
    asyncio.run(main())
