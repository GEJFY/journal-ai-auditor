"""
JAIA コアモジュール

アプリケーション全体で使用される基盤機能を提供します。

モジュール:
- config: 設定管理（環境変数、設定ファイル）
- logging: ロギングシステム（構造化ログ、監査ログ）
- exceptions: カスタム例外クラス
"""

from app.core.config import settings
from app.core.exceptions import (
    AgentError,
    AnalysisError,
    AuthorizationError,
    BenfordAnalysisError,
    ColumnMappingError,
    ConflictError,
    ConnectionError,
    DatabaseError,
    DataValidationError,
    DuplicateDataError,
    EncodingError,
    FileReadError,
    FileValidationError,
    ImportError,
    IntegrityError,
    JAIAException,
    LLMProviderError,
    MLModelError,
    OrchestratorError,
    QueryError,
    RateLimitError,
    ReportError,
    ReportGenerationError,
    ResourceNotFoundError,
    RuleExecutionError,
    TemplateNotFoundError,
    ToolExecutionError,
    ValidationError,
)
from app.core.logging import (
    LogContext,
    audit_log,
    get_logger,
    get_request_id,
    log_function_call,
    perf_log,
    set_request_id,
    setup_logging,
)

__all__ = [
    # 設定
    "settings",
    # ロギング
    "setup_logging",
    "get_logger",
    "audit_log",
    "perf_log",
    "get_request_id",
    "set_request_id",
    "LogContext",
    "log_function_call",
    # 例外
    "JAIAException",
    "ValidationError",
    "FileValidationError",
    "DataValidationError",
    "ColumnMappingError",
    "ImportError",
    "FileReadError",
    "EncodingError",
    "DuplicateDataError",
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "IntegrityError",
    "AnalysisError",
    "RuleExecutionError",
    "MLModelError",
    "BenfordAnalysisError",
    "AgentError",
    "OrchestratorError",
    "LLMProviderError",
    "ToolExecutionError",
    "ReportError",
    "TemplateNotFoundError",
    "ReportGenerationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "ConflictError",
    "RateLimitError",
]
