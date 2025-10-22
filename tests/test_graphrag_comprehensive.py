#!/usr/bin/env python3
"""
Comprehensive Test Suite for GraphRAG Service
Tests all endpoints using both basic and advanced scenarios
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx
import pytest
from pydantic import BaseModel, Field
import logging
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8010/api/v1"
TIMEOUT = 30.0

class TestStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    SKIPPED = "skipped"

@dataclass
class TestResult:
    """Result of a single test"""
    test_name: str
    endpoint: str
    method: str
    status: TestStatus
    response_time: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        return {
            'test_name': self.test_name,
            'endpoint': self.endpoint,
            'method': self.method,
            'status': self.status.value,
            'response_time': self.response_time,
            'status_code': self.status_code,
            'error': self.error,
            'data': self.data
        }

class GraphRAGTestClient:
    """Test client for GraphRAG Service"""
    
    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"}
        )
        self.results: List[TestResult] = []
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def execute_test(
        self,
        test_name: str,
        endpoint: str,
        method: str = "GET",
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> TestResult:
        """Execute a single test and record the result"""
        start_time = time.time()
        
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                json=json_data,
                params=params
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Determine test status based on response
            if 200 <= response.status_code < 300:
                status = TestStatus.SUCCESS
            else:
                status = TestStatus.FAILURE
            
            result = TestResult(
                test_name=test_name,
                endpoint=endpoint,
                method=method,
                status=status,
                response_time=response_time,
                status_code=response.status_code,
                data=response.json() if response.text else None
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = TestResult(
                test_name=test_name,
                endpoint=endpoint,
                method=method,
                status=TestStatus.ERROR,
                response_time=response_time,
                error=str(e)
            )
        
        self.results.append(result)
        return result
    
    # Health Check Tests
    async def test_health_ping(self) -> TestResult:
        """Test basic health check endpoint"""
        return await self.execute_test(
            test_name="Health Ping",
            endpoint="/health/ping",
            method="GET"
        )
    
    async def test_health_metrics(self) -> TestResult:
        """Test health metrics endpoint"""
        return await self.execute_test(
            test_name="Health Metrics",
            endpoint="/health/metrics",
            method="GET"
        )
    
    # Graph Creation Tests
    async def test_create_simple_graph(self) -> TestResult:
        """Test creating a simple graph without AI summaries"""
        test_data = {
            "document_id": "test_doc_001",
            "markdown_content": "Test legal document content",
            "entities": [
                {
                    "entity_id": "ent_001",
                    "entity_text": "Supreme Court",
                    "entity_type": "COURT",
                    "confidence": 0.95,
                    "start_position": 0,
                    "end_position": 13
                },
                {
                    "entity_id": "ent_002",
                    "entity_text": "John Doe",
                    "entity_type": "PARTY",
                    "confidence": 0.90,
                    "start_position": 20,
                    "end_position": 28
                }
            ],
            "relationships": [
                {
                    "relationship_id": "rel_001",
                    "source_entity": "ent_001",
                    "target_entity": "ent_002",
                    "relationship_type": "DECIDED_CASE",
                    "confidence": 0.85
                }
            ],
            "graph_options": {
                "enable_deduplication": True,
                "enable_community_detection": True,
                "use_ai_summaries": False,  # Disable AI to avoid Prompt Service dependency
                "leiden_resolution": 1.0,
                "min_community_size": 2
            }
        }
        
        return await self.execute_test(
            test_name="Create Simple Graph",
            endpoint="/graph/create",
            method="POST",
            json_data=test_data
        )
    
    async def test_create_complex_graph(self) -> TestResult:
        """Test creating a complex graph with multiple entities"""
        # Generate more complex test data
        entities = []
        for i in range(20):
            entities.append({
                "entity_id": f"ent_{i:03d}",
                "entity_text": f"Entity {i}",
                "entity_type": ["COURT", "PARTY", "ATTORNEY", "JUDGE"][i % 4],
                "confidence": 0.80 + (i % 20) / 100,
                "start_position": i * 10,
                "end_position": i * 10 + 8
            })
        
        relationships = []
        for i in range(15):
            relationships.append({
                "relationship_id": f"rel_{i:03d}",
                "source_entity": f"ent_{i:03d}",
                "target_entity": f"ent_{(i+1):03d}",
                "relationship_type": ["CITES", "DECIDED_CASE", "REPRESENTS"][i % 3],
                "confidence": 0.75 + (i % 25) / 100
            })
        
        test_data = {
            "document_id": "test_doc_complex_001",
            "markdown_content": "Complex legal document with multiple entities and relationships",
            "entities": entities,
            "relationships": relationships,
            "graph_options": {
                "enable_deduplication": True,
                "enable_community_detection": True,
                "enable_cross_document_linking": True,
                "use_ai_summaries": False,
                "leiden_resolution": 1.0,
                "min_community_size": 3,
                "similarity_threshold": 0.85
            }
        }
        
        return await self.execute_test(
            test_name="Create Complex Graph",
            endpoint="/graph/create",
            method="POST",
            json_data=test_data
        )
    
    async def test_query_graph(self) -> TestResult:
        """Test querying graph data"""
        test_data = {
            "query_type": "entities",
            "filters": {
                "entity_type": "COURT"
            },
            "limit": 10
        }
        
        return await self.execute_test(
            test_name="Query Graph Entities",
            endpoint="/graph/query",
            method="POST",
            json_data=test_data
        )
    
    async def test_graph_stats(self) -> TestResult:
        """Test getting graph statistics"""
        return await self.execute_test(
            test_name="Graph Statistics",
            endpoint="/graph/stats",
            method="GET"
        )
    
    # Performance Test
    async def test_performance_batch(self, count: int = 5) -> List[TestResult]:
        """Test performance with multiple concurrent requests"""
        tasks = []
        for i in range(count):
            test_data = {
                "document_id": f"perf_test_{i:03d}",
                "markdown_content": f"Performance test document {i} with entity content",
                "entities": [
                    {
                        "entity_id": f"perf_ent_{i:03d}",
                        "entity_text": f"Performance Entity {i}",
                        "entity_type": "PARTY",
                        "confidence": 0.90
                    }
                ],
                "graph_options": {
                    "use_ai_summaries": False,
                    "enable_community_detection": False
                }
            }
            
            task = self.execute_test(
                test_name=f"Performance Test {i}",
                endpoint="/graph/create",
                method="POST",
                json_data=test_data
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive test report"""
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r.status == TestStatus.SUCCESS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILURE)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        
        avg_response_time = sum(r.response_time for r in self.results) / total_tests if total_tests > 0 else 0
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful": successful,
                "failed": failed,
                "errors": errors,
                "success_rate": (successful / total_tests * 100) if total_tests > 0 else 0,
                "avg_response_time_ms": round(avg_response_time, 2)
            },
            "results": [r.to_dict() for r in self.results],
            "timestamp": datetime.now().isoformat()
        }
    
    def print_summary(self):
        """Print a formatted summary of test results"""
        report = self.generate_report()
        
        print("\n" + "="*60)
        print("GraphRAG Service Test Results")
        print("="*60)
        
        summary = report['summary']
        print(f"\nTotal Tests: {summary['total_tests']}")
        print(f"✅ Successful: {summary['successful']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Errors: {summary['errors']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Avg Response Time: {summary['avg_response_time_ms']:.2f}ms")
        
        print("\n" + "-"*60)
        print("Individual Test Results:")
        print("-"*60)
        
        for result in self.results:
            status_icon = "✅" if result.status == TestStatus.SUCCESS else "❌" if result.status == TestStatus.FAILURE else "⚠️"
            print(f"{status_icon} {result.test_name:30} | {result.response_time:>8.2f}ms | {result.endpoint}")
            if result.error:
                print(f"   Error: {result.error}")


