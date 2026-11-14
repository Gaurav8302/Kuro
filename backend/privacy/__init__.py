"""
Privacy package for Kuro AI.

Provides data minimization, retention management, user data controls,
and provider data flow documentation.
"""

from .minimization import (
    DataCategory,
    RetentionPolicy,
    DEFAULT_RETENTION_POLICIES,
    PII_PATTERNS,
    RedactionResult,
    DataMinimizer,
    RetentionManager,
    get_data_minimizer,
    get_retention_manager,
    redact_text,
    redact_dict,
    check_retention,
    log_data_deletion,
)

from .controls import (
    DataControlAction,
    DataExportRequest,
    DataDeletionRequest,
    RectificationRequest,
    RestrictionRequest,
    UserDataController,
    get_user_data_controller,
)

from .provider_flows import (
    Provider,
    DataClassification,
    DataFlow,
    PROVIDER_DATA_FLOWS,
    DPA_STATUS,
    get_provider_flows,
    get_all_flows,
    get_dpa_status,
    generate_data_flow_report,
)

__all__ = [
    # minimization
    "DataCategory",
    "RetentionPolicy",
    "DEFAULT_RETENTION_POLICIES",
    "PII_PATTERNS",
    "RedactionResult",
    "DataMinimizer",
    "RetentionManager",
    "get_data_minimizer",
    "get_retention_manager",
    "redact_text",
    "redact_dict",
    "check_retention",
    "log_data_deletion",
    # controls
    "DataControlAction",
    "DataExportRequest",
    "DataDeletionRequest",
    "RectificationRequest",
    "RestrictionRequest",
    "UserDataController",
    "get_user_data_controller",
    # provider_flows
    "Provider",
    "DataClassification",
    "DataFlow",
    "PROVIDER_DATA_FLOWS",
    "DPA_STATUS",
    "get_provider_flows",
    "get_all_flows",
    "get_dpa_status",
    "generate_data_flow_report",
]