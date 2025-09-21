"""
Security Controls Middleware (MW_SEC)
Provides comprehensive security controls, threat detection, and access monitoring.
"""

import logging
import os
import time
from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from .types import MiddlewareMetrics, SecurityContext, SecurityLevel

logger = logging.getLogger(__name__)


class SecurityControlsMiddleware(BaseHTTPMiddleware):
    """
    Security Controls Middleware (MW_SEC)

    Provides:
    - Threat detection and analysis
    - Security level assessment
    - Access pattern monitoring
    - Security event logging
    - Intrusion detection

    Configuration via environment variables:
    - SECURITY_RATE_LIMIT_30SEC: requests per 30 seconds (default: 25)
    - SECURITY_RATE_LIMIT_MINUTE: requests per minute (default: 50)
    - SECURITY_RATE_LIMIT_5MIN: requests per 5 minutes (default: 150)
    - SECURITY_AUTO_DETECT_THRESHOLD: automation detection threshold (default: 20)
    - SECURITY_STRICT_MODE: enable strict security mode (default: true)
    """

    def __init__(self, app):
        super().__init__(app)
        self.security_bearer = HTTPBearer(auto_error=False)
        self.threat_patterns = self._load_threat_patterns()
        self.access_tracker = {}
        self.blocked_ips = set()

        # Load configuration from environment
        self.rate_limit_30sec = int(os.getenv("SECURITY_RATE_LIMIT_30SEC", "25"))
        self.rate_limit_minute = int(os.getenv("SECURITY_RATE_LIMIT_MINUTE", "50"))
        self.rate_limit_5min = int(os.getenv("SECURITY_RATE_LIMIT_5MIN", "150"))
        self.auto_detect_threshold = int(
            os.getenv("SECURITY_AUTO_DETECT_THRESHOLD", "20")
        )
        self.strict_mode = os.getenv("SECURITY_STRICT_MODE", "true").lower() == "true"

        logger.info(
            f"Security middleware initialized - Rate limits: {self.rate_limit_30sec}/30s, {self.rate_limit_minute}/min, {self.rate_limit_5min}/5min, Auto-detect: {self.auto_detect_threshold}, Strict: {self.strict_mode}"
        )

    def _load_threat_patterns(self) -> Dict[str, Any]:
        """Load threat detection patterns."""
        return {
            "sql_injection": [
                r"union\s+select",
                r"drop\s+table",
                r"insert\s+into",
                r"delete\s+from",
                r"'\s*or\s*'1'\s*=\s*'1'",
            ],
            "xss": [r"<script.*?>", r"javascript:", r"on\w+\s*=", r"expression\s*\("],
            "path_traversal": [r"\.\./", r"\.\.\\", r"~/"],
            "command_injection": [
                r";\s*(cat|ls|pwd|whoami)",
                r"\|\s*(curl|wget|nc)",
                r"&&\s*(rm|mv|cp)",
            ],
        }

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _analyze_threats(self, request: Request) -> Dict[str, Any]:
        """Analyze request for potential threats."""
        threats = {}

        # Analyze URL
        url_str = str(request.url)
        for threat_type, patterns in self.threat_patterns.items():
            for pattern in patterns:
                import re

                if re.search(pattern, url_str, re.IGNORECASE):
                    if threat_type not in threats:
                        threats[threat_type] = []
                    threats[threat_type].append(f"URL pattern: {pattern}")

        # Analyze headers
        for header_name, header_value in request.headers.items():
            for threat_type, patterns in self.threat_patterns.items():
                for pattern in patterns:
                    import re

                    if re.search(pattern, header_value, re.IGNORECASE):
                        if threat_type not in threats:
                            threats[threat_type] = []
                        threats[threat_type].append(f"Header {header_name}: {pattern}")

        return threats

    def _assess_security_level(
        self, request: Request, threats: Dict[str, Any]
    ) -> SecurityLevel:
        """Assess the security level of the request."""
        if threats:
            # Critical threats
            if "sql_injection" in threats or "command_injection" in threats:
                return SecurityLevel.CRITICAL

            # High risk threats
            if "xss" in threats or "path_traversal" in threats:
                return SecurityLevel.HIGH

            # Medium risk
            return SecurityLevel.MEDIUM

        # Check for suspicious patterns
        suspicious_indicators = 0

        # Check user agent
        user_agent = request.headers.get("User-Agent", "")
        if not user_agent or len(user_agent) < 10:
            suspicious_indicators += 1

        # Check for automation indicators
        automation_headers = ["X-Automated", "X-Bot", "X-Crawler", "X-Script"]
        for header in automation_headers:
            if header in request.headers:
                suspicious_indicators += 1

        if suspicious_indicators >= 2:
            return SecurityLevel.MEDIUM
        elif suspicious_indicators >= 1:
            return SecurityLevel.LOW

        return SecurityLevel.LOW

    def _track_access_pattern(self, client_ip: str, endpoint: str) -> Dict[str, Any]:
        """Track access patterns for rate limiting and abuse detection."""
        now = time.time()

        if client_ip not in self.access_tracker:
            self.access_tracker[client_ip] = {
                "requests": [],
                "endpoints": {},
                "first_seen": now,
                "total_requests": 0,
            }

        tracker = self.access_tracker[client_ip]

        # Clean old requests (last 5 minutes)
        tracker["requests"] = [
            req_time for req_time in tracker["requests"] if now - req_time < 300
        ]

        # Add current request with high precision timestamp
        tracker["requests"].append(now)
        tracker["total_requests"] += 1

        # Track endpoint usage
        if endpoint not in tracker["endpoints"]:
            tracker["endpoints"][endpoint] = 0
        tracker["endpoints"][endpoint] += 1

        # Calculate access patterns with more sensitive time windows
        requests_last_minute = len(
            [req_time for req_time in tracker["requests"] if now - req_time < 60]
        )
        requests_last_30_seconds = len(
            [req_time for req_time in tracker["requests"] if now - req_time < 30]
        )
        requests_last_5_minutes = len(tracker["requests"])

        return {
            "requests_per_minute": requests_last_minute,
            "requests_per_30_seconds": requests_last_30_seconds,
            "requests_per_5_minutes": requests_last_5_minutes,
            "total_requests": tracker["total_requests"],
            "unique_endpoints": len(tracker["endpoints"]),
            "session_duration": now - tracker["first_seen"],
        }

    def _should_block_request(
        self,
        threats: Dict[str, Any],
        access_pattern: Dict[str, Any],
        security_level: SecurityLevel,
    ) -> tuple[bool, str]:
        """Determine if request should be blocked."""

        # Block critical threats immediately (always enforced)
        if security_level == SecurityLevel.CRITICAL:
            return True, "Critical security threat detected"

        # Skip rate limiting if strict mode is disabled (for testing environments)
        if not self.strict_mode:
            return False, ""

        # Configurable rate limiting
        if access_pattern["requests_per_30_seconds"] > self.rate_limit_30sec:
            return (
                True,
                f"Rate limit exceeded: {access_pattern['requests_per_30_seconds']} requests per 30 seconds (limit: {self.rate_limit_30sec})",
            )

        if access_pattern["requests_per_minute"] > self.rate_limit_minute:
            return (
                True,
                f"Rate limit exceeded: {access_pattern['requests_per_minute']} requests per minute (limit: {self.rate_limit_minute})",
            )

        if access_pattern["requests_per_5_minutes"] > self.rate_limit_5min:
            return (
                True,
                f"Rate limit exceeded: {access_pattern['requests_per_5_minutes']} requests per 5 minutes (limit: {self.rate_limit_5min})",
            )

        # Configurable automation detection
        if (
            access_pattern["requests_per_minute"] > self.auto_detect_threshold
            and access_pattern["unique_endpoints"] < 3
        ):
            return (
                True,
                f"Suspicious automation pattern detected: {access_pattern['requests_per_minute']} requests/min to {access_pattern['unique_endpoints']} endpoints (threshold: {self.auto_detect_threshold})",
            )

        return False, ""

    async def dispatch(self, request: Request, call_next):
        """Process security controls middleware."""
        start_time = datetime.now()
        metrics = MiddlewareMetrics(start_time=start_time)

        try:
            # Get client information
            client_ip = self._get_client_ip(request)
            endpoint = f"{request.method} {request.url.path}"

            # Check if IP is blocked
            if client_ip in self.blocked_ips:
                logger.warning(f"Blocked request from banned IP: {client_ip}")
                raise HTTPException(
                    status_code=403, detail="Access denied: IP address blocked"
                )

            # Analyze threats
            threats = self._analyze_threats(request)

            # Assess security level
            security_level = self._assess_security_level(request, threats)

            # Track access patterns
            access_pattern = self._track_access_pattern(client_ip, endpoint)

            # Determine if request should be blocked
            should_block, block_reason = self._should_block_request(
                threats, access_pattern, security_level
            )

            if should_block:
                logger.warning(f"Blocking request from {client_ip}: {block_reason}")
                # Add to blocked IPs for repeated violations
                if access_pattern["requests_per_minute"] > 100:
                    self.blocked_ips.add(client_ip)
                    logger.warning(f"Added {client_ip} to blocked IPs list")

                raise HTTPException(
                    status_code=429 if "rate limit" in block_reason.lower() else 403,
                    detail=block_reason,
                )

            # Create security context
            security_context = SecurityContext(
                security_level=security_level, threat_indicators=threats
            )

            # Add security context to request state
            request.state.security_context = security_context
            request.state.access_pattern = access_pattern

            # Log security events
            if threats or security_level != SecurityLevel.LOW:
                logger.info(
                    f"Security event - IP: {client_ip}, "
                    f"Level: {security_level.value}, "
                    f"Threats: {list(threats.keys())}, "
                    f"Endpoint: {endpoint}"
                )

            # Process request
            response = await call_next(request)

            # Add security headers to response
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

            metrics.status = "success"
            metrics.end_time = datetime.now()
            metrics.duration_ms = (
                metrics.end_time - metrics.start_time
            ).total_seconds() * 1000

            return response

        except HTTPException:
            metrics.status = "blocked"
            metrics.end_time = datetime.now()
            metrics.duration_ms = (
                metrics.end_time - metrics.start_time
            ).total_seconds() * 1000
            raise

        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            metrics.status = "error"
            metrics.errors.append(str(e))
            metrics.end_time = datetime.now()
            metrics.duration_ms = (
                metrics.end_time - metrics.start_time
            ).total_seconds() * 1000
            raise HTTPException(status_code=500, detail="Security processing error")

        finally:
            # Store metrics in request state
            if hasattr(request.state, "middleware_metrics"):
                request.state.middleware_metrics["security"] = metrics
            else:
                request.state.middleware_metrics = {"security": metrics}