async def run_comprehensive_tests():
    """Run all GraphRAG tests"""
    async with GraphRAGTestClient() as client:
        print("\n🚀 Starting GraphRAG Service Comprehensive Tests...")
        
        # Health Check Tests
        print("\n📊 Testing Health Endpoints...")
        await client.test_health_ping()
        await client.test_health_metrics()
        
        # Graph CRUD Tests
        print("\n📈 Testing Graph CRUD Operations...")
        await client.test_create_simple_graph()
        await client.test_create_complex_graph()
        await client.test_query_graph()
        await client.test_graph_stats()
        
        # Performance Tests
        print("\n⚡ Running Performance Tests...")
        await client.test_performance_batch(5)
        
        # Generate and print report
        client.print_summary()
        
        # Save report to file
        report = client.generate_report()
        report_file = f"graphrag_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return report


async def run_specific_test(test_name: str):
    """Run a specific test by name"""
    async with GraphRAGTestClient() as client:
        test_methods = {
            "health": client.test_health_ping,
            "metrics": client.test_health_metrics,
            "simple_graph": client.test_create_simple_graph,
            "complex_graph": client.test_create_complex_graph,
            "query": client.test_query_graph,
            "stats": client.test_graph_stats
        }
        
        if test_name in test_methods:
            print(f"\n🚀 Running test: {test_name}")
            result = await test_methods[test_name]()
            print(f"\nResult: {result.status.value}")
            if result.error:
                print(f"Error: {result.error}")
            return result
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(test_methods.keys())}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run specific test
        asyncio.run(run_specific_test(sys.argv[1]))
    else:
        # Run all tests
        asyncio.run(run_comprehensive_tests())