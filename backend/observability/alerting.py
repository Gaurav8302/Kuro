"""
Alerting for Kuro AI.

Provides alert rules, notification channels, and alert management.
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert lifecycle status."""
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


@dataclass
class Alert:
    """Alert instance."""
    name: str
    severity: AlertSeverity
    message: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    status: AlertStatus = AlertStatus.FIRING
    starts_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ends_at: Optional[str] = None
    fingerprint: str = ""  # For deduplication

    def __post_init__(self):
        if not self.fingerprint:
            # Generate fingerprint from name + sorted labels
            import hashlib
            label_str = "|".join(f"{k}={v}" for k, v in sorted(self.labels.items()))
            self.fingerprint = hashlib.sha256(f"{self.name}|{label_str}".encode()).hexdigest()[:16]


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    condition: Callable[[], Awaitable[bool]]  # Returns True if alert should fire
    severity: AlertSeverity
    message: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    for_duration: float = 0.0  # Seconds condition must be true before firing
    interval: float = 60.0  # Evaluation interval
    cooldown: float = 300.0  # Seconds before re-firing after resolve


class NotificationChannel(ABC):
    """Abstract notification channel."""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Send notification for alert. Returns True on success."""
        pass

    @abstractmethod
    async def send_resolved(self, alert: Alert) -> bool:
        """Send resolution notification."""
        pass


class LogNotificationChannel(NotificationChannel):
    """Log-based notification (for development)."""

    async def send(self, alert: Alert) -> bool:
        log_func = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.CRITICAL: logger.error,
        }.get(alert.severity, logger.info)

        log_func(
            "ALERT FIRING: %(alert_name)s - %(message)s",
            extra={
                "alert_name": alert.name,
                "severity": alert.severity.value,
                "message": alert.message,
                "labels": alert.labels,
                "fingerprint": alert.fingerprint,
            },
        )
        return True

    async def send_resolved(self, alert: Alert) -> bool:
        logger.info(
            "ALERT RESOLVED: %(alert_name)s - %(message)s",
            extra={
                "alert_name": alert.name,
                "severity": alert.severity.value,
                "message": alert.message,
                "fingerprint": alert.fingerprint,
            },
        )
        return True


class WebhookNotificationChannel(NotificationChannel):
    """HTTP webhook notification channel."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 10.0):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout

    async def send(self, alert: Alert) -> bool:
        try:
            import httpx
            payload = {
                "alert": {
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "labels": alert.labels,
                    "annotations": alert.annotations,
                    "status": alert.status.value,
                    "starts_at": alert.starts_at,
                    "fingerprint": alert.fingerprint,
                }
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.url, json=payload, headers=self.headers)
                return response.status_code < 400
        except Exception as e:
            logger.error(f"Webhook notification failed: {e}")
            return False

    async def send_resolved(self, alert: Alert) -> bool:
        # Fire and forget for resolved
        asyncio.create_task(self.send(alert))
        return True


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_addr: str,
        to_addrs: List[str],
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs
        self.use_tls = use_tls

    async def send(self, alert: Alert) -> bool:
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.name}"

            body = f"""
Alert: {alert.name}
Severity: {alert.severity.value}
Message: {alert.message}
Time: {alert.starts_at}
Labels: {alert.labels}
Annotations: {alert.annotations}
Fingerprint: {alert.fingerprint}
"""
            msg.attach(MIMEText(body, "plain"))

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_sync, msg)
            return True
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False

    def _send_sync(self, msg: MIMEMultipart):
        if self.use_tls:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
        server.login(self.username, self.password)
        server.send_message(msg)
        server.quit()

    async def send_resolved(self, alert: Alert) -> bool:
        # Create resolved email
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)
            msg["Subject"] = f"[RESOLVED] {alert.name}"

            body = f"""
Alert: {alert.name} - RESOLVED
Severity: {alert.severity.value}
Message: {alert.message}
Started: {alert.starts_at}
Ended: {alert.ends_at or datetime.now(timezone.utc).isoformat()}
Fingerprint: {alert.fingerprint}
"""
            msg.attach(MIMEText(body, "plain"))

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_sync, msg)
            return True
        except Exception as e:
            logger.error(f"Email resolution notification failed: {e}")
            return False


