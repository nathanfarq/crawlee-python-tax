"""Rate limiter for respectful CRA scraping."""

import asyncio
import time
from collections import defaultdict
from typing import Any

from crawlee._utils import console


class CRARateLimiter:
    """Rate limiter with per-minute, per-hour, and per-day tracking."""

    def __init__(
        self,
        *,
        max_requests_per_minute: int = 30,
        max_requests_per_hour: int = 500,
        max_requests_per_day: int = 5000,
        request_delay: float = 2.0,
    ) -> None:
        self._max_per_minute = max_requests_per_minute
        self._max_per_hour = max_requests_per_hour
        self._max_per_day = max_requests_per_day
        self._request_delay = request_delay

        # Track request timestamps for different time windows
        self._requests: defaultdict[str, list[float]] = defaultdict(list)
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a request, blocking if necessary."""
        async with self._lock:
            current_time = time.time()

            # Clean old requests from tracking
            self._cleanup_old_requests(current_time)

            # Check if we're within limits
            await self._wait_if_rate_limited(current_time)

            # Ensure minimum delay between requests
            if self._last_request_time > 0:
                time_since_last = current_time - self._last_request_time
                if time_since_last < self._request_delay:
                    wait_time = self._request_delay - time_since_last
                    console.print(f'[yellow]Rate limiting: waiting {wait_time:.1f}s[/yellow]')
                    await asyncio.sleep(wait_time)
                    current_time = time.time()

            # Record this request
            self._requests['minute'].append(current_time)
            self._requests['hour'].append(current_time)
            self._requests['day'].append(current_time)
            self._last_request_time = current_time

    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove old request timestamps outside the tracking windows."""
        # Remove requests older than 1 minute
        minute_cutoff = current_time - 60
        self._requests['minute'] = [t for t in self._requests['minute'] if t > minute_cutoff]

        # Remove requests older than 1 hour
        hour_cutoff = current_time - 3600
        self._requests['hour'] = [t for t in self._requests['hour'] if t > hour_cutoff]

        # Remove requests older than 1 day
        day_cutoff = current_time - 86400
        self._requests['day'] = [t for t in self._requests['day'] if t > day_cutoff]

    async def _wait_if_rate_limited(self, current_time: float) -> None:
        """Wait if any rate limits would be exceeded."""
        # Check per-minute limit
        if len(self._requests['minute']) >= self._max_per_minute:
            oldest_request = min(self._requests['minute'])
            wait_time = 60 - (current_time - oldest_request) + 1
            if wait_time > 0:
                console.print(f'[red]Per-minute limit reached: waiting {wait_time:.1f}s[/red]')
                await asyncio.sleep(wait_time)
                return

        # Check per-hour limit
        if len(self._requests['hour']) >= self._max_per_hour:
            oldest_request = min(self._requests['hour'])
            wait_time = 3600 - (current_time - oldest_request) + 1
            if wait_time > 0:
                console.print(f'[red]Per-hour limit reached: waiting {wait_time:.1f}s[/red]')
                await asyncio.sleep(wait_time)
                return

        # Check per-day limit
        if len(self._requests['day']) >= self._max_per_day:
            oldest_request = min(self._requests['day'])
            wait_time = 86400 - (current_time - oldest_request) + 1
            if wait_time > 0:
                console.print(f'[red]Per-day limit reached: waiting {wait_time:.1f}s[/red]')
                await asyncio.sleep(wait_time)
                return

    def get_stats(self) -> dict[str, Any]:
        """Get current rate limiting statistics."""
        current_time = time.time()
        self._cleanup_old_requests(current_time)

        return {
            'requests_last_minute': len(self._requests['minute']),
            'requests_last_hour': len(self._requests['hour']),
            'requests_last_day': len(self._requests['day']),
            'max_per_minute': self._max_per_minute,
            'max_per_hour': self._max_per_hour,
            'max_per_day': self._max_per_day,
        }
