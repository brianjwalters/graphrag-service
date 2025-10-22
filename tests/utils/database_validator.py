"""
Database Validator for GraphRAG E2E Testing

Validates all graph schema tables using SupabaseClient with proper
admin_operation access patterns.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from uuid import UUID

# Add graphrag-service to path for imports
graphrag_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(graphrag_path))

from clients.supabase_client import create_admin_supabase_client


@dataclass
class ValidationResult:
    """Result of a database table validation."""
    table_name: str
    passed: bool
    row_count: int
    expected_min: int
    expected_max: Optional[int] = None
    message: str = ""
    sample_data: Optional[List[Dict]] = None


class DatabaseValidator:
    """
    Validates GraphRAG database tables using SupabaseClient.

    All database access uses create_admin_supabase_client() with
    admin_operation=True to bypass RLS policies.
    """

    def __init__(self, client_id: UUID, case_id: UUID):
        """
        Initialize validator with test tenant IDs.

        Args:
            client_id: Test client UUID
            case_id: Test case UUID
        """
        self.client_id = str(client_id)
        self.case_id = str(case_id)
        self.supabase = create_admin_supabase_client("graphrag-e2e-test")
        self.results: List[ValidationResult] = []

    async def validate_nodes(self, expected_min: int = 50) -> ValidationResult:
        """
        Validate graph.nodes table.

        Args:
            expected_min: Minimum expected entity nodes

        Returns:
            ValidationResult with validation details
        """
        print(f"\n📊 Validating graph.nodes (expect ≥{expected_min} entities)...")

        try:
            # Query nodes with UUID filtering
            nodes = await self.supabase.get(
                "graph.nodes",
                filters={"client_id": self.client_id},
                limit=1000,
                admin_operation=True
            )

            row_count = len(nodes)
            passed = row_count >= expected_min

            # Get sample data
            sample = nodes[:5] if nodes else []

            # Validate UUID columns populated
            uuid_populated = all(node.get("client_id") for node in nodes)

            result = ValidationResult(
                table_name="graph.nodes",
                passed=passed and uuid_populated,
                row_count=row_count,
                expected_min=expected_min,
                message=f"{'✅' if passed else '❌'} Found {row_count} nodes (expected ≥{expected_min}). UUID columns: {'✅' if uuid_populated else '❌'}",
                sample_data=sample
            )

            print(f"  {result.message}")
            if sample:
                print(f"  Sample: {sample[0].get('name', 'N/A')} (type: {sample[0].get('node_type', 'N/A')})")

            self.results.append(result)
            return result

        except Exception as e:
            result = ValidationResult(
                table_name="graph.nodes",
                passed=False,
                row_count=0,
                expected_min=expected_min,
                message=f"❌ Error validating nodes: {str(e)}"
            )
            print(f"  {result.message}")
            self.results.append(result)
            return result

    async def validate_edges(self, expected_min: int = 100) -> ValidationResult:
        """
        Validate graph.edges table.

        Args:
            expected_min: Minimum expected relationships

        Returns:
            ValidationResult
        """
        print(f"\n📊 Validating graph.edges (expect ≥{expected_min} relationships)...")

        try:
            edges = await self.supabase.get(
                "graph.edges",
                filters={"client_id": self.client_id},
                limit=1000,
                admin_operation=True
            )

            row_count = len(edges)
            passed = row_count >= expected_min

            sample = edges[:5] if edges else []

            result = ValidationResult(
                table_name="graph.edges",
                passed=passed,
                row_count=row_count,
                expected_min=expected_min,
                message=f"{'✅' if passed else '❌'} Found {row_count} edges (expected ≥{expected_min})",
                sample_data=sample
            )

            print(f"  {result.message}")
            if sample:
                print(f"  Sample: {sample[0].get('relationship_type', 'N/A')}")

            self.results.append(result)
            return result

        except Exception as e:
            result = ValidationResult(
                table_name="graph.edges",
                passed=False,
                row_count=0,
                expected_min=expected_min,
                message=f"❌ Error validating edges: {str(e)}"
            )
            print(f"  {result.message}")
            self.results.append(result)
            return result

    async def validate_communities(self, expected_min: int = 3, expected_max: int = 10) -> ValidationResult:
        """
        Validate graph.communities table (Leiden clustering).

        Args:
            expected_min: Minimum expected communities
            expected_max: Maximum expected communities

        Returns:
            ValidationResult
        """
        print(f"\n📊 Validating graph.communities (expect {expected_min}-{expected_max} communities)...")

        try:
            communities = await self.supabase.get(
                "graph.communities",
                filters={"client_id": self.client_id},
                limit=100,
                admin_operation=True
            )

            row_count = len(communities)
            passed = expected_min <= row_count <= expected_max

            sample = communities[:3] if communities else []

            result = ValidationResult(
                table_name="graph.communities",
                passed=passed,
                row_count=row_count,
                expected_min=expected_min,
                expected_max=expected_max,
                message=f"{'✅' if passed else '❌'} Found {row_count} communities (expected {expected_min}-{expected_max})",
                sample_data=sample
            )

            print(f"  {result.message}")
            if sample:
                print(f"  Sample: Community {sample[0].get('id', 'N/A')} (level: {sample[0].get('level', 'N/A')})")

            self.results.append(result)
            return result

        except Exception as e:
            result = ValidationResult(
                table_name="graph.communities",
                passed=False,
                row_count=0,
                expected_min=expected_min,
                expected_max=expected_max,
                message=f"❌ Error validating communities: {str(e)}"
            )
            print(f"  {result.message}")
            self.results.append(result)
            return result

    async def validate_chunk_entity_connections(self, expected_min: int = 100) -> ValidationResult:
        """
        Validate graph.chunk_entity_connections table (NEW FEATURE).

        Args:
            expected_min: Minimum expected connections

        Returns:
            ValidationResult
        """
        print(f"\n📊 Validating graph.chunk_entity_connections (expect ≥{expected_min} connections)...")

        try:
            connections = await self.supabase.get(
                "graph.chunk_entity_connections",
                filters={"client_id": self.client_id},
                limit=1000,
                admin_operation=True
            )

            row_count = len(connections)
            passed = row_count >= expected_min

            # Validate relevance scores
            relevance_scores = [c.get("relevance_score", 0) for c in connections]
            avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

            sample = connections[:5] if connections else []

            result = ValidationResult(
                table_name="graph.chunk_entity_connections",
                passed=passed,
                row_count=row_count,
                expected_min=expected_min,
                message=f"{'✅' if passed else '❌'} Found {row_count} connections (expected ≥{expected_min}). Avg relevance: {avg_relevance:.3f}",
                sample_data=sample
            )

            print(f"  {result.message}")
            if sample:
                print(f"  Sample: Chunk {sample[0].get('chunk_id', 'N/A')[:8]}... → Entity {sample[0].get('entity_id', 'N/A')[:8]}... (score: {sample[0].get('relevance_score', 0):.3f})")

            self.results.append(result)
            return result

        except Exception as e:
            result = ValidationResult(
                table_name="graph.chunk_entity_connections",
                passed=False,
                row_count=0,
                expected_min=expected_min,
                message=f"❌ Error validating chunk_entity_connections: {str(e)}"
            )
            print(f"  {result.message}")
            self.results.append(result)
            return result

    async def validate_chunk_cross_references(self, expected_min: int = 20) -> ValidationResult:
        """
        Validate graph.chunk_cross_references table (NEW FEATURE).

        Args:
            expected_min: Minimum expected cross-references

        Returns:
            ValidationResult
        """
        print(f"\n📊 Validating graph.chunk_cross_references (expect ≥{expected_min} cross-refs)...")

        try:
            cross_refs = await self.supabase.get(
                "graph.chunk_cross_references",
                filters={"source_client_id": self.client_id},
                limit=500,
                admin_operation=True
            )

            row_count = len(cross_refs)
            passed = row_count >= expected_min

            # Analyze reference types
            citation_refs = sum(1 for r in cross_refs if r.get("reference_type") == "citation")
            semantic_refs = sum(1 for r in cross_refs if r.get("reference_type") == "semantic_similarity")

            sample = cross_refs[:5] if cross_refs else []

            result = ValidationResult(
                table_name="graph.chunk_cross_references",
                passed=passed,
                row_count=row_count,
                expected_min=expected_min,
                message=f"{'✅' if passed else '❌'} Found {row_count} cross-refs (expected ≥{expected_min}). Citations: {citation_refs}, Semantic: {semantic_refs}",
                sample_data=sample
            )

            print(f"  {result.message}")
            if sample:
                print(f"  Sample: {sample[0].get('source_chunk_id', 'N/A')[:8]}... → {sample[0].get('target_chunk_id', 'N/A')[:8]}... ({sample[0].get('reference_type', 'N/A')})")

            self.results.append(result)
            return result

        except Exception as e:
            result = ValidationResult(
                table_name="graph.chunk_cross_references",
                passed=False,
                row_count=0,
                expected_min=expected_min,
                message=f"❌ Error validating chunk_cross_references: {str(e)}"
            )
            print(f"  {result.message}")
            self.results.append(result)
            return result

    async def validate_embeddings(self, expected_min: int = 30, expected_dimensions: int = 2048) -> ValidationResult:
        """
        Validate graph.embeddings table (Jina v4 2048-dim).

        Args:
            expected_min: Minimum expected embeddings
            expected_dimensions: Expected embedding dimensions

        Returns:
            ValidationResult
        """
        print(f"\n📊 Validating graph.embeddings (expect ≥{expected_min} embeddings, {expected_dimensions}-dim)...")

        try:
            embeddings = await self.supabase.get(
                "graph.embeddings",
                filters={"client_id": self.client_id},
                limit=100,
                admin_operation=True
            )

            row_count = len(embeddings)
            passed = row_count >= expected_min

            # Validate embedding dimensions
            if embeddings:
                first_embedding = embeddings[0].get("embedding", [])
                actual_dimensions = len(first_embedding) if isinstance(first_embedding, list) else 0
                dimensions_match = actual_dimensions == expected_dimensions
            else:
                dimensions_match = False
                actual_dimensions = 0

            sample = embeddings[:3] if embeddings else []

            result = ValidationResult(
                table_name="graph.embeddings",
                passed=passed and dimensions_match,
                row_count=row_count,
                expected_min=expected_min,
                message=f"{'✅' if passed and dimensions_match else '❌'} Found {row_count} embeddings (expected ≥{expected_min}). Dimensions: {actual_dimensions}/{expected_dimensions}",
                sample_data=sample
            )

            print(f"  {result.message}")

            self.results.append(result)
            return result

        except Exception as e:
            result = ValidationResult(
                table_name="graph.embeddings",
                passed=False,
                row_count=0,
                expected_min=expected_min,
                message=f"❌ Error validating embeddings: {str(e)}"
            )
            print(f"  {result.message}")
            self.results.append(result)
            return result

    async def validate_contextual_chunks(self, expected_min: int = 30) -> ValidationResult:
        """
        Validate graph.contextual_chunks table.

        Args:
            expected_min: Minimum expected chunks

        Returns:
            ValidationResult
        """
        print(f"\n📊 Validating graph.contextual_chunks (expect ≥{expected_min} chunks)...")

        try:
            chunks = await self.supabase.get(
                "graph.contextual_chunks",
                filters={"client_id": self.client_id},
                limit=100,
                admin_operation=True
            )

            row_count = len(chunks)
            passed = row_count >= expected_min

            # Check for contextual wrapping
            contextual_count = sum(1 for c in chunks if c.get("contextual_text"))

            sample = chunks[:3] if chunks else []

            result = ValidationResult(
                table_name="graph.contextual_chunks",
                passed=passed,
                row_count=row_count,
                expected_min=expected_min,
                message=f"{'✅' if passed else '❌'} Found {row_count} chunks (expected ≥{expected_min}). Contextual: {contextual_count}/{row_count}",
                sample_data=sample
            )

            print(f"  {result.message}")
            if sample:
                chunk_text = sample[0].get("chunk_text", "")
                print(f"  Sample: {chunk_text[:100]}..." if len(chunk_text) > 100 else f"  Sample: {chunk_text}")

            self.results.append(result)
            return result

        except Exception as e:
            result = ValidationResult(
                table_name="graph.contextual_chunks",
                passed=False,
                row_count=0,
                expected_min=expected_min,
                message=f"❌ Error validating contextual_chunks: {str(e)}"
            )
            print(f"  {result.message}")
            self.results.append(result)
            return result

    async def validate_all_tables(self) -> bool:
        """
        Run all table validations.

        Returns:
            True if all validations passed, False otherwise
        """
        print("\n" + "=" * 80)
        print("DATABASE VALIDATION")
        print("=" * 80)

        # Run all validations
        await self.validate_nodes(expected_min=50)
        await self.validate_edges(expected_min=100)
        await self.validate_communities(expected_min=3, expected_max=10)
        await self.validate_chunk_entity_connections(expected_min=100)
        await self.validate_chunk_cross_references(expected_min=20)
        await self.validate_embeddings(expected_min=30, expected_dimensions=2048)
        await self.validate_contextual_chunks(expected_min=30)

        # Print summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        all_passed = passed_count == total_count

        print(f"Overall: {'✅ ALL VALIDATIONS PASSED' if all_passed else '❌ SOME VALIDATIONS FAILED'}")
        print(f"Passed: {passed_count}/{total_count}")

        if not all_passed:
            print("\n❌ FAILED VALIDATIONS:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.table_name}: {r.message}")

        print("=" * 80)

        return all_passed

    def get_summary_dict(self) -> Dict[str, Any]:
        """
        Get summary dictionary for reporting.

        Returns:
            Dictionary with validation summary
        """
        return {
            "total_tables": len(self.results),
            "passed_tables": sum(1 for r in self.results if r.passed),
            "failed_tables": sum(1 for r in self.results if not r.passed),
            "all_passed": all(r.passed for r in self.results),
            "total_rows": sum(r.row_count for r in self.results),
            "validations": [
                {
                    "table": r.table_name,
                    "passed": r.passed,
                    "row_count": r.row_count,
                    "expected_min": r.expected_min,
                    "expected_max": r.expected_max,
                    "message": r.message
                }
                for r in self.results
            ]
        }
