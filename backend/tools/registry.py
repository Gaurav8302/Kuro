"""Central Tool Registry and Execution Framework for Kuro AI.

Provides:
- Tool registration with strict schemas
- Permission-based authorization (capabilities)
- Risk tier enforcement (T0-T4)
- Confirmation requirements for consequential actions
- SSRF protection for network tools
- Idempotency for side-effecting operations
- Audit logging
"""

import json
import logging
import hashlib
import time
import re
import ipaddress
import socket
import asyncio
from typing import Dict, List, Optional, Any, Set, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from functools import wraps
import uuid
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

class RiskTier(Enum):
    """Risk tiers for tool operations."""
    T0 = "t0"  # Pure calculation/local formatting - schema validation only
    T1 = "t1"  # Read-only user data - auth + owner check + audit
    T2 = "t2"  # Reversible local mutation - explicit scope + undo where possible
    T3 = "t3"  # External side effects - explicit user confirmation required
    T4 = "t4"  # High-impact/irreversible - strong confirmation + narrow allowlist


class ToolCapability(Enum):
    """Capabilities required to execute tools."""
    PROFILE_READ = "profile.read"
    PROFILE_WRITE = "profile.write"
    MEMORY_READ = "memory.read"
    MEMORY_WRITE = "memory.write"
    MEMORY_DELETE = "memory.delete"
    SESSION_READ = "session.read"
    SESSION_WRITE = "session.write"
    SESSION_DELETE = "session.delete"
    WEB_SEARCH = "web.search"
    WEB_FETCH = "web.fetch"
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    CODE_EXEC = "code.exec"
    MESSAGE_SEND = "message.send"
    CALENDAR_READ = "calendar.read"
    CALENDAR_WRITE = "calendar.write"
    SYSTEM_SETTINGS = "system.settings"
    ADMIN_ACTION = "admin.action"


@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None


@dataclass
class ToolDefinition:
    """Complete tool definition."""
    name: str
    version: str
    description: str
    parameters: List[ToolParameter]
    required_capabilities: List[ToolCapability]
    risk_tier: RiskTier
    reads_data: bool = False
    writes_data: bool = False
    external_side_effect: bool = False
    reversible: bool = False
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None
    rate_limit: Optional[Tuple[int, int]] = None  # (max_requests, window_seconds)
    timeout_seconds: int = 30
    output_size_limit: int = 10000
    idempotency_key_param: Optional[str] = None
    allowed_environments: List[str] = field(default_factory=lambda: ["production", "staging", "development"])
    tags: List[str] = field(default_factory=list)
    execution_func: Optional[Callable] = None  # Set at registration


@dataclass
class ToolCall:
    """A tool call request."""
    tool_name: str
    arguments: Dict[str, Any]
    idempotency_key: Optional[str] = None
    confirmation_token: Optional[str] = None
    caller_user_id: Optional[str] = None
    caller_capabilities: Set[ToolCapability] = field(default_factory=set)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    result: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: int = 0
    idempotency_key: Optional[str] = None
    confirmation_required: bool = False
    confirmation_message: Optional[str] = None
    confirmation_token: Optional[str] = None
    audit_data: Dict[str, Any] = field(default_factory=dict)


class ToolExecutionError(Exception):
    """Tool execution error with code."""
    def __init__(self, message: str, error_code: str = "execution_error"):
        super().__init__(message)
        self.error_code = error_code


# =============================================================================
# SSRF PROTECTION
# =============================================================================

# Private/reserved IP ranges that must be blocked
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local
    ipaddress.ip_network("224.0.0.0/4"),      # Multicast
    ipaddress.ip_network("240.0.0.0/4"),      # Reserved
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),         # IPv6 private
]

# Cloud metadata endpoints to block
BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata",
    "169.254.169.254",  # AWS/GCP/Azure metadata
    "metadata.azure.com",
    "metadata.nginx",
}

# Allowed schemes
ALLOWED_SCHEMES = {"https", "http"}


def is_ip_allowed(ip_str: str) -> bool:
    """Check if an IP address is allowed (not in blocked ranges)."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for blocked_range in BLOCKED_IP_RANGES:
            if ip in blocked_range:
                return False
        return True
    except ValueError:
        return False


def is_hostname_allowed(hostname: str) -> bool:
    """Check if a hostname is allowed."""
    hostname_lower = hostname.lower().rstrip(".")
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False
    # Block internal-style hostnames
    if any(h in hostname_lower for h in [".internal", ".local", ".lan", "localhost"]):
        return False
    return True


async def resolve_and_validate_url(url: str, allowed_schemes: Set[str] = None) -> Tuple[bool, str, Optional[str]]:
    """Resolve DNS and validate the resolved IP is allowed.
    
    Returns: (is_allowed, resolved_url_or_original, error_message)
    """
    allowed_schemes = allowed_schemes or ALLOWED_SCHEMES
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            return False, url, f"Scheme '{parsed.scheme}' not allowed"
        
        hostname = parsed.hostname or ""
        if not is_hostname_allowed(hostname):
            return False, url, f"Hostname '{hostname}' is blocked"
        
        # Resolve DNS
        try:
            # Get all IPs for the hostname
            infos = socket.getaddrinfo(hostname, None)
            resolved_ips = []
            for info in infos:
                # info is a tuple: (family, type, proto, canonname, sockaddr)
                # sockaddr is (ip, port) for IPv4 or (ip, port, flowinfo, scopeid) for IPv6
                sockaddr = info[4]
                ip = sockaddr[0]
                resolved_ips.append(ip)
            
            for ip in resolved_ips:
                if not is_ip_allowed(ip):
                    return False, url, f"Resolved IP '{ip}' is in blocked range"
            
            return True, url, None
        except socket.gaierror as e:
            return False, url, f"DNS resolution failed: {e}"
            
    except Exception as e:
        return False, url, f"URL validation failed: {e}"


def validate_redirect_url(url: str, original_url: str, allowed_schemes: Set[str] = None) -> Tuple[bool, str]:
    """Validate a redirect URL against SSRF protections."""
    allowed_schemes = allowed_schemes or ALLOWED_SCHEMES
    
    try:
        parsed = urlparse(url)
        if parsed.scheme not in allowed_schemes:
            return False, f"Redirect scheme '{parsed.scheme}' not allowed"
        
        # Don't allow redirect to blocked hostnames
        if not is_hostname_allowed(parsed.hostname or ""):
            return False, f"Redirect to blocked hostname '{parsed.hostname}'"
        
        # Don't allow redirect to very different domain (optional)
        original_host = urlparse(original_url).hostname or ""
        if parsed.hostname != original_host:
            # Cross-domain redirect - could allow with warning
            logger.warning(f"Cross-domain redirect from {original_host} to {parsed.hostname}")
        
        return True, ""
    except Exception as e:
        return False, f"Redirect validation failed: {e}"


# =============================================================================
# TOOL REGISTRY
# =============================================================================

class ToolRegistry:
    """Central registry for all tools."""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._capability_tools: Dict[ToolCapability, Set[str]] = {}
    
    def register(self, definition: ToolDefinition) -> None:
        """Register a tool definition."""
        if definition.name in self._tools:
            raise ValueError(f"Tool '{definition.name}' already registered")
        
        # Validate definition
        if not definition.execution_func:
            raise ValueError(f"Tool '{definition.name}' missing execution function")
        
        # Set confirmation requirement based on risk tier
        if definition.risk_tier in (RiskTier.T3, RiskTier.T4):
            definition.requires_confirmation = True
            if not definition.confirmation_message:
                definition.confirmation_message = f"Confirm execution of '{definition.name}'?"
        
        self._tools[definition.name] = definition
        
        # Index by capability
        for cap in definition.required_capabilities:
            if cap not in self._capability_tools:
                self._capability_tools[cap] = set()
            self._capability_tools[cap].add(definition.name)
        
        logger.info(f"Registered tool: {definition.name} (tier={definition.risk_tier.value}, caps={[c.value for c in definition.required_capabilities]})")
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self, capability: Optional[ToolCapability] = None) -> List[ToolDefinition]:
        """List all tools, optionally filtered by capability."""
        if capability:
            tool_names = self._capability_tools.get(capability, set())
            return [self._tools[name] for name in tool_names if name in self._tools]
        return list(self._tools.values())
    
    def get_tools_by_capability(self, capabilities: Set[ToolCapability]) -> List[ToolDefinition]:
        """Get tools that require any of the given capabilities."""
        tool_names = set()
        for cap in capabilities:
            tool_names.update(self._capability_tools.get(cap, set()))
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def validate_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate arguments against tool schema."""
        tool = self.get(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"
        
        # Check required parameters
        for param in tool.parameters:
            if param.required and param.name not in arguments:
                return False, f"Missing required parameter: {param.name}"
            
            if param.name in arguments:
                value = arguments[param.name]
                # Type validation
                valid, err = self._validate_type(param, value)
                if not valid:
                    return False, f"Parameter '{param.name}': {err}"
                
                # Enum validation
                if param.enum and value not in param.enum:
                    return False, f"Parameter '{param.name}' must be one of: {param.enum}"
                
                # Range validation
                if isinstance(value, (int, float)):
                    if param.minimum is not None and value < param.minimum:
                        return False, f"Parameter '{param.name}' must be >= {param.minimum}"
                    if param.maximum is not None and value > param.maximum:
                        return False, f"Parameter '{param.name}' must be <= {param.maximum}"
                
                # Length validation
                if isinstance(value, str):
                    if param.min_length is not None and len(value) < param.min_length:
                        return False, f"Parameter '{param.name}' must be at least {param.min_length} characters"
                    if param.max_length is not None and len(value) > param.max_length:
                        return False, f"Parameter '{param.name}' must be at most {param.max_length} characters"
                    if param.pattern and not re.match(param.pattern, value):
                        return False, f"Parameter '{param.name}' does not match pattern"
                
                if isinstance(value, list):
                    if param.min_length is not None and len(value) < param.min_length:
                        return False, f"Parameter '{param.name}' must have at least {param.min_length} items"
                    if param.max_length is not None and len(value) > param.max_length:
                        return False, f"Parameter '{param.name}' must have at most {param.max_length} items"
        
        # Reject unknown parameters
        known_params = {p.name for p in tool.parameters}
        unknown = set(arguments.keys()) - known_params
        if unknown:
            return False, f"Unknown parameters: {unknown}"
        
        return True, None
    
    def _validate_type(self, param: ToolParameter, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a value matches the parameter type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        expected_type = type_map.get(param.type)
        if expected_type and not isinstance(value, expected_type):
            return False, f"Expected {param.type}, got {type(value).__name__}"
        return True, None


# =============================================================================
# CONFIRMATION MANAGEMENT
# =============================================================================

class ConfirmationManager:
    """Manages user confirmations for consequential actions."""
    
    def __init__(self, ttl_seconds: int = 300):
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
    
    def create_confirmation(
        self,
        user_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        message: str,
        risk_tier: RiskTier
    ) -> str:
        """Create a pending confirmation request."""
        token = hashlib.sha256(f"{user_id}:{tool_name}:{time.time()}:{uuid.uuid4()}".encode()).hexdigest()[:32]
        
        self._pending[token] = {
            "user_id": user_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "message": message,
            "risk_tier": risk_tier.value,
            "created_at": time.time(),
            "expires_at": time.time() + self._ttl,
            "confirmed": False,
        }
        return token
    
    def get_confirmation(self, token: str) -> Optional[Dict[str, Any]]:
        """Get a pending confirmation."""
        confirmation = self._pending.get(token)
        if not confirmation:
            return None
        
        if time.time() > confirmation["expires_at"]:
            del self._pending[token]
            return None
        
        return confirmation
    
    def confirm(self, token: str) -> Tuple[bool, Optional[str]]:
        """Mark a confirmation as approved."""
        confirmation = self.get_confirmation(token)
        if not confirmation:
            return False, "Confirmation not found or expired"
        
        confirmation["confirmed"] = True
        confirmation["confirmed_at"] = time.time()
        return True, None
    
    def cancel(self, token: str) -> bool:
        """Cancel a pending confirmation."""
        if token in self._pending:
            del self._pending[token]
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """Remove expired confirmations."""
        now = time.time()
        expired = [token for token, c in self._pending.items() if now > c["expires_at"]]
        for token in expired:
            del self._pending[token]
        return len(expired)


# =============================================================================
# IDEMPOTENCY MANAGER
# =============================================================================

class IdempotencyManager:
    """Manages idempotency keys for side-effecting operations."""
    
    def __init__(self, ttl_seconds: int = 86400):  # 24 hours default
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
    
    def check_and_store(
        self,
        idempotency_key: str,
        user_id: str,
        tool_name: str,
        result: ToolResult
    ) -> Tuple[bool, Optional[ToolResult]]:
        """Check if key exists, if not store result. Returns (is_new, existing_result)."""
        if idempotency_key in self._keys:
            existing = self._keys[idempotency_key]
            if existing["user_id"] != user_id:
                return False, None  # Key belongs to different user
            if existing["tool_name"] != tool_name:
                return False, None  # Key used for different tool
            return False, ToolResult(**existing["result"])
        
        # Store new result
        self._keys[idempotency_key] = {
            "user_id": user_id,
            "tool_name": tool_name,
            "result": {
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "error_code": result.error_code,
                "execution_time_ms": result.execution_time_ms,
                "audit_data": result.audit_data,
            },
            "created_at": time.time(),
        }
        return True, None
    
    def get(self, idempotency_key: str, user_id: str) -> Optional[ToolResult]:
        """Get stored result for idempotency key."""
        if idempotency_key not in self._keys:
            return None
        existing = self._keys[idempotency_key]
        if existing["user_id"] != user_id:
            return None
        return ToolResult(**existing["result"])
    
    def cleanup_expired(self) -> int:
        """Remove expired keys."""
        now = time.time()
        expired = [
            key for key, data in self._keys.items()
            if now - data["created_at"] > self._ttl
        ]
        for key in expired:
            del self._keys[key]
        return len(expired)


# =============================================================================
# TOOL EXECUTOR
# =============================================================================

class ToolExecutor:
    """Executes tools with full safety checks."""
    
    def __init__(
        self,
        registry: ToolRegistry,
        confirmation_manager: ConfirmationManager,
        idempotency_manager: IdempotencyManager,
        audit_logger: Optional[Callable] = None
    ):
        self.registry = registry
        self.confirmation_manager = confirmation_manager
        self.idempotency_manager = idempotency_manager
        self.audit_logger = audit_logger
    
    async def execute(self, call: ToolCall) -> ToolResult:
        """Execute a tool call with full safety checks."""
        start_time = time.time()
        
        # 1. Get tool definition
        tool = self.registry.get(call.tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{call.tool_name}' not found",
                error_code="tool_not_found",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 2. Validate environment
        env = "production"  # Could be configured
        if env not in tool.allowed_environments:
            return ToolResult(
                success=False,
                error=f"Tool not allowed in environment '{env}'",
                error_code="environment_not_allowed",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 3. Check capabilities
        if not self._check_capabilities(tool, call.caller_capabilities):
            return ToolResult(
                success=False,
                error=f"Insufficient capabilities for tool '{call.tool_name}'",
                error_code="insufficient_capabilities",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 4. Validate arguments
        valid, err = self.registry.validate_arguments(call.tool_name, call.arguments)
        if not valid:
            return ToolResult(
                success=False,
                error=f"Invalid arguments: {err}",
                error_code="invalid_arguments",
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 5. Check idempotency
        idempotency_key = call.idempotency_key or call.arguments.get(tool.idempotency_key_param) if tool.idempotency_key_param else None
        if idempotency_key and call.caller_user_id:
            is_new, existing = self.idempotency_manager.check_and_store(
                idempotency_key, call.caller_user_id, call.tool_name,
                ToolResult(success=False)  # Placeholder
            )
            if not is_new and existing:
                logger.info(f"Idempotent replay for {call.tool_name} with key {idempotency_key[:8]}")
                return existing
        
        # 6. Check confirmation for T3/T4
        if tool.requires_confirmation and tool.risk_tier in (RiskTier.T3, RiskTier.T4):
            if not call.confirmation_token:
                # Create confirmation request
                token = self.confirmation_manager.create_confirmation(
                    user_id=call.caller_user_id or "unknown",
                    tool_name=call.tool_name,
                    arguments=call.arguments,
                    message=tool.confirmation_message or f"Confirm execution of '{call.tool_name}'?",
                    risk_tier=tool.risk_tier
                )
                return ToolResult(
                    success=False,
                    error="Confirmation required",
                    error_code="confirmation_required",
                    confirmation_required=True,
                    confirmation_message=tool.confirmation_message,
                    confirmation_token=token,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            else:
                # Verify confirmation
                confirmed, err = self.confirmation_manager.confirm(call.confirmation_token)
                if not confirmed:
                    return ToolResult(
                        success=False,
                        error=f"Confirmation failed: {err}",
                        error_code="confirmation_failed",
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
        
        # 7. Apply rate limiting (if configured)
        if tool.rate_limit and call.caller_user_id:
            # Rate limiting would be applied here via the rate limiter
            pass
        
        # 8. Execute the tool
        try:
            if tool.execution_func:
                # Check if async
                if asyncio.iscoroutinefunction(tool.execution_func):
                    result = await asyncio.wait_for(
                        tool.execution_func(**call.arguments),
                        timeout=tool.timeout_seconds
                    )
                else:
                    result = tool.execution_func(**call.arguments)
            else:
                raise ToolExecutionError("Tool has no execution function", "no_execution_func")
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Wrap result
            if isinstance(result, ToolResult):
                tool_result = result
                tool_result.execution_time_ms = execution_time
            else:
                tool_result = ToolResult(
                    success=True,
                    result=result,
                    execution_time_ms=execution_time
                )
            
            # Store idempotency result
            if idempotency_key and call.caller_user_id:
                self.idempotency_manager.check_and_store(
                    idempotency_key, call.caller_user_id, call.tool_name, tool_result
                )
            
            # 9. Audit log
            self._audit_log(call, tool_result, execution_time)
            
            return tool_result
            
        except asyncio.TimeoutError:
            execution_time = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {tool.timeout_seconds}s",
                error_code="timeout",
                execution_time_ms=execution_time
            )
        except ToolExecutionError as e:
            execution_time = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                error=str(e),
                error_code=e.error_code,
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Tool execution error for {call.tool_name}: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"Internal execution error: {str(e)}",
                error_code="execution_error",
                execution_time_ms=execution_time
            )
    
    def _check_capabilities(self, tool: ToolDefinition, caller_caps: Set[ToolCapability]) -> bool:
        """Check if caller has required capabilities."""
        if not tool.required_capabilities:
            return True  # No capabilities required
        
        caller_cap_set = set(caller_caps)
        return all(cap in caller_cap_set for cap in tool.required_capabilities)
    
    def _audit_log(self, call: ToolCall, result: ToolResult, execution_time: int) -> None:
        """Log tool execution for audit."""
        audit_entry = {
            "timestamp": time.time(),
            "request_id": call.request_id,
            "tool_name": call.tool_name,
            "user_id": call.caller_user_id,
            "arguments": call.arguments,
            "success": result.success,
            "error": result.error,
            "error_code": result.error_code,
            "execution_time_ms": execution_time,
            "idempotency_key": call.idempotency_key,
            "confirmation_token": call.confirmation_token,
        }
        
        if self.audit_logger:
            try:
                self.audit_logger(audit_entry)
            except Exception as e:
                logger.error(f"Audit logging failed: {e}")
        else:
            logger.info(f"TOOL_AUDIT: {json.dumps(audit_entry)}")


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

_tool_registry: Optional[ToolRegistry] = None
_confirmation_manager: Optional[ConfirmationManager] = None
_idempotency_manager: Optional[IdempotencyManager] = None
_tool_executor: Optional[ToolExecutor] = None


def get_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry


def get_confirmation_manager() -> ConfirmationManager:
    global _confirmation_manager
    if _confirmation_manager is None:
        _confirmation_manager = ConfirmationManager()
    return _confirmation_manager


def get_idempotency_manager() -> IdempotencyManager:
    global _idempotency_manager
    if _idempotency_manager is None:
        _idempotency_manager = IdempotencyManager()
    return _idempotency_manager


def get_tool_executor() -> ToolExecutor:
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor(
            registry=get_tool_registry(),
            confirmation_manager=get_confirmation_manager(),
            idempotency_manager=get_idempotency_manager(),
        )
    return _tool_executor


# =============================================================================
# TOOL REGISTRATION HELPERS
# =============================================================================

def register_tool(
    name: str,
    version: str,
    description: str,
    parameters: List[ToolParameter],
    required_capabilities: List[ToolCapability],
    risk_tier: RiskTier,
    execution_func: Callable,
    **kwargs
) -> None:
    """Convenience function to register a tool."""
    definition = ToolDefinition(
        name=name,
        version=version,
        description=description,
        parameters=parameters,
        required_capabilities=required_capabilities,
        risk_tier=risk_tier,
        execution_func=execution_func,
        **kwargs
    )
    get_tool_registry().register(definition)


async def execute_tool(call: ToolCall) -> ToolResult:
    """Convenience function to execute a tool."""
    return await get_tool_executor().execute(call)


__all__ = [
    # Enums
    "RiskTier",
    "ToolCapability",
    
    # Data classes
    "ToolParameter",
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "ToolExecutionError",
    
    # Core classes
    "ToolRegistry",
    "ConfirmationManager",
    "IdempotencyManager",
    "ToolExecutor",
    
    # SSRF
    "is_ip_allowed",
    "is_hostname_allowed",
    "resolve_and_validate_url",
    "validate_redirect_url",
    "BLOCKED_IP_RANGES",
    "BLOCKED_HOSTNAMES",
    "ALLOWED_SCHEMES",
    
    # Globals
    "get_tool_registry",
    "get_confirmation_manager",
    "get_idempotency_manager",
    "get_tool_executor",
    "register_tool",
    "execute_tool",
]