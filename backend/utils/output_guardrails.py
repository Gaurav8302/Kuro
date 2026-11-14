"""Output Guardrails and Response Validation.

Provides comprehensive output validation for AI responses:
- Schema/format validation
- Safety policy enforcement
- Citation/grounding validation
- Secret/credential detection
- Tool call validation
- Markdown/HTML sanitization
- Structured output validation
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Result of output validation."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    RETRY = "retry"


class ViolationType(Enum):
    """Types of validation violations."""
    SCHEMA_MISMATCH = "schema_mismatch"
    SAFETY_VIOLATION = "safety_violation"
    SECRET_LEAKAGE = "secret_leakage"
    CITATION_ERROR = "citation_error"
    TOOL_CLAIM_ERROR = "tool_claim_error"
    FORMAT_ERROR = "format_error"
    LENGTH_EXCEEDED = "length_exceeded"
    UNSAFE_RENDERING = "unsafe_rendering"
    HALLUCINATION_RISK = "hallucination_risk"


@dataclass
class ValidationViolation:
    """A single validation violation."""
    violation_type: ViolationType
    message: str
    severity: str  # "low", "medium", "high", "critical"
    location: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete validation report for a response."""
    result: ValidationResult
    violations: List[ValidationViolation]
    sanitized_response: str
    metadata: Dict[str, Any]


# =============================================================================
# SAFETY POLICY PATTERNS
# =============================================================================

# Secrets/credentials that must never appear in output
SECRET_PATTERNS = [
    (r"(?i)(?:api[_\s]?key|apikey)\s*[:=]\s*[A-Za-z0-9_\-]{16,}", "API key"),
    (r"(?i)(?:secret[_\s]?key|secretkey)\s*[:=]\s*[A-Za-z0-9_\-]{16,}", "Secret key"),
    (r"(?i)(?:access[_\s]?token|accesstoken)\s*[:=]\s*[A-Za-z0-9_\-\.]{20,}", "Access token"),
    (r"(?i)(?:bearer\s+token)\s*[:=]\s*[A-Za-z0-9_\-\.]{20,}", "Bearer token"),
    (r"(?i)password\s*[:=]\s*[^\s]{8,}", "Password"),
    (r"(?i)(?:private[_\s]?key|privatekey)\s*[:=]\s*[A-Za-z0-9_\-\/+=]{32,}", "Private key"),
    (r"(?i)(?:ssh[_\s]?key|sshkey)\s*[:=]\s*[A-Za-z0-9_\-\/+=]{32,}", "SSH key"),
    (r"(?i)(?:database[_\s]?url|db[_\s]?url)\s*[:=]\s*[^\s]{16,}", "Database URL"),
    (r"(?i)(?:connection[_\s]?string)\s*[:=]\s*[^\s]{16,}", "Connection string"),
    (r"(?i)(?:webhook[_\s]?url|webhook_url)\s*[:=]\s*https?://[^\s]{16,}", "Webhook URL"),
    # JWT tokens
    (r"eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+", "JWT token"),
    # AWS keys
    (r"(?i)AKIA[A-Z0-9]{16}", "AWS access key"),
    (r"(?i)aws[_\s]?secret[_\s]?access[_\s]?key\s*[:=]\s*[A-Za-z0-9/+=]{40}", "AWS secret key"),
    # GitHub tokens
    (r"(?i)gh[pousr]_[A-Za-z0-9_]{36,}", "GitHub token"),
    # Generic high-entropy strings (potential secrets)
    (r"[A-Za-z0-9_\-]{32,}", "High-entropy string"),
]

# Unsafe claims about tool execution
TOOL_CLAIM_PATTERNS = [
    (r"(?i)(?:successfully|completed|finished)\s+(?:sent|sent|emailed|mailed|dispatched)", "claimed_email_sent"),
    (r"(?i)(?:successfully|completed|finished)\s+(?:deleted|removed|erased)\s+(?:file|document|data)", "claimed_file_deleted"),
    (r"(?i)(?:successfully|completed|finished)\s+(?:published|posted|created)\s+(?:post|article|page)", "claimed_published"),
    (r"(?i)(?:successfully|completed|finished)\s+(?:updated|modified|changed)\s+(?:database|record|entry)", "claimed_database_write"),
    (r"(?i)(?:successfully|completed|finished)\s+(?:paid|charged|billed|transferred)\s+\$?\d+", "claimed_payment"),
    (r"(?i)the\s+(?:email|message|file|document|post|payment)\s+(?:was|has been)\s+(?:sent|delivered|completed|processed)", "passive_tool_claim"),
    (r"(?i)i\s+(?:have|just)\s+(?:sent|emailed|deleted|published|paid|created)", "first_person_tool_claim"),
]

# Citation validation patterns
CITATION_PATTERNS = [
    (r"\[(\d+(?:,\s*\d+)*)\]", "bracket_citation"),
    (r"\(source\s*:\s*[^\)]+\)", "source_citation"),
    (r"(?i)according to\s+[^\.]+", "according_to_citation"),
    (r"(?i)source\s*:\s*\d+", "source_number"),
    (r"\[\^[^\]]+\]", "footnote_citation"),
]

# Hallucination risk indicators
HALLUCINATION_INDICATORS = [
    (r"(?i)\b(?:recent|latest|new|breaking)\s+(?:study|research|report|paper)\s+(?:shows|found|suggests|indicates)", "recent_study_claim"),
    (r"(?i)in\s+(?:19|20)\d{2},?\s+(?:a|an|the)\s+(?:new|recent|latest)\s+(?:study|discovery|breakthrough)", "dated_study_claim"),
    (r"(?i)(?:scientists|researchers|experts)\s+(?:have|just|recently)\s+(?:discovered|found|proven|confirmed)", "expert_discovery_claim"),
    (r"(?i)(?:definitely|certainly|absolutely|undeniably)\s+(?:true|false|correct|wrong|proven)", "absolute_certainty_claim"),
    (r"(?i)(?:everyone knows|it's obvious|clearly|it is well known)", "consensus_claim"),
    (r"(?i)studies\s+show\s+that", "generic_studies_claim"),
    (r"(?i)research\s+(?:indicates|suggests|proves|confirms)\s+that", "research_claim"),
]

# Unsafe HTML/Markdown patterns for rendering
UNSAFE_RENDERING_PATTERNS = [
    (r"<script[^>]*>.*?</script>", "script_tag"),
    (r"<iframe[^>]*>.*?</iframe>", "iframe_tag"),
    (r"javascript\s*:", "javascript_protocol"),
    (r"data\s*:\s*text/html", "data_uri_html"),
    (r"on\w+\s*=", "event_handler"),
    (r"<object[^>]*>", "object_tag"),
    (r"<embed[^>]*>", "embed_tag"),
    (r"<form[^>]*>", "form_tag"),
    (r"<input[^>]*>", "input_tag"),
]

# Length limits
MAX_RESPONSE_LENGTH = 50000  # characters
MAX_RESPONSE_WORDS = 10000   # words


# =============================================================================
# OUTPUT VALIDATOR
# =============================================================================

class OutputValidator:
    """Comprehensive output validation for AI responses."""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self._compiled_secret_patterns = [(re.compile(p, re.IGNORECASE), label) for p, label in SECRET_PATTERNS]
        self._compiled_tool_patterns = [(re.compile(p, re.IGNORECASE), label) for p, label in TOOL_CLAIM_PATTERNS]
        self._compiled_citation_patterns = [(re.compile(p, re.IGNORECASE), label) for p, label in CITATION_PATTERNS]
        self._compiled_hallucination_patterns = [(re.compile(p, re.IGNORECASE), label) for p, label in HALLUCINATION_INDICATORS]
        self._compiled_unsafe_render_patterns = [(re.compile(p, re.IGNORECASE | re.DOTALL), label) for p, label in UNSAFE_RENDERING_PATTERNS]
    
    def validate(
        self,
        response: str,
        expected_schema: Optional[Dict] = None,
        citations: Optional[List[str]] = None,
        tool_calls_made: Optional[List[Dict]] = None,
        source_content: Optional[List[str]] = None
    ) -> ValidationReport:
        """Validate a response against all guardrails."""
        violations = []
        sanitized = response
        
        # 1. Length check
        if len(response) > MAX_RESPONSE_LENGTH:
            violations.append(ValidationViolation(
                violation_type=ViolationType.LENGTH_EXCEEDED,
                message=f"Response exceeds maximum length ({len(response)} > {MAX_RESPONSE_LENGTH})",
                severity="high",
                suggested_fix="Truncate response or summarize"
            ))
            sanitized = sanitized[:MAX_RESPONSE_LENGTH] + "... [truncated]"
        
        word_count = len(response.split())
        if word_count > MAX_RESPONSE_WORDS:
            violations.append(ValidationViolation(
                violation_type=ViolationType.LENGTH_EXCEEDED,
                message=f"Response exceeds maximum word count ({word_count} > {MAX_RESPONSE_WORDS})",
                severity="medium",
                suggested_fix="Condense response"
            ))
        
        # 2. Schema validation
        if expected_schema:
            schema_violations = self._validate_schema(response, expected_schema)
            violations.extend(schema_violations)
        
        # 3. Secret/credential detection
        secret_violations = self._detect_secrets(response)
        violations.extend(secret_violations)
        
        # 3b. Sanitize secrets from response
        sanitized = self._sanitize_secrets(sanitized)
        
        # 4. Tool claim validation
        if tool_calls_made is not None:
            tool_violations = self._validate_tool_claims(response, tool_calls_made)
            violations.extend(tool_violations)
        else:
            # Still check for unsupported tool claims
            tool_violations = self._detect_unsupported_tool_claims(response)
            violations.extend(tool_violations)
        
        # 5. Citation validation
        if citations is not None:
            citation_violations = self._validate_citations(response, citations)
            violations.extend(citation_violations)
        
        # 6. Hallucination risk detection
        hallucination_violations = self._detect_hallucination_risk(response, source_content)
        violations.extend(hallucination_violations)
        
        # 7. Unsafe rendering detection
        rendering_violations = self._detect_unsafe_rendering(response)
        violations.extend(rendering_violations)
        sanitized = self._sanitize_rendering(sanitized)
        
        # 8. Safety policy (basic)
        safety_violations = self._check_safety_policy(response)
        violations.extend(safety_violations)
        
        # Determine overall result
        result = self._determine_result(violations)
        
        # Build metadata
        metadata = {
            "response_length": len(response),
            "word_count": word_count,
            "violation_count": len(violations),
            "violation_types": list(set(v.violation_type.value for v in violations)),
            "has_citations": bool(citations and len(citations) > 0),
            "has_tool_calls": bool(tool_calls_made and len(tool_calls_made) > 0),
        }
        
        return ValidationReport(
            result=result,
            violations=violations,
            sanitized_response=sanitized,
            metadata=metadata
        )
    
    def _validate_schema(self, response: str, schema: Dict) -> List[ValidationViolation]:
        """Validate response against expected JSON schema."""
        violations = []
        try:
            parsed = json.loads(response)
            # Basic type checking
            if "type" in schema:
                expected_type = schema["type"]
                if expected_type == "object" and not isinstance(parsed, dict):
                    violations.append(ValidationViolation(
                        violation_type=ViolationType.SCHEMA_MISMATCH,
                        message=f"Expected JSON object, got {type(parsed).__name__}",
                        severity="high"
                    ))
                elif expected_type == "array" and not isinstance(parsed, list):
                    violations.append(ValidationViolation(
                        violation_type=ViolationType.SCHEMA_MISMATCH,
                        message=f"Expected JSON array, got {type(parsed).__name__}",
                        severity="high"
                    ))
            # Required fields
            if "required" in schema and isinstance(parsed, dict):
                for field in schema["required"]:
                    if field not in parsed:
                        violations.append(ValidationViolation(
                            violation_type=ViolationType.SCHEMA_MISMATCH,
                            message=f"Missing required field: {field}",
                            severity="high",
                            location=field
                        ))
        except json.JSONDecodeError as e:
            violations.append(ValidationViolation(
                violation_type=ViolationType.SCHEMA_MISMATCH,
                message=f"Response is not valid JSON: {e}",
                severity="high"
            ))
        return violations
    
    def _detect_secrets(self, response: str) -> List[ValidationViolation]:
        """Detect secrets/credentials in response."""
        violations = []
        for pattern, label in self._compiled_secret_patterns:
            for match in pattern.finditer(response):
                violations.append(ValidationViolation(
                    violation_type=ViolationType.SECRET_LEAKAGE,
                    message=f"Potential {label} detected in response",
                    severity="critical",
                    location=f"characters {match.start()}-{match.end()}",
                    suggested_fix="Remove or redact sensitive credentials"
                ))
        return violations
    
    def _sanitize_secrets(self, response: str) -> str:
        """Remove/redact secrets from response."""
        result = response
        for pattern, label in self._compiled_secret_patterns:
            result = pattern.sub(f"[REDACTED:{label}]", result)
        return result
    
    def _validate_tool_claims(self, response: str, tool_calls_made: List[Dict]) -> List[ValidationViolation]:
        """Validate that tool execution claims match actual tool calls."""
        violations = []
        # Extract claimed tool actions from response
        for pattern, label in self._compiled_tool_patterns:
            for match in pattern.finditer(response):
                # Check if there's a corresponding tool call
                claimed_action = match.group(0).lower()
                matched = False
                for call in tool_calls_made:
                    tool_name = call.get("name", "").lower()
                    if tool_name in claimed_action or any(kw in claimed_action for kw in ["email", "delete", "publish", "pay", "transfer"]):
                        matched = True
                        break
                if not matched:
                    violations.append(ValidationViolation(
                        violation_type=ViolationType.TOOL_CLAIM_ERROR,
                        message=f"Response claims {label} but no corresponding tool call was made",
                        severity="high",
                        location=f"characters {match.start()}-{match.end()}",
                        suggested_fix="Remove unsupported tool execution claims or add actual tool calls"
                    ))
        return violations
    
    def _detect_unsupported_tool_claims(self, response: str) -> List[ValidationViolation]:
        """Detect tool claims when no tool calls were made (general case)."""
        violations = []
        # Only flag high-confidence claims
        high_confidence_patterns = [
            (r"(?i)successfully\s+(?:sent|delivered|completed)\s+(?:the\s+)?(?:email|message|file)", "claimed_completion"),
            (r"(?i)i\s+have\s+(?:sent|deleted|published|paid)\s+", "first_person_claim"),
        ]
        for pattern, label in high_confidence_patterns:
            for match in pattern.finditer(response):
                violations.append(ValidationViolation(
                    violation_type=ViolationType.TOOL_CLAIM_ERROR,
                    message=f"Response makes unsupported {label}: tool execution not verified",
                    severity="medium",
                    location=f"characters {match.start()}-{match.end()}",
                    suggested_fix="Only claim tool execution when tool calls have actually been made and returned success"
                ))
        return violations
    
    def _validate_citations(self, response: str, citations: List[str]) -> List[ValidationViolation]:
        """Validate that citations in response match provided sources."""
        violations = []
        # Find all citation-like patterns in response
        found_citations = set()
        for pattern, label in self._compiled_citation_patterns:
            for match in pattern.finditer(response):
                found_citations.add(match.group(0))
        
        # Check if response has citations but none were provided
        if found_citations and not citations:
            violations.append(ValidationViolation(
                violation_type=ViolationType.CITATION_ERROR,
                message="Response contains citations but no citation sources were provided",
                severity="medium",
                suggested_fix="Provide citation sources or remove citation references"
            ))
        
        # Check if provided citations are referenced
        if citations and not found_citations:
            violations.append(ValidationViolation(
                violation_type=ViolationType.CITATION_ERROR,
                message="Citation sources provided but not referenced in response",
                severity="low",
                suggested_fix="Add citation references to response"
            ))
        
        return violations
    
    def _detect_hallucination_risk(self, response: str, source_content: Optional[List[str]] = None) -> List[ValidationViolation]:
        """Detect potential hallucination patterns."""
        violations = []
        for pattern, label in self._compiled_hallucination_patterns:
            for match in pattern.finditer(response):
                severity = "medium"
                if label in ["absolute_certainty_claim", "consensus_claim"]:
                    severity = "high"
                violations.append(ValidationViolation(
                    violation_type=ViolationType.HALLUCINATION_RISK,
                    message=f"Potential hallucination indicator: {label}",
                    severity=severity,
                    location=f"characters {match.start()}-{match.end()}",
                    suggested_fix="Verify factual claims against sources or add uncertainty qualifiers"
                ))
        
        # If source content provided, check for unsupported claims
        if source_content:
            source_text = " ".join(source_content).lower() if isinstance(source_content, list) else str(source_content).lower()
            response_words = set(response.lower().split())
            source_words = set(source_text.split())
            # Check for specific factual claims not in sources
            # This is a simplified check - real implementation would use NLI
            pass
        
        return violations
    
    def _detect_unsafe_rendering(self, response: str) -> List[ValidationViolation]:
        """Detect unsafe HTML/Markdown patterns."""
        violations = []
        for pattern, label in self._compiled_unsafe_render_patterns:
            for match in pattern.finditer(response):
                violations.append(ValidationViolation(
                    violation_type=ViolationType.UNSAFE_RENDERING,
                    message=f"Unsafe rendering pattern detected: {label}",
                    severity="high",
                    location=f"characters {match.start()}-{match.end()}",
                    suggested_fix="Remove or escape unsafe HTML/Markdown"
                ))
        return violations
    
    def _sanitize_rendering(self, response: str) -> str:
        """Sanitize unsafe rendering patterns."""
        result = response
        for pattern, label in self._compiled_unsafe_render_patterns:
            result = pattern.sub(f"[REMOVED:{label}]", result)
        return result
    
    def _check_safety_policy(self, response: str) -> List[ValidationViolation]:
        """Basic safety policy checks."""
        violations = []
        response_lower = response.lower()
        
        # Check for harmful content encouragement
        harmful_encouragement = [
            (r"(?i)you should\s+(?:kill|harm|hurt|attack)", "encourages_violence"),
            (r"(?i)how to\s+(?:make|create|build)\s+(?:bomb|explosive|weapon|poison)", "weapon_instructions"),
            (r"(?i)here's how to\s+(?:hack|crack|steal|fraud)", "illegal_instructions"),
        ]
        
        for pattern, label in harmful_encouragement:
            if re.search(pattern, response_lower):
                violations.append(ValidationViolation(
                    violation_type=ViolationType.SAFETY_VIOLATION,
                    message=f"Safety violation: {label}",
                    severity="critical",
                    suggested_fix="Remove harmful content"
                ))
        
        return violations
    
    def _determine_result(self, violations: List[ValidationViolation]) -> ValidationResult:
        """Determine overall validation result."""
        if not violations:
            return ValidationResult.PASS
        
        has_critical = any(v.severity == "critical" for v in violations)
        has_high = any(v.severity == "high" for v in violations)
        has_medium = any(v.severity == "medium" for v in violations)
        
        if has_critical:
            return ValidationResult.FAIL
        elif has_high:
            return ValidationResult.FAIL if self.strict_mode else ValidationResult.RETRY
        elif has_medium:
            return ValidationResult.WARNING
        else:
            return ValidationResult.WARNING


# Global validator instance
_validator: Optional[OutputValidator] = None

def get_validator(strict_mode: bool = True) -> OutputValidator:
    global _validator
    if _validator is None:
        _validator = OutputValidator(strict_mode=strict_mode)
    return _validator


def validate_output(
    response: str,
    expected_schema: Optional[Dict] = None,
    citations: Optional[List[str]] = None,
    tool_calls_made: Optional[List[Dict]] = None,
    source_content: Optional[List[str]] = None,
    strict_mode: bool = True
) -> ValidationReport:
    """Convenience function to validate output."""
    return get_validator(strict_mode).validate(
        response, expected_schema, citations, tool_calls_made, source_content
    )


def is_output_valid(
    response: str,
    expected_schema: Optional[Dict] = None,
    citations: Optional[List[str]] = None,
    tool_calls_made: Optional[List[Dict]] = None,
    strict_mode: bool = True
) -> Tuple[bool, ValidationReport]:
    """Check if output is valid (PASS or WARNING)."""
    report = validate_output(response, expected_schema, citations, tool_calls_made, None, strict_mode)
    is_valid = report.result in (ValidationResult.PASS, ValidationResult.WARNING)
    return is_valid, report


__all__ = [
    "OutputValidator",
    "ValidationReport",
    "ValidationViolation",
    "ValidationResult",
    "ViolationType",
    "get_validator",
    "validate_output",
    "is_output_valid",
]