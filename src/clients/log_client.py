import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum
import os
from collections import deque
import backoff
from contextlib import asynccontextmanager

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class LogClient:
    """Client for interacting with the Log Service API"""
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        service_name: str = None,
        batch_size: int = 100,
        flush_interval: float = 1.0,
        max_retries: int = 3,
        timeout: float = 10.0,
        fallback_to_console: bool = True,
        fallback_to_file: bool = True,
        fallback_file_path: str = "/tmp/luris_fallback.log"
    ):
        self.base_url = base_url or os.getenv("LOG_SERVICE_URL", "http://localhost:8001/api/v1")
        self.api_key = api_key or os.getenv("LOG_SERVICE_API_KEY", "")
        self.service_name = service_name or os.getenv("SERVICE_NAME", "unknown")
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        self.timeout = timeout
        self.fallback_to_console = fallback_to_console
        self.fallback_to_file = fallback_to_file
        self.fallback_file_path = fallback_file_path
        self._session: Optional[aiohttp.ClientSession] = None
        self._log_queue: deque = deque()
        self._flush_task: Optional[asyncio.Task] = None
        self._closed = False
        self._health_check_interval = 30.0
        self._is_healthy = True
        self._health_check_task: Optional[asyncio.Task] = None
        self._default_context = {
            "service": self.service_name,
            "environment": os.getenv("ENVIRONMENT", "production"),
            "version": os.getenv("SERVICE_VERSION", "unknown"),
            "host": os.getenv("HOSTNAME", "unknown"),
            "process_id": os.getpid()
        }

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def close(self):
        self._closed = True
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        await self._flush_logs()
        if self._session:
            await self._session.close()
            self._session = None

    # --- Logging Methods ---
    async def debug(self, message: str, **context):
        await self.log(LogLevel.DEBUG, message, **context)

    async def info(self, message: str, **context):
        await self.log(LogLevel.INFO, message, **context)

    async def warning(self, message: str, **context):
        await self.log(LogLevel.WARNING, message, **context)

    async def error(self, message: str, error: Optional[Exception] = None, **context):
        if error:
            context["error_type"] = type(error).__name__
            context["error_message"] = str(error)
            if hasattr(error, "__traceback__"):
                import traceback
                context["stack_trace"] = traceback.format_tb(error.__traceback__)
        await self.log(LogLevel.ERROR, message, **context)

    async def critical(self, message: str, error: Optional[Exception] = None, **context):
        if error:
            context["error_type"] = type(error).__name__
            context["error_message"] = str(error)
            if hasattr(error, "__traceback__"):
                import traceback
                context["stack_trace"] = traceback.format_tb(error.__traceback__)
        await self.log(LogLevel.CRITICAL, message, **context)

    async def log(self, level: Union[LogLevel, str], message: str, **context):
        log_entry = {
            "level": level.value if isinstance(level, LogLevel) else level,
            "message": message,
            "service": self.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {**self._default_context, **context}
        }
        # Add trace context if available
        if hasattr(asyncio, "current_task"):
            task = asyncio.current_task()
            if task and hasattr(task, "trace_id"):
                log_entry["trace_id"] = task.trace_id
            if task and hasattr(task, "span_id"):
                log_entry["span_id"] = task.span_id
        self._log_queue.append(log_entry)
        if len(self._log_queue) >= self.batch_size:
            await self._flush_logs()

    async def log_batch(self, entries: List[Dict[str, Any]]):
        for entry in entries:
            if "level" not in entry or "message" not in entry:
                continue
            entry.setdefault("service", self.service_name)
            entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            entry.setdefault("context", {}).update(self._default_context)
            self._log_queue.append(entry)
        if len(self._log_queue) >= self.batch_size:
            await self._flush_logs()

    # --- Search and Retrieval ---
    async def search(
        self,
        level: Optional[str] = None,
        service: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        text: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[Dict[str, Any]]:
        if not self._session:
            await self.start()
        params = {"limit": limit, "offset": offset}
        if level:
            params["level"] = level
        if service:
            params["service"] = service
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()
        if text:
            params["text"] = text
        for key, value in filters.items():
            params[f"context.{key}"] = value
        try:
            async with self._session.get(
                f"{self.base_url}/logs",
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("logs", [])
        except Exception as e:
            await self._handle_error("search", e)
            return []

    async def get_stats(self, period: str = "day") -> Dict[str, Any]:
        if not self._session:
            await self.start()
        try:
            async with self._session.get(
                f"{self.base_url}/logs/stats",
                params={"period": period}
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            await self._handle_error("get_stats", e)
            return {}

    # --- Health Check ---
    async def health_check(self) -> Dict[str, Any]:
        if not self._session:
            await self.start()
        try:
            async with self._session.get(f"{self.base_url}/health") as response:
                response.raise_for_status()
                return await response.json()
        except Exception:
            return {"status": "unhealthy"}

    async def ping(self) -> bool:
        if not self._session:
            await self.start()
        try:
            async with self._session.get(f"{self.base_url}/health/ping") as response:
                return response.status == 200
        except Exception:
            return False

    # --- Internal Methods ---
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"LogClient/{self.service_name}"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _flush_loop(self):
        while not self._closed:
            try:
                await asyncio.sleep(self.flush_interval)
                if self._log_queue:
                    await self._flush_logs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.fallback_to_console:
                    print(f"Error in flush loop: {e}")

    async def _health_check_loop(self):
        while not self._closed:
            try:
                await asyncio.sleep(self._health_check_interval)
                health = await self.health_check()
                self._is_healthy = health.get("status") == "healthy"
            except asyncio.CancelledError:
                break
            except Exception:
                self._is_healthy = False

    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=30
    )
    async def _flush_logs(self):
        if not self._log_queue or not self._session:
            return
        logs_to_send = []
        while self._log_queue and len(logs_to_send) < self.batch_size:
            logs_to_send.append(self._log_queue.popleft())
        if not logs_to_send:
            return
        try:
            if len(logs_to_send) == 1:
                async with self._session.post(
                    f"{self.base_url}/logs",
                    json=logs_to_send[0]
                ) as response:
                    response.raise_for_status()
            else:
                async with self._session.post(
                    f"{self.base_url}/logs/batch",
                    json={"logs": logs_to_send}
                ) as response:
                    response.raise_for_status()
        except Exception as e:
            await self._handle_failed_logs(logs_to_send, e)

    async def _handle_failed_logs(self, logs: List[Dict[str, Any]], error: Exception):
        if self.fallback_to_console:
            for log in logs:
                print(json.dumps(log))
        if self.fallback_to_file:
            try:
                with open(self.fallback_file_path, 'a') as f:
                    for log in logs:
                        f.write(json.dumps(log) + '\n')
            except Exception:
                pass
        if len(self._log_queue) < self.batch_size * 10:
            for log in logs:
                self._log_queue.append(log)

    async def _handle_error(self, operation: str, error: Exception):
        error_log = {
            "level": "error",
            "message": f"LogClient {operation} failed",
            "service": self.service_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": {
                "operation": operation,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        }
        if self.fallback_to_console:
            print(json.dumps(error_log))
        if self.fallback_to_file:
            try:
                with open(self.fallback_file_path, 'a') as f:
                    f.write(json.dumps(error_log) + '\n')
            except Exception:
                pass 