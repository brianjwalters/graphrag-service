"""
Service Health Checker for E2E Testing

Verifies that all required Luris services are running via systemctl
before executing E2E pipeline tests.
"""

import asyncio
import subprocess
from typing import Dict, List, Tuple
from dataclasses import dataclass
import httpx
from datetime import datetime


@dataclass
class ServiceConfig:
    """Configuration for a Luris service."""
    name: str
    systemd_unit: str
    health_endpoint: str
    port: int
    required: bool = True


class ServiceHealthChecker:
    """
    Checks health status of all Luris services required for E2E testing.

    Verifies:
    1. systemd service is active and running
    2. HTTP health endpoint responds successfully
    3. Service is ready to accept requests
    """

    # Service definitions for E2E pipeline
    REQUIRED_SERVICES = [
        ServiceConfig(
            name="Document Upload",
            systemd_unit="luris-document-upload",
            health_endpoint="http://localhost:8008/api/v1/health",
            port=8008
        ),
        ServiceConfig(
            name="Entity Extraction",
            systemd_unit="luris-entity-extraction",
            health_endpoint="http://localhost:8007/api/v1/health",
            port=8007
        ),
        ServiceConfig(
            name="Chunking Service",
            systemd_unit="luris-chunking",
            health_endpoint="http://localhost:8009/api/v1/health",
            port=8009
        ),
        ServiceConfig(
            name="GraphRAG Service",
            systemd_unit="luris-graphrag",
            health_endpoint="http://localhost:8010/api/v1/health",
            port=8010
        ),
        ServiceConfig(
            name="vLLM LLM Service",
            systemd_unit="luris-vllm",
            health_endpoint="http://localhost:8080/health",
            port=8080
        ),
        ServiceConfig(
            name="vLLM Embeddings Service",
            systemd_unit="luris-vllm-embeddings",
            health_endpoint="http://localhost:8081/health",
            port=8081
        ),
        ServiceConfig(
            name="Log Service",
            systemd_unit="luris-log",
            health_endpoint="http://localhost:8001/api/v1/health",
            port=8001
        ),
        ServiceConfig(
            name="Supabase Service",
            systemd_unit="luris-supabase",
            health_endpoint="http://localhost:8002/api/v1/health",
            port=8002
        ),
    ]

    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.start_time = None
        self.end_time = None

    def check_systemd_status(self, service_config: ServiceConfig) -> Tuple[bool, str]:
        """
        Check if systemd service is active and running.

        Args:
            service_config: Service configuration

        Returns:
            Tuple of (is_active, status_message)
        """
        try:
            # Check if service is active
            result = subprocess.run(
                ["systemctl", "is-active", service_config.systemd_unit],
                capture_output=True,
                text=True,
                timeout=5
            )

            is_active = result.stdout.strip() == "active"

            if is_active:
                # Get detailed status
                status_result = subprocess.run(
                    ["systemctl", "status", service_config.systemd_unit, "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                # Extract uptime from status
                status_lines = status_result.stdout.split('\n')
                uptime_info = "unknown"
                for line in status_lines:
                    if "Active:" in line:
                        uptime_info = line.strip()
                        break

                return True, f"Active ({uptime_info})"
            else:
                return False, f"Service is {result.stdout.strip()}"

        except subprocess.TimeoutExpired:
            return False, "systemctl command timeout"
        except Exception as e:
            return False, f"Error checking systemd: {str(e)}"

    async def check_http_health(self, service_config: ServiceConfig) -> Tuple[bool, str, int]:
        """
        Check HTTP health endpoint.

        Args:
            service_config: Service configuration

        Returns:
            Tuple of (is_healthy, message, response_time_ms)
        """
        start = datetime.now()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(service_config.health_endpoint)
                response_time = int((datetime.now() - start).total_seconds() * 1000)

                if response.status_code == 200:
                    return True, f"HTTP 200 OK ({response_time}ms)", response_time
                else:
                    return False, f"HTTP {response.status_code} ({response_time}ms)", response_time

        except httpx.ConnectError:
            response_time = int((datetime.now() - start).total_seconds() * 1000)
            return False, f"Connection refused on port {service_config.port}", response_time
        except httpx.TimeoutException:
            response_time = int((datetime.now() - start).total_seconds() * 1000)
            return False, f"Health endpoint timeout (>{response_time}ms)", response_time
        except Exception as e:
            response_time = int((datetime.now() - start).total_seconds() * 1000)
            return False, f"Error: {str(e)}", response_time

    async def check_service(self, service_config: ServiceConfig) -> Dict:
        """
        Comprehensive health check for a single service.

        Args:
            service_config: Service configuration

        Returns:
            Dictionary with health check results
        """
        print(f"\nChecking {service_config.name} ({service_config.systemd_unit})...")

        # Step 1: Check systemd status
        systemd_active, systemd_message = self.check_systemd_status(service_config)
        print(f"  ├─ systemd: {'✅' if systemd_active else '❌'} {systemd_message}")

        # Step 2: Check HTTP health (only if systemd is active)
        if systemd_active:
            http_healthy, http_message, response_time = await self.check_http_health(service_config)
            print(f"  └─ HTTP health: {'✅' if http_healthy else '❌'} {http_message}")
        else:
            http_healthy = False
            http_message = "Skipped (service not active)"
            response_time = -1
            print(f"  └─ HTTP health: ⏭️  {http_message}")

        overall_healthy = systemd_active and http_healthy

        return {
            "service_name": service_config.name,
            "systemd_unit": service_config.systemd_unit,
            "port": service_config.port,
            "systemd_active": systemd_active,
            "systemd_message": systemd_message,
            "http_healthy": http_healthy,
            "http_message": http_message,
            "response_time_ms": response_time,
            "overall_healthy": overall_healthy,
            "required": service_config.required
        }

    async def check_all_services(self) -> Tuple[bool, Dict[str, Dict]]:
        """
        Check health of all required services.

        Returns:
            Tuple of (all_healthy, results_dict)
        """
        print("=" * 80)
        print("LURIS SERVICE HEALTH CHECK")
        print("=" * 80)

        self.start_time = datetime.now()

        # Check all services in parallel
        tasks = [self.check_service(config) for config in self.REQUIRED_SERVICES]
        results = await asyncio.gather(*tasks)

        # Build results dictionary
        self.results = {r["service_name"]: r for r in results}

        self.end_time = datetime.now()
        total_time = (self.end_time - self.start_time).total_seconds()

        # Determine overall health
        all_healthy = all(
            r["overall_healthy"]
            for r in results
            if r["required"]
        )

        # Print summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        healthy_count = sum(1 for r in results if r["overall_healthy"])
        total_count = len(results)
        required_healthy = sum(1 for r in results if r["required"] and r["overall_healthy"])
        required_count = sum(1 for r in results if r["required"])

        print(f"Overall Status: {'✅ ALL SERVICES HEALTHY' if all_healthy else '❌ SOME SERVICES UNHEALTHY'}")
        print(f"Healthy Services: {healthy_count}/{total_count}")
        print(f"Required Services: {required_healthy}/{required_count}")
        print(f"Check Duration: {total_time:.2f}s")

        if not all_healthy:
            print("\n❌ FAILED SERVICES:")
            for r in results:
                if not r["overall_healthy"] and r["required"]:
                    print(f"  - {r['service_name']} ({r['systemd_unit']})")
                    print(f"    systemd: {r['systemd_message']}")
                    print(f"    HTTP: {r['http_message']}")

        print("=" * 80)

        return all_healthy, self.results

    def start_failed_services(self) -> List[str]:
        """
        Attempt to start all failed required services via systemctl.

        Returns:
            List of service names that were started (or attempted)
        """
        started_services = []

        for service_name, result in self.results.items():
            if not result["overall_healthy"] and result["required"]:
                print(f"\n🚀 Attempting to start {service_name}...")
                try:
                    subprocess.run(
                        ["sudo", "systemctl", "start", result["systemd_unit"]],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=True
                    )
                    print(f"  ✅ Started {result['systemd_unit']}")
                    started_services.append(service_name)
                except subprocess.CalledProcessError as e:
                    print(f"  ❌ Failed to start {result['systemd_unit']}: {e.stderr}")
                except Exception as e:
                    print(f"  ❌ Error starting {result['systemd_unit']}: {str(e)}")

        return started_services

    def get_summary_dict(self) -> Dict:
        """
        Get summary dictionary for reporting.

        Returns:
            Dictionary with summary metrics
        """
        if not self.results:
            return {}

        return {
            "total_services": len(self.results),
            "healthy_services": sum(1 for r in self.results.values() if r["overall_healthy"]),
            "required_services": sum(1 for r in self.results.values() if r["required"]),
            "required_healthy": sum(
                1 for r in self.results.values()
                if r["required"] and r["overall_healthy"]
            ),
            "all_healthy": all(
                r["overall_healthy"]
                for r in self.results.values()
                if r["required"]
            ),
            "check_duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time
                else 0
            ),
            "services": self.results
        }


async def verify_services_ready() -> bool:
    """
    Convenience function to verify all services are ready for E2E testing.

    Returns:
        True if all required services are healthy, False otherwise
    """
    checker = ServiceHealthChecker()
    all_healthy, _ = await checker.check_all_services()

    if not all_healthy:
        print("\n⚠️  Some services are not healthy.")
        print("Would you like to attempt starting failed services? (requires sudo)")
        # In automated testing, we don't prompt - just return False
        return False

    return True


if __name__ == "__main__":
    # Standalone execution for manual testing
    import sys

    async def main():
        checker = ServiceHealthChecker()
        all_healthy, results = await checker.check_all_services()

        if not all_healthy:
            print("\n" + "=" * 80)
            print("REMEDIATION OPTIONS")
            print("=" * 80)
            print("To start failed services manually:")
            for service_name, result in results.items():
                if not result["overall_healthy"] and result["required"]:
                    print(f"  sudo systemctl start {result['systemd_unit']}")
            print("=" * 80)
            sys.exit(1)
        else:
            print("\n✅ All services ready for E2E testing!")
            sys.exit(0)

    asyncio.run(main())