class AlertManager:
    """Manages alert evaluation, firing, and notifications."""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}  # fingerprint -> Alert
        self._channels: List[NotificationChannel] = []
        self._evaluation_tasks: Dict[str, asyncio.Task] = {}
        self._silences: Dict[str, float] = {}  # fingerprint -> silence_until timestamp
        self._running = False

    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self._rules[rule.name] = rule

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self._channels.append(channel)

    def add_default_channels(self) -> None:
        """Add default log channel."""
        self.add_channel(LogNotificationChannel())

    async def start(self) -> None:
        """Start alert evaluation."""
        if self._running:
            return
        self._running = True

        # Start evaluation tasks for each rule
        for rule in self._rules.values():
            task = asyncio.create_task(self._evaluate_rule(rule))
            self._evaluation_tasks[rule.name] = task

        logger.info(f"Alert manager started with {len(self._rules)} rules")

    async def stop(self) -> None:
        """Stop alert evaluation."""
        self._running = False
        for task in self._evaluation_tasks.values():
            task.cancel()
        await asyncio.gather(*self._evaluation_tasks.values(), return_exceptions=True)
        self._evaluation_tasks.clear()
        logger.info("Alert manager stopped")

    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """Evaluate a rule periodically."""
        condition_true_since: Optional[float] = None

        while self._running:
            try:
                # Check if silenced
                if self._is_silenced(rule.name):
                    await asyncio.sleep(rule.interval)
                    continue

                # Evaluate condition
                should_fire = await rule.condition()

                if should_fire:
                    if condition_true_since is None:
                        condition_true_since = time.time()

                    # Check if condition has been true long enough
                    if time.time() - condition_true_since >= rule.for_duration:
                        await self._fire_alert(rule)
                        condition_true_since = None  # Reset after firing
                else:
                    condition_true_since = None

                    # Check if we should resolve any active alert for this rule
                    await self._resolve_if_needed(rule.name)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")

            await asyncio.sleep(rule.interval)

    async def _fire_alert(self, rule: AlertRule) -> None:
        """Fire an alert."""
        fingerprint = self._generate_fingerprint(rule)

        # Check if already firing
        if fingerprint in self._active_alerts:
            existing = self._active_alerts[fingerprint]
            if existing.status == AlertStatus.FIRING:
                # Check cooldown
                if time.time() - datetime.fromisoformat(existing.starts_at.replace('Z', '+00:00')).timestamp() < rule.cooldown:
                    return

        alert = Alert(
            name=rule.name,
            severity=rule.severity,
            message=rule.message,
            labels=rule.labels.copy(),
            annotations=rule.annotations.copy(),
            fingerprint=fingerprint,
        )

        self._active_alerts[fingerprint] = alert

        # Send notifications
        for channel in self._channels:
            try:
                await channel.send(alert)
            except Exception as e:
                logger.error(f"Notification channel failed: {e}")

        logger.warning(
            "Alert fired: %(alert_name)s",
            extra={
                "alert_name": rule.name,
                "severity": rule.severity.value,
                "fingerprint": fingerprint,
            },
        )

    async def _resolve_if_needed(self, rule_name: str) -> None:
        """Resolve alerts for a rule if condition is no longer true."""
        to_resolve = []
        for fingerprint, alert in self._active_alerts.items():
            if alert.name == rule_name and alert.status == AlertStatus.FIRING:
                to_resolve.append(fingerprint)

        for fingerprint in to_resolve:
            await self._resolve_alert(fingerprint)

    async def _resolve_alert(self, fingerprint: str) -> None:
        """Resolve an active alert."""
        alert = self._active_alerts.get(fingerprint)
        if not alert or alert.status != AlertStatus.FIRING:
            return

        alert.status = AlertStatus.RESOLVED
        alert.ends_at = datetime.now(timezone.utc).isoformat()

        # Send resolution notifications
        for channel in self._channels:
            try:
                await channel.send_resolved(alert)
            except Exception as e:
                logger.error(f"Resolution notification failed: {e}")

        logger.info(
            "Alert resolved: %(alert_name)s",
            extra={
                "alert_name": alert.name,
                "fingerprint": fingerprint,
            },
        )

    def _generate_fingerprint(self, rule: AlertRule) -> str:
        """Generate fingerprint for rule."""
        import hashlib
        label_str = "|".join(f"{k}={v}" for k, v in sorted(rule.labels.items()))
        return hashlib.sha256(f"{rule.name}|{label_str}".encode()).hexdigest()[:16]

    def _is_silenced(self, rule_name: str) -> bool:
        """Check if rule is silenced."""
        for fingerprint, silence_until in list(self._silences.items()):
            if time.time() > silence_until:
                del self._silences[fingerprint]
            elif fingerprint.startswith(rule_name):
                return True
        return False

    def silence(self, fingerprint: str, duration: float = 3600) -> None:
        """Silence an alert for duration seconds."""
        self._silences[fingerprint] = time.time() + duration

    def unsilence(self, fingerprint: str) -> None:
        """Remove silence for an alert."""
        self._silences.pop(fingerprint, None)

    def get_active_alerts(self) -> List[Alert]:
        """Get all active (firing) alerts."""
        return [a for a in self._active_alerts.values() if a.status == AlertStatus.FIRING]

    def get_all_alerts(self) -> List[Alert]:
        """Get all alerts (including resolved)."""
        return list(self._active_alerts.values())

    def acknowledge(self, fingerprint: str) -> bool:
        """Acknowledge an alert."""
        alert = self._active_alerts.get(fingerprint)
        if alert and alert.status == AlertStatus.FIRING:
            alert.status = AlertStatus.ACKNOWLEDGED
            return True
        return False


# =============================================================================
# BUILT-IN ALERT RULES
# =============================================================================

def create_default_rules(
    health_check_fn: Optional[Callable[[], Awaitable[Dict[str, Any]]]] = None,
) -> List[AlertRule]:
    """Create default alert rules."""
    rules = []

    # High error rate
    async def check_error_rate():
        # This would integrate with metrics
        return False  # Placeholder

    rules.append(AlertRule(
        name="high_error_rate",
        condition=check_error_rate,
        severity=AlertSeverity.CRITICAL,
        message="Error rate exceeds 5%",
        labels={"component": "api"},
        annotations={"runbook": "https://wiki.example.com/runbooks/high-error-rate"},
        for_duration=60,
        interval=30,
    ))

    # High latency
    async def check_high_latency():
        return False  # Placeholder

    rules.append(AlertRule(
        name="high_latency",
        condition=check_high_latency,
        severity=AlertSeverity.WARNING,
        message="P99 latency exceeds 5s",
        labels={"component": "api"},
        for_duration=120,
        interval=60,
    ))

    # Database down
    async def check_database():
        if health_check_fn:
            result = await health_check_fn()
            for check in result.get("checks", []):
                if check["name"] == "mongodb" and check["status"] == "unhealthy":
                    return True
        return False

    rules.append(AlertRule(
        name="database_down",
        condition=check_database,
        severity=AlertSeverity.CRITICAL,
        message="MongoDB connection failed",
        labels={"component": "database"},
        annotations={"runbook": "https://wiki.example.com/runbooks/database-down"},
        for_duration=30,
        interval=30,
    ))

    # Pinecone down
    async def check_pinecone():
        if health_check_fn:
            result = await health_check_fn()
            for check in result.get("checks", []):
                if check["name"] == "pinecone" and check["status"] == "unhealthy":
                    return True
        return False

    rules.append(AlertRule(
        name="vector_store_down",
        condition=check_pinecone,
        severity=AlertSeverity.CRITICAL,
        message="Pinecone connection failed",
        labels={"component": "vector_store"},
        for_duration=30,
        interval=30,
    ))

    # LLM provider down
    async def check_llm_provider():
        if health_check_fn:
            result = await health_check_fn()
            for check in result.get("checks", []):
                if check["name"] in ("groq", "openrouter") and check["status"] == "unhealthy":
                    return True
        return False

    rules.append(AlertRule(
        name="llm_provider_down",
        condition=check_llm_provider,
        severity=AlertSeverity.CRITICAL,
        message="LLM provider unavailable",
        labels={"component": "llm"},
        for_duration=60,
        interval=60,
    ))

    # High memory usage
    async def check_memory():
        if health_check_fn:
            result = await health_check_fn()
            for check in result.get("checks", []):
                if check["name"] == "memory" and check["status"] == "unhealthy":
                    return True
        return False

    rules.append(AlertRule(
        name="high_memory",
        condition=check_memory,
        severity=AlertSeverity.WARNING,
        message="Memory usage exceeds 90%",
        labels={"component": "system"},
        for_duration=300,
        interval=60,
    ))

    # High disk usage
    async def check_disk():
        if health_check_fn:
            result = await health_check_fn()
            for check in result.get("checks", []):
                if check["name"] == "disk" and check["status"] == "unhealthy":
                    return True
        return False

    rules.append(AlertRule(
        name="high_disk",
        condition=check_disk,
        severity=AlertSeverity.WARNING,
        message="Disk usage exceeds 95%",
        labels={"component": "system"},
        for_duration=300,
        interval=300,
    ))

    # Active requests overload
    async def check_active_requests():
        if health_check_fn:
            result = await health_check_fn()
            for check in result.get("checks", []):
                if check["name"] == "active_requests" and check["status"] == "unhealthy":
                    return True
        return False

    rules.append(AlertRule(
        name="request_overload",
        condition=check_active_requests,
        severity=AlertSeverity.WARNING,
        message="Active requests exceed threshold",
        labels={"component": "api"},
        for_duration=60,
        interval=30,
    ))

    return rules


# Global alert manager
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
        _alert_manager.add_default_channels()
    return _alert_manager


async def init_alerting(
    health_check_fn: Optional[Callable[[], Awaitable[Dict[str, Any]]]] = None,
    webhook_url: Optional[str] = None,
    email_config: Optional[Dict[str, Any]] = None,
) -> AlertManager:
    """Initialize alert manager with default rules and channels."""
    manager = get_alert_manager()

    # Add default rules
    for rule in create_default_rules(health_check_fn):
        manager.add_rule(rule)

    # Add webhook if configured
    if webhook_url:
        manager.add_channel(WebhookNotificationChannel(webhook_url))

    # Add email if configured
    if email_config:
        manager.add_channel(EmailNotificationChannel(**email_config))

    await manager.start()
    return manager


async def shutdown_alerting() -> None:
    """Shutdown alert manager."""
    global _alert_manager
    if _alert_manager:
        await _alert_manager.stop()
        _alert_manager = None


__all__ = [
    "AlertSeverity",
    "AlertStatus",
    "Alert",
    "AlertRule",
    "NotificationChannel",
    "LogNotificationChannel",
    "WebhookNotificationChannel",
    "EmailNotificationChannel",
    "AlertManager",
    "create_default_rules",
    "get_alert_manager",
    "init_alerting",
    "shutdown_alerting",
]