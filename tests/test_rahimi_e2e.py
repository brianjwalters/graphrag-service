"""
End-to-End GraphRAG Test with Rahimi.pdf

Comprehensive 7-stage test of the complete document processing pipeline:
1. Service Health Check (systemctl verification)
2. Document Upload
3. Entity Extraction
4. Smart Chunking
5. GraphRAG Construction
6. Database Validation
7. Performance Benchmarking

All database access uses SupabaseClient with admin_operation=True.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import httpx

# Add utils to path
utils_path = Path(__file__).parent / "utils"
sys.path.insert(0, str(utils_path))

from service_health_checker import ServiceHealthChecker
from database_validator import DatabaseValidator
from performance_analyzer import PerformanceAnalyzer
from report_generator import ReportGenerator, E2ETestReport


class PipelineTestHarness:
    """
    Orchestrates the complete E2E test pipeline for GraphRAG service.

    Tests the full document processing workflow from upload through
    knowledge graph construction with comprehensive validation.
    """

    # Test Configuration
    TEST_DOCUMENT = Path("/srv/luris/be/entity-extraction-service/tests/docs/Rahimi.pdf")
    TEST_CLIENT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
    TEST_CASE_ID = UUID("660e8400-e29b-41d4-a716-446655440001")
    OUTPUT_DIR = Path("/srv/luris/be/graphrag-service/tests/results")

    # Service Endpoints
    DOCUMENT_UPLOAD_URL = "http://localhost:8008/api/v1/documents/upload"
    ENTITY_EXTRACTION_URL = "http://localhost:8007/api/v1/extract/ai"
    CHUNKING_URL = "http://localhost:8009/api/v1/chunk/smart"
    GRAPHRAG_URL = "http://localhost:8010/api/v1/graph/create"

    def __init__(self):
        """Initialize test harness."""
        self.test_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.stage_results: list = []
        self.document_id: Optional[str] = None

        # Initialize utilities
        self.service_checker = ServiceHealthChecker()
        self.db_validator = DatabaseValidator(self.TEST_CLIENT_ID, self.TEST_CASE_ID)
        self.perf_analyzer = PerformanceAnalyzer(self.TEST_CLIENT_ID, self.TEST_CASE_ID, iterations=20)
        self.report_generator = ReportGenerator(self.OUTPUT_DIR)

        # HTTP client
        self.http_client = httpx.AsyncClient(timeout=300.0)

    async def cleanup(self):
        """Cleanup resources."""
        await self.http_client.aclose()

    def _record_stage_result(self, stage_number: int, stage_name: str, passed: bool,
                             duration: float, details: str = ""):
        """
        Record result of a test stage.

        Args:
            stage_number: Stage number (1-7)
            stage_name: Human-readable stage name
            passed: Whether stage passed
            duration: Duration in seconds
            details: Additional details
        """
        result = {
            "stage_number": stage_number,
            "stage_name": stage_name,
            "passed": passed,
            "status": "PASSED" if passed else "FAILED",
            "duration_seconds": duration,
            "details": details
        }
        self.stage_results.append(result)

        status_icon = "✅" if passed else "❌"
        print(f"\n{status_icon} Stage {stage_number}: {stage_name} - {result['status']} ({duration:.2f}s)")
        if details:
            print(f"   Details: {details}")

    async def stage_0_service_health(self) -> bool:
        """
        Stage 0: Verify all services are running via systemctl.

        Returns:
            True if all services healthy, False otherwise
        """
        print("\n" + "=" * 80)
        print("STAGE 0: SERVICE HEALTH CHECK")
        print("=" * 80)

        start = time.time()
        all_healthy, results = await self.service_checker.check_all_services()
        duration = time.time() - start

        self._record_stage_result(
            stage_number=0,
            stage_name="Service Health Check (systemctl)",
            passed=all_healthy,
            duration=duration,
            details=f"{results.get('healthy_services', 0)}/{results.get('total_services', 0)} services healthy"
        )

        return all_healthy

    async def stage_1_document_upload(self) -> bool:
        """
        Stage 1: Upload Rahimi.pdf to Document Upload Service.

        Returns:
            True if upload successful, False otherwise
        """
        print("\n" + "=" * 80)
        print("STAGE 1: DOCUMENT UPLOAD")
        print("=" * 80)

        if not self.TEST_DOCUMENT.exists():
            print(f"❌ Test document not found: {self.TEST_DOCUMENT}")
            self._record_stage_result(1, "Document Upload", False, 0, "Test document not found")
            return False

        start = time.time()

        try:
            # Read document file
            with open(self.TEST_DOCUMENT, 'rb') as f:
                files = {
                    'file': ('Rahimi.pdf', f, 'application/pdf')
                }
                data = {
                    'client_id': str(self.TEST_CLIENT_ID),
                    'case_id': str(self.TEST_CASE_ID),
                    'document_name': 'Rahimi.pdf'
                }

                print(f"📤 Uploading {self.TEST_DOCUMENT.name} to {self.DOCUMENT_UPLOAD_URL}...")
                response = await self.http_client.post(
                    self.DOCUMENT_UPLOAD_URL,
                    files=files,
                    data=data
                )

            duration = time.time() - start

            if response.status_code == 200:
                result = response.json()
                self.document_id = result.get("document_id")
                print(f"✅ Upload successful! Document ID: {self.document_id}")

                self._record_stage_result(
                    1, "Document Upload", True, duration,
                    f"Document ID: {self.document_id}"
                )
                return True
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                print(f"Response: {response.text}")
                self._record_stage_result(1, "Document Upload", False, duration, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            duration = time.time() - start
            print(f"❌ Upload error: {str(e)}")
            self._record_stage_result(1, "Document Upload", False, duration, str(e))
            return False

    async def stage_2_entity_extraction(self) -> bool:
        """
        Stage 2: Extract entities using AI extraction service.

        Returns:
            True if extraction successful, False otherwise
        """
        print("\n" + "=" * 80)
        print("STAGE 2: ENTITY EXTRACTION")
        print("=" * 80)

        if not self.document_id:
            print("❌ No document_id from previous stage")
            self._record_stage_result(2, "Entity Extraction", False, 0, "Missing document_id")
            return False

        start = time.time()

        try:
            payload = {
                "document_id": self.document_id,
                "client_id": str(self.TEST_CLIENT_ID),
                "case_id": str(self.TEST_CASE_ID),
                "extraction_mode": "ai"  # Use AI extraction for comprehensive results
            }

            print(f"🔍 Extracting entities from document {self.document_id}...")
            response = await self.http_client.post(
                self.ENTITY_EXTRACTION_URL,
                json=payload
            )

            duration = time.time() - start

            if response.status_code == 200:
                result = response.json()
                entity_count = len(result.get("entities", []))
                print(f"✅ Extraction successful! Found {entity_count} entities")

                self._record_stage_result(
                    2, "Entity Extraction", True, duration,
                    f"Extracted {entity_count} entities"
                )
                return True
            else:
                print(f"❌ Extraction failed with status {response.status_code}")
                print(f"Response: {response.text}")
                self._record_stage_result(2, "Entity Extraction", False, duration, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            duration = time.time() - start
            print(f"❌ Extraction error: {str(e)}")
            self._record_stage_result(2, "Entity Extraction", False, duration, str(e))
            return False

    async def stage_3_smart_chunking(self) -> bool:
        """
        Stage 3: Perform smart chunking with contextual enhancement.

        Returns:
            True if chunking successful, False otherwise
        """
        print("\n" + "=" * 80)
        print("STAGE 3: SMART CHUNKING")
        print("=" * 80)

        if not self.document_id:
            print("❌ No document_id from previous stage")
            self._record_stage_result(3, "Smart Chunking", False, 0, "Missing document_id")
            return False

        start = time.time()

        try:
            payload = {
                "document_id": self.document_id,
                "client_id": str(self.TEST_CLIENT_ID),
                "case_id": str(self.TEST_CASE_ID),
                "strategy": "smart",
                "generate_embeddings": True  # Generate embeddings for chunks
            }

            print(f"✂️  Chunking document {self.document_id} with smart strategy...")
            response = await self.http_client.post(
                self.CHUNKING_URL,
                json=payload
            )

            duration = time.time() - start

            if response.status_code == 200:
                result = response.json()
                chunk_count = len(result.get("chunks", []))
                print(f"✅ Chunking successful! Created {chunk_count} chunks")

                self._record_stage_result(
                    3, "Smart Chunking", True, duration,
                    f"Created {chunk_count} contextual chunks"
                )
                return True
            else:
                print(f"❌ Chunking failed with status {response.status_code}")
                print(f"Response: {response.text}")
                self._record_stage_result(3, "Smart Chunking", False, duration, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            duration = time.time() - start
            print(f"❌ Chunking error: {str(e)}")
            self._record_stage_result(3, "Smart Chunking", False, duration, str(e))
            return False

    async def stage_4_graphrag_construction(self) -> bool:
        """
        Stage 4: Construct knowledge graph with GraphRAG service.

        This creates:
        - Entity nodes
        - Relationships (edges)
        - Communities (Leiden clustering)
        - Chunk-entity connections
        - Chunk cross-references

        Returns:
            True if construction successful, False otherwise
        """
        print("\n" + "=" * 80)
        print("STAGE 4: GRAPHRAG CONSTRUCTION")
        print("=" * 80)

        if not self.document_id:
            print("❌ No document_id from previous stage")
            self._record_stage_result(4, "GraphRAG Construction", False, 0, "Missing document_id")
            return False

        start = time.time()

        try:
            payload = {
                "document_id": self.document_id,
                "client_id": str(self.TEST_CLIENT_ID),
                "case_id": str(self.TEST_CASE_ID),
                "processing_mode": "FULL_GRAPHRAG"  # Full processing with all features
            }

            print(f"🕸️  Building knowledge graph for document {self.document_id}...")
            print("   This includes:")
            print("   - Entity deduplication (0.85 threshold)")
            print("   - Relationship discovery")
            print("   - Leiden community detection")
            print("   - Chunk-entity connections")
            print("   - Chunk cross-references")

            response = await self.http_client.post(
                self.GRAPHRAG_URL,
                json=payload
            )

            duration = time.time() - start

            if response.status_code == 200:
                result = response.json()
                node_count = result.get("node_count", 0)
                edge_count = result.get("edge_count", 0)
                community_count = result.get("community_count", 0)

                print(f"✅ GraphRAG construction successful!")
                print(f"   Nodes: {node_count}")
                print(f"   Edges: {edge_count}")
                print(f"   Communities: {community_count}")

                self._record_stage_result(
                    4, "GraphRAG Construction", True, duration,
                    f"Nodes: {node_count}, Edges: {edge_count}, Communities: {community_count}"
                )
                return True
            else:
                print(f"❌ GraphRAG construction failed with status {response.status_code}")
                print(f"Response: {response.text}")
                self._record_stage_result(4, "GraphRAG Construction", False, duration, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            duration = time.time() - start
            print(f"❌ GraphRAG construction error: {str(e)}")
            self._record_stage_result(4, "GraphRAG Construction", False, duration, str(e))
            return False

    async def stage_5_database_validation(self) -> bool:
        """
        Stage 5: Validate all database tables using SupabaseClient.

        Validates:
        - graph.nodes (entities)
        - graph.edges (relationships)
        - graph.communities (Leiden clustering)
        - graph.chunk_entity_connections (NEW)
        - graph.chunk_cross_references (NEW)
        - graph.embeddings (Jina v4 2048-dim)
        - graph.contextual_chunks

        Returns:
            True if all validations passed, False otherwise
        """
        print("\n" + "=" * 80)
        print("STAGE 5: DATABASE VALIDATION")
        print("=" * 80)

        start = time.time()

        try:
            all_passed = await self.db_validator.validate_all_tables()
            duration = time.time() - start

            summary = self.db_validator.get_summary_dict()

            self._record_stage_result(
                5, "Database Validation", all_passed, duration,
                f"Validated {summary['total_tables']} tables: {summary['passed_tables']} passed, {summary['failed_tables']} failed"
            )

            return all_passed

        except Exception as e:
            duration = time.time() - start
            print(f"❌ Database validation error: {str(e)}")
            self._record_stage_result(5, "Database Validation", False, duration, str(e))
            return False

    async def stage_6_performance_benchmark(self) -> bool:
        """
        Stage 6: Benchmark query performance.

        Compares:
        - Old: metadata JSONB filtering
        - New: UUID column filtering

        Target: ≥50% improvement

        Returns:
            True if performance target met, False otherwise
        """
        print("\n" + "=" * 80)
        print("STAGE 6: PERFORMANCE BENCHMARK")
        print("=" * 80)

        start = time.time()

        try:
            summary = await self.perf_analyzer.run_comprehensive_benchmark()
            duration = time.time() - start

            target_met = summary["target_met"]
            avg_improvement = summary["avg_improvement_p50_pct"]

            self._record_stage_result(
                6, "Performance Benchmark", target_met, duration,
                f"Average improvement: {avg_improvement:.1f}% (target: ≥50%)"
            )

            return target_met

        except Exception as e:
            duration = time.time() - start
            print(f"❌ Performance benchmark error: {str(e)}")
            self._record_stage_result(6, "Performance Benchmark", False, duration, str(e))
            return False

    async def run_e2e_test(self) -> E2ETestReport:
        """
        Run complete end-to-end test pipeline.

        Returns:
            E2ETestReport with complete test results
        """
        print("\n" + "🚀" * 40)
        print("GRAPHRAG END-TO-END TEST")
        print("🚀" * 40)
        print(f"Test ID: {self.test_id}")
        print(f"Document: {self.TEST_DOCUMENT.name}")
        print(f"Client ID: {self.TEST_CLIENT_ID}")
        print(f"Case ID: {self.TEST_CASE_ID}")
        print("🚀" * 40)

        self.start_time = datetime.now()

        try:
            # Stage 0: Service Health
            service_health_passed = await self.stage_0_service_health()
            if not service_health_passed:
                print("\n⚠️  WARNING: Some services are not healthy")
                print("Continuing anyway to test available services...")

            # Stage 1: Document Upload
            upload_passed = await self.stage_1_document_upload()
            if not upload_passed:
                print("\n❌ Upload failed - cannot continue with remaining stages")
                self.end_time = datetime.now()
                return self._generate_report()

            # Stage 2: Entity Extraction
            extraction_passed = await self.stage_2_entity_extraction()
            if not extraction_passed:
                print("\n❌ Entity extraction failed - cannot continue")
                self.end_time = datetime.now()
                return self._generate_report()

            # Stage 3: Smart Chunking
            chunking_passed = await self.stage_3_smart_chunking()
            if not chunking_passed:
                print("\n❌ Chunking failed - cannot continue")
                self.end_time = datetime.now()
                return self._generate_report()

            # Stage 4: GraphRAG Construction
            graphrag_passed = await self.stage_4_graphrag_construction()
            if not graphrag_passed:
                print("\n❌ GraphRAG construction failed - cannot continue")
                self.end_time = datetime.now()
                return self._generate_report()

            # Stage 5: Database Validation
            validation_passed = await self.stage_5_database_validation()

            # Stage 6: Performance Benchmark
            perf_passed = await self.stage_6_performance_benchmark()

        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            self.end_time = datetime.now()
            await self.cleanup()

        return self._generate_report()

    def _generate_report(self) -> E2ETestReport:
        """
        Generate comprehensive test report.

        Returns:
            E2ETestReport with all results
        """
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0

        passed_stages = sum(1 for s in self.stage_results if s["passed"])
        total_stages = len(self.stage_results)
        overall_status = "PASSED" if passed_stages == total_stages else "FAILED"

        report = E2ETestReport(
            test_id=self.test_id,
            start_time=self.start_time.isoformat() if self.start_time else "",
            end_time=self.end_time.isoformat() if self.end_time else "",
            duration_seconds=duration,
            document_name=self.TEST_DOCUMENT.name,
            client_id=str(self.TEST_CLIENT_ID),
            case_id=str(self.TEST_CASE_ID),
            service_health=self.service_checker.get_summary_dict(),
            stage_results=self.stage_results,
            database_validation=self.db_validator.get_summary_dict(),
            performance_benchmark=self.perf_analyzer.get_summary_dict(),
            overall_status=overall_status,
            total_stages=total_stages,
            passed_stages=passed_stages,
            failed_stages=total_stages - passed_stages
        )

        # Generate all report formats
        print("\n" + "=" * 80)
        print("FINAL RESULTS")
        print("=" * 80)
        print(f"Overall Status: {overall_status}")
        print(f"Passed Stages: {passed_stages}/{total_stages}")
        print(f"Total Duration: {duration:.2f}s")
        print("=" * 80)

        report_files = self.report_generator.generate_all_reports(report)
        print(f"\n📄 Reports generated:")
        print(f"   HTML: {report_files['html']}")
        print(f"   CSV:  {report_files['csv']}")
        print(f"   JSON: {report_files['json']}")

        return report


async def main():
    """Main test execution."""
    harness = PipelineTestHarness()
    report = await harness.run_e2e_test()

    # Exit with appropriate code
    exit_code = 0 if report.overall_status == "PASSED" else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
