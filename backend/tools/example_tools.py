"""Example tools for Kuro AI demonstrating the tool registry framework."""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .registry import (
    register_tool,
    ToolParameter,
    ToolCapability,
    RiskTier,
    ToolDefinition,
    ToolResult,
    ToolCall,
    get_tool_registry,
)

logger = logging.getLogger(__name__)


# =============================================================================
# T0 TOOLS - Pure Calculation / Local Formatting
# =============================================================================

async def calculate_expression(expression: str) -> Dict[str, Any]:
    """Safely evaluate a mathematical expression."""
    import ast
    import operator
    
    # Only allow safe operations
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    def eval_node(node):
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.BinOp):
            left = eval_node(node.left)
            right = eval_node(node.right)
            op_type = type(node.op)
            if op_type in allowed_operators:
                return allowed_operators[op_type](left, right)
            raise ValueError(f"Unsupported operator: {op_type}")
        elif isinstance(node, ast.UnaryOp):
            operand = eval_node(node.operand)
            op_type = type(node.op)
            if op_type in allowed_operators:
                return allowed_operators[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type}")
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")
    
    try:
        tree = ast.parse(expression, mode='eval')
        result = eval_node(tree.body)
        return {"result": result, "expression": expression}
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")


register_tool(
    name="calculate",
    version="1.0.0",
    description="Safely evaluate a mathematical expression (basic arithmetic only)",
    parameters=[
        ToolParameter(
            name="expression",
            type="string",
            description="Mathematical expression to evaluate (e.g., '2 + 3 * 4', '(10 + 5) / 3')",
            required=True,
            pattern=r"^[\d\s+\-*/().]+$",
            max_length=200,
        ),
    ],
    required_capabilities=[],  # No capabilities needed for pure calculation
    risk_tier=RiskTier.T0,
    execution_func=calculate_expression,
    tags=["math", "calculation", "utility"],
)


# =============================================================================
# T1 TOOLS - Read-Only User Data
# =============================================================================

async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile information (read-only)."""
    # This would typically query the database
    # For now, return mock data
    return {
        "user_id": user_id,
        "name": "User",
        "created_at": "2024-01-01T00:00:00Z",
        "preferences": {
            "language": "en",
            "theme": "dark",
        },
    }


register_tool(
    name="get_profile",
    version="1.0.0",
    description="Get the authenticated user's profile information",
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User ID (must match authenticated user)",
            required=True,
        ),
    ],
    required_capabilities=[ToolCapability.PROFILE_READ],
    risk_tier=RiskTier.T1,
    execution_func=get_user_profile,
    tags=["profile", "read", "user"],
)


async def list_user_sessions(user_id: str, limit: int = 20) -> Dict[str, Any]:
    """List user's chat sessions (read-only)."""
    # Mock implementation
    return {
        "sessions": [
            {"session_id": "sess_1", "title": "Chat about Python", "created_at": "2024-01-15T10:00:00Z", "message_count": 5},
            {"session_id": "sess_2", "title": "Project planning", "created_at": "2024-01-14T15:30:00Z", "message_count": 12},
        ][:limit],
        "total": 2,
    }


register_tool(
    name="list_sessions",
    version="1.0.0",
    description="List the authenticated user's chat sessions",
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User ID (must match authenticated user)",
            required=True,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of sessions to return",
            required=False,
            default=20,
            minimum=1,
            maximum=100,
        ),
    ],
    required_capabilities=[ToolCapability.SESSION_READ],
    risk_tier=RiskTier.T1,
    execution_func=list_user_sessions,
    tags=["session", "read", "list"],
)


async def search_memories(user_id: str, query: str, limit: int = 10) -> Dict[str, Any]:
    """Search user's memories (read-only)."""
    # Mock implementation
    return {
        "memories": [
            {"id": "mem_1", "text": "User likes Python programming", "score": 0.95, "category": "preference"},
            {"id": "mem_2", "text": "User is working on a web project", "score": 0.87, "category": "project"},
        ][:limit],
        "query": query,
    }


