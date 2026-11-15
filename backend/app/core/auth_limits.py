from collections import deque
from ipaddress import ip_address
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse


class AuthRateLimiter:
    """Bound per-client authentication traffic for a single API process."""

    def __init__(self, window_seconds: int = 60, max_clients: int = 4096, trusted_proxies=()):
        self._window = window_seconds
        self._max_clients = max_clients
        self._attempts: dict[tuple[str, str], deque[float]] = {}
        self._sweep_at = 0.0
        self._lock = Lock()
        self._trusted_proxies = trusted_proxies

    def _client_host(self, request: Request) -> str:
        peer = request.client.host if request.client else "unknown"
        try:
            peer_address = ip_address(peer)
        except ValueError:
            return peer
        if not any(peer_address in network for network in self._trusted_proxies):
            return str(peer_address)

        # Walk from the trusted socket peer toward the client. Anything to the
        # left of the first untrusted hop can have been supplied by that hop.
        forwarded = ",".join(request.headers.getlist("x-forwarded-for"))
        for hop in reversed(forwarded.split(",")):
            try:
                address = ip_address(hop.strip())
            except ValueError:
                break
            if not any(address in network for network in self._trusted_proxies):
                return str(address)
        return str(peer_address)

    def check(self, request: Request, action: str, limit: int) -> None:
        key = (action, self._client_host(request))
        with self._lock:
            now = monotonic()
            cutoff = now - self._window
            if now >= self._sweep_at:
                self._attempts = {key: attempts for key, attempts in self._attempts.items() if attempts[-1] > cutoff}
                self._sweep_at = now + self._window

            attempts = self._attempts.get(key)
            if attempts is None:
                if len(self._attempts) >= self._max_clients:
                    self._reject(self._window)
                attempts = self._attempts[key] = deque()
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= limit:
                self._reject(ceil(attempts[0] + self._window - now))
            attempts.append(now)

    @staticmethod
    def _reject(retry_after: int) -> None:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Wait a minute and try again.",
            headers={"Retry-After": str(max(1, retry_after))},
        )


class AuthBodyLimit:
    """Bound auth JSON input before FastAPI reads or parses it."""

    def __init__(self, app, max_bytes: int = 4096):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http" or scope["method"] != "POST"
            or scope["path"].rstrip("/") not in {"/auth/login", "/auth/register"}
        ):
            await self.app(scope, receive, send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > self.max_bytes:
                response = JSONResponse({"detail": "Authentication request is too large."}, status_code=413)
                await response(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        # Replay even an empty request once before forwarding disconnects.
        first_read = True

        async def replay():
            nonlocal first_read
            if first_read:
                first_read = False
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