register_tool(
    name="search_memories",
    version="1.0.0",
    description="Search the authenticated user's long-term memories",
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User ID (must match authenticated user)",
            required=True,
        ),
        ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
            min_length=1,
            max_length=500,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of results",
            required=False,
            default=10,
            minimum=1,
            maximum=50,
        ),
    ],
    required_capabilities=[ToolCapability.MEMORY_READ],
    risk_tier=RiskTier.T1,
    execution_func=search_memories,
    tags=["memory", "search", "read"],
)


# =============================================================================
# T2 TOOLS - Reversible Local Mutation
# =============================================================================

async def update_profile(user_id: str, name: Optional[str] = None, preferences: Optional[Dict] = None) -> Dict[str, Any]:
    """Update user profile (reversible mutation)."""
    # Mock implementation - in reality would update database
    updated = {}
    if name:
        updated["name"] = name
    if preferences:
        updated["preferences"] = preferences
    
    return {
        "success": True,
        "updated_fields": list(updated.keys()),
        "user_id": user_id,
        "reversible": True,
        "revert_instructions": "Use the same tool with previous values to revert",
    }


register_tool(
    name="update_profile",
    version="1.0.0",
    description="Update the authenticated user's profile (reversible)",
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User ID (must match authenticated user)",
            required=True,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="New display name",
            required=False,
            max_length=100,
        ),
        ToolParameter(
            name="preferences",
            type="object",
            description="User preferences object",
            required=False,
        ),
    ],
    required_capabilities=[ToolCapability.PROFILE_WRITE],
    risk_tier=RiskTier.T2,
    execution_func=update_profile,
    reversible=True,
    tags=["profile", "write", "update"],
    idempotency_key_param="user_id",
)


async def create_memory(user_id: str, text: str, category: str = "general", importance: float = 0.5) -> Dict[str, Any]:
    """Create a new memory for the user."""
    import uuid
    memory_id = str(uuid.uuid4())
    return {
        "success": True,
        "memory_id": memory_id,
        "text": text,
        "category": category,
        "importance": importance,
        "created_at": datetime.utcnow().isoformat(),
        "reversible": True,
        "revert_instructions": f"Use delete_memory with memory_id={memory_id}",
    }


register_tool(
    name="create_memory",
    version="1.0.0",
    description="Create a new long-term memory for the authenticated user",
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User ID (must match authenticated user)",
            required=True,
        ),
        ToolParameter(
            name="text",
            type="string",
            description="Memory content",
            required=True,
            min_length=1,
            max_length=5000,
        ),
        ToolParameter(
            name="category",
            type="string",
            description="Memory category",
            required=False,
            default="general",
            enum=["general", "preference", "project", "fact", "contact", "note"],
        ),
        ToolParameter(
            name="importance",
            type="number",
            description="Importance score (0.0 to 1.0)",
            required=False,
            default=0.5,
            minimum=0.0,
            maximum=1.0,
        ),
    ],
    required_capabilities=[ToolCapability.MEMORY_WRITE],
    risk_tier=RiskTier.T2,
    execution_func=create_memory,
    reversible=True,
    tags=["memory", "write", "create"],
    idempotency_key_param="user_id",
)


# =============================================================================
# T3 TOOLS - External Side Effects (Requires Confirmation)
# =============================================================================

async def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Search the web (external side effect - requires confirmation)."""
    # This would call an actual search API
    # For now, return mock results
    return {
        "query": query,
        "results": [
            {"title": f"Result for '{query}'", "url": "https://example.com/1", "snippet": "Sample result..."},
            {"title": f"More about '{query}'", "url": "https://example.com/2", "snippet": "Another result..."},
        ][:max_results],
        "searched_at": datetime.utcnow().isoformat(),
    }


register_tool(
    name="web_search",
    version="1.0.0",
    description="Search the web for information (external API call, requires confirmation)",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="Search query",
            required=True,
            min_length=1,
            max_length=500,
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results",
            required=False,
            default=5,
            minimum=1,
            maximum=20,
        ),
    ],
    required_capabilities=[ToolCapability.WEB_SEARCH],
    risk_tier=RiskTier.T3,
    execution_func=web_search,
    requires_confirmation=True,
    confirmation_message="This will perform a web search via external API. Confirm?",
    tags=["web", "search", "external"],
    rate_limit=(20, 60),  # 20 requests per minute
)


async def send_email(to: str, subject: str, body: str, user_id: str) -> Dict[str, Any]:
    """Send an email (external side effect - requires confirmation)."""
    # This would call an actual email API
    return {
        "success": True,
        "message_id": f"msg_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "to": to,
        "subject": subject,
        "sent_at": datetime.utcnow().isoformat(),
    }


register_tool(
    name="send_email",
    version="1.0.0",
    description="Send an email on behalf of the user (requires explicit confirmation)",
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User ID (must match authenticated user)",
            required=True,
        ),
        ToolParameter(
            name="to",
            type="string",
            description="Recipient email address",
            required=True,
            pattern=r"^[^@]+@[^@]+\.[^@]+$",
        ),
        ToolParameter(
            name="subject",
            type="string",
            description="Email subject",
            required=True,
            max_length=200,
        ),
        ToolParameter(
            name="body",
            type="string",
            description="Email body",
            required=True,
            max_length=10000,
        ),
    ],
    required_capabilities=[ToolCapability.MESSAGE_SEND],
    risk_tier=RiskTier.T3,
    execution_func=send_email,
    requires_confirmation=True,
    confirmation_message="This will send an email to the specified recipient. Confirm?",
    tags=["email", "send", "external", "communication"],
    rate_limit=(10, 3600),  # 10 emails per hour
)


# =============================================================================
# T4 TOOLS - High-Impact / Irreversible
# =============================================================================

async def delete_user_account(user_id: str, confirmation_phrase: str) -> Dict[str, Any]:
    """Delete user account (high-impact, irreversible)."""
    expected_phrase = "DELETE MY ACCOUNT PERMANENTLY"
    if confirmation_phrase != expected_phrase:
        raise ValueError(f"Confirmation phrase must be exactly: '{expected_phrase}'")
    
    # This would actually delete the account
    return {
        "success": True,
        "message": "Account deletion initiated. This action is irreversible.",
        "user_id": user_id,
        "deleted_at": datetime.utcnow().isoformat(),
        "irreversible": True,
    }


register_tool(
    name="delete_account",
    version="1.0.0",
    description="Permanently delete the authenticated user's account (irreversible, requires strong confirmation)",
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User ID (must match authenticated user)",
            required=True,
        ),
        ToolParameter(
            name="confirmation_phrase",
            type="string",
            description="Must type exactly: 'DELETE MY ACCOUNT PERMANENTLY'",
            required=True,
        ),
    ],
    required_capabilities=[ToolCapability.PROFILE_WRITE, ToolCapability.MEMORY_DELETE, ToolCapability.SESSION_DELETE],
    risk_tier=RiskTier.T4,
    execution_func=delete_user_account,
    requires_confirmation=True,
    confirmation_message="This will PERMANENTLY DELETE your account and all data. This cannot be undone. Type 'DELETE MY ACCOUNT PERMANENTLY' to confirm.",
    tags=["account", "delete", "irreversible", "destructive"],
)


# =============================================================================
# Initialize all tools on module import
# =============================================================================

def init_tools() -> None:
    """Initialize all tools. Call this on application startup."""
    # Tools are registered via @register_tool decorator on import
    registry = get_tool_registry()
    logger.info(f"Initialized {len(registry.list_tools())} tools:")
    for tool in registry.list_tools():
        logger.info(f"  - {tool.name} (tier={tool.risk_tier.value}, caps={[c.value for c in tool.required_capabilities]})")


# =============================================================================
# Tool Execution Helper
# =============================================================================

async def execute_tool_for_user(
    user_id: str,
    tool_name: str,
    arguments: Dict[str, Any],
    capabilities: Optional[List[ToolCapability]] = None,
    confirmation_token: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> ToolResult:
    """Execute a tool on behalf of a user with proper context."""
    from tools.registry import ToolCall, ToolCapability, execute_tool
    
    call = ToolCall(
        tool_name=tool_name,
        arguments=arguments,
        caller_user_id=user_id,
        caller_capabilities=set(capabilities) if capabilities else set(),
        confirmation_token=confirmation_token,
        idempotency_key=idempotency_key,
    )
    
    return await execute_tool(call)


__all__ = [
    "init_tools",
    "execute_tool_for_user",
    "calculate_expression",
    "get_user_profile",
    "list_user_sessions",
    "search_memories",
    "update_profile",
    "create_memory",
    "web_search",
    "send_email",
    "delete_user_account",
]