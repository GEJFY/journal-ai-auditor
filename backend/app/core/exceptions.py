"""
JAIA カスタム例外クラス

アプリケーション全体で使用する例外クラスを定義します。

例外の階層:
    JAIAException (基底クラス)
    ├── ValidationError
    │   ├── FileValidationError
    │   ├── DataValidationError
    │   └── ColumnMappingError
    ├── ImportError
    │   ├── FileReadError
    │   ├── EncodingError
    │   └── DuplicateDataError
    ├── DatabaseError
    │   ├── ConnectionError
    │   ├── QueryError
    │   └── IntegrityError
    ├── AnalysisError
    │   ├── RuleExecutionError
    │   ├── MLModelError
    │   └── BenfordAnalysisError
    ├── AgentError
    │   ├── OrchestratorError
    │   ├── LLMProviderError
    │   └── ToolExecutionError
    ├── ReportError
    │   ├── TemplateNotFoundError
    │   └── ReportGenerationError
    └── AuthorizationError

使用例:
    from app.core.exceptions import ValidationError, DataValidationError

    if not data:
        raise DataValidationError(
            message="データが空です",
            field="journal_entries",
            detail={"row_count": 0}
        )
"""

from typing import Any


class JAIAException(Exception):
    """
    JAIA基底例外クラス。

    全てのJAIA固有の例外はこのクラスを継承します。

    Attributes:
        message: エラーメッセージ
        error_code: エラーコード（API応答用）
        detail: 追加の詳細情報
        http_status_code: HTTPステータスコード
    """

    error_code: str = "JAIA_ERROR"
    http_status_code: int = 500

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        detail: dict[str, Any] | None = None,
        http_status_code: int | None = None
    ):
        """
        例外を初期化します。

        Args:
            message: エラーメッセージ
            error_code: エラーコード（省略時はクラスのデフォルト）
            detail: 追加の詳細情報
            http_status_code: HTTPステータスコード（省略時はクラスのデフォルト）
        """
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        if http_status_code:
            self.http_status_code = http_status_code
        self.detail = detail or {}

    def to_dict(self) -> dict[str, Any]:
        """
        例外をAPI応答用の辞書形式に変換します。

        Returns:
            dict: エラー情報を含む辞書
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "detail": self.detail
        }

    def __str__(self) -> str:
        """文字列表現を返します。"""
        if self.detail:
            return f"[{self.error_code}] {self.message} - {self.detail}"
        return f"[{self.error_code}] {self.message}"


# ========================================
# バリデーション関連の例外
# ========================================

class ValidationError(JAIAException):
    """バリデーションエラーの基底クラス。"""

    error_code = "VALIDATION_ERROR"
    http_status_code = 400


class FileValidationError(ValidationError):
    """
    ファイル検証エラー。

    ファイル形式、サイズ、拡張子などの検証失敗時に発生します。
    """

    error_code = "FILE_VALIDATION_ERROR"

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        expected_format: str | None = None,
        actual_format: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if file_path:
            detail["file_path"] = file_path
        if expected_format:
            detail["expected_format"] = expected_format
        if actual_format:
            detail["actual_format"] = actual_format
        super().__init__(message, detail=detail, **kwargs)


class DataValidationError(ValidationError):
    """
    データ検証エラー。

    データの値、型、範囲などの検証失敗時に発生します。
    """

    error_code = "DATA_VALIDATION_ERROR"

    def __init__(
        self,
        message: str,
        field: str | None = None,
        row_number: int | None = None,
        expected_value: Any = None,
        actual_value: Any = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if field:
            detail["field"] = field
        if row_number is not None:
            detail["row_number"] = row_number
        if expected_value is not None:
            detail["expected_value"] = str(expected_value)
        if actual_value is not None:
            detail["actual_value"] = str(actual_value)
        super().__init__(message, detail=detail, **kwargs)


class ColumnMappingError(ValidationError):
    """
    カラムマッピングエラー。

    必須カラムが見つからない、またはマッピングが不正な場合に発生します。
    """

    error_code = "COLUMN_MAPPING_ERROR"

    def __init__(
        self,
        message: str,
        missing_columns: list[str] | None = None,
        invalid_mappings: dict[str, str] | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if missing_columns:
            detail["missing_columns"] = missing_columns
        if invalid_mappings:
            detail["invalid_mappings"] = invalid_mappings
        super().__init__(message, detail=detail, **kwargs)


# ========================================
# インポート関連の例外
# ========================================

class ImportError(JAIAException):
    """インポートエラーの基底クラス。"""

    error_code = "IMPORT_ERROR"
    http_status_code = 422


class FileReadError(ImportError):
    """
    ファイル読み込みエラー。

    ファイルが存在しない、アクセス権限がない等の場合に発生します。
    """

    error_code = "FILE_READ_ERROR"

    def __init__(
        self,
        message: str,
        file_path: str,
        original_error: Exception | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["file_path"] = file_path
        if original_error:
            detail["original_error"] = str(original_error)
        super().__init__(message, detail=detail, **kwargs)


class EncodingError(ImportError):
    """
    エンコーディングエラー。

    ファイルのエンコーディングが不正な場合に発生します。
    """

    error_code = "ENCODING_ERROR"

    def __init__(
        self,
        message: str,
        expected_encoding: str | None = None,
        detected_encoding: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if expected_encoding:
            detail["expected_encoding"] = expected_encoding
        if detected_encoding:
            detail["detected_encoding"] = detected_encoding
        super().__init__(message, detail=detail, **kwargs)


class DuplicateDataError(ImportError):
    """
    重複データエラー。

    同一データが既に存在する場合に発生します。
    """

    error_code = "DUPLICATE_DATA_ERROR"

    def __init__(
        self,
        message: str,
        duplicate_keys: list[str] | None = None,
        duplicate_count: int | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if duplicate_keys:
            detail["duplicate_keys"] = duplicate_keys
        if duplicate_count is not None:
            detail["duplicate_count"] = duplicate_count
        super().__init__(message, detail=detail, **kwargs)


# ========================================
# データベース関連の例外
# ========================================

class DatabaseError(JAIAException):
    """データベースエラーの基底クラス。"""

    error_code = "DATABASE_ERROR"
    http_status_code = 500


class ConnectionError(DatabaseError):
    """
    データベース接続エラー。

    データベースへの接続に失敗した場合に発生します。
    """

    error_code = "DB_CONNECTION_ERROR"

    def __init__(
        self,
        message: str,
        database_type: str | None = None,
        database_path: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if database_type:
            detail["database_type"] = database_type
        if database_path:
            detail["database_path"] = database_path
        super().__init__(message, detail=detail, **kwargs)


class QueryError(DatabaseError):
    """
    クエリ実行エラー。

    SQLクエリの実行に失敗した場合に発生します。
    """

    error_code = "QUERY_ERROR"

    def __init__(
        self,
        message: str,
        query: str | None = None,
        parameters: dict[str, Any] | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if query:
            # クエリは長い場合があるため、先頭200文字のみ保持
            detail["query"] = query[:200] + ("..." if len(query) > 200 else "")
        if parameters:
            detail["parameters"] = parameters
        super().__init__(message, detail=detail, **kwargs)


class IntegrityError(DatabaseError):
    """
    データ整合性エラー。

    一意制約違反、外部キー制約違反などの場合に発生します。
    """

    error_code = "INTEGRITY_ERROR"
    http_status_code = 409


# ========================================
# 分析関連の例外
# ========================================

class AnalysisError(JAIAException):
    """分析エラーの基底クラス。"""

    error_code = "ANALYSIS_ERROR"
    http_status_code = 500


class RuleExecutionError(AnalysisError):
    """
    ルール実行エラー。

    監査ルールの実行中にエラーが発生した場合に発生します。
    """

    error_code = "RULE_EXECUTION_ERROR"

    def __init__(
        self,
        message: str,
        rule_id: str,
        rule_name: str | None = None,
        affected_count: int | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["rule_id"] = rule_id
        if rule_name:
            detail["rule_name"] = rule_name
        if affected_count is not None:
            detail["affected_count"] = affected_count
        super().__init__(message, detail=detail, **kwargs)


class MLModelError(AnalysisError):
    """
    機械学習モデルエラー。

    MLモデルの学習または推論中にエラーが発生した場合に発生します。
    """

    error_code = "ML_MODEL_ERROR"

    def __init__(
        self,
        message: str,
        model_name: str,
        phase: str | None = None,  # "training" or "inference"
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["model_name"] = model_name
        if phase:
            detail["phase"] = phase
        super().__init__(message, detail=detail, **kwargs)


class BenfordAnalysisError(AnalysisError):
    """
    Benford分析エラー。

    Benfordの法則に基づく分析中にエラーが発生した場合に発生します。
    """

    error_code = "BENFORD_ANALYSIS_ERROR"

    def __init__(
        self,
        message: str,
        digit_position: int | None = None,  # 1 or 2
        sample_size: int | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if digit_position is not None:
            detail["digit_position"] = digit_position
        if sample_size is not None:
            detail["sample_size"] = sample_size
        super().__init__(message, detail=detail, **kwargs)


# ========================================
# エージェント関連の例外
# ========================================

class AgentError(JAIAException):
    """エージェントエラーの基底クラス。"""

    error_code = "AGENT_ERROR"
    http_status_code = 500


class OrchestratorError(AgentError):
    """
    オーケストレーターエラー。

    エージェントの調整・管理中にエラーが発生した場合に発生します。
    """

    error_code = "ORCHESTRATOR_ERROR"

    def __init__(
        self,
        message: str,
        session_id: str | None = None,
        current_phase: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if session_id:
            detail["session_id"] = session_id
        if current_phase:
            detail["current_phase"] = current_phase
        super().__init__(message, detail=detail, **kwargs)


class LLMProviderError(AgentError):
    """
    LLMプロバイダーエラー。

    LLM API呼び出し中にエラーが発生した場合に発生します。
    """

    error_code = "LLM_PROVIDER_ERROR"
    http_status_code = 503

    def __init__(
        self,
        message: str,
        provider: str,
        model: str | None = None,
        error_type: str | None = None,  # "rate_limit", "timeout", "auth", etc.
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["provider"] = provider
        if model:
            detail["model"] = model
        if error_type:
            detail["error_type"] = error_type
        super().__init__(message, detail=detail, **kwargs)


class ToolExecutionError(AgentError):
    """
    ツール実行エラー。

    エージェントのツール実行中にエラーが発生した場合に発生します。
    """

    error_code = "TOOL_EXECUTION_ERROR"

    def __init__(
        self,
        message: str,
        tool_name: str,
        input_params: dict[str, Any] | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["tool_name"] = tool_name
        if input_params:
            detail["input_params"] = input_params
        super().__init__(message, detail=detail, **kwargs)


# ========================================
# レポート関連の例外
# ========================================

class ReportError(JAIAException):
    """レポートエラーの基底クラス。"""

    error_code = "REPORT_ERROR"
    http_status_code = 500


class TemplateNotFoundError(ReportError):
    """
    テンプレート未発見エラー。

    指定されたレポートテンプレートが見つからない場合に発生します。
    """

    error_code = "TEMPLATE_NOT_FOUND"
    http_status_code = 404

    def __init__(
        self,
        message: str,
        template_id: str,
        available_templates: list[str] | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["template_id"] = template_id
        if available_templates:
            detail["available_templates"] = available_templates
        super().__init__(message, detail=detail, **kwargs)


class ReportGenerationError(ReportError):
    """
    レポート生成エラー。

    レポートの生成中にエラーが発生した場合に発生します。
    """

    error_code = "REPORT_GENERATION_ERROR"

    def __init__(
        self,
        message: str,
        report_type: str,
        stage: str | None = None,  # "data_fetch", "render", "export"
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["report_type"] = report_type
        if stage:
            detail["stage"] = stage
        super().__init__(message, detail=detail, **kwargs)


# ========================================
# 認証・認可関連の例外
# ========================================

class AuthorizationError(JAIAException):
    """
    認可エラー。

    ユーザーが許可されていない操作を実行しようとした場合に発生します。
    """

    error_code = "AUTHORIZATION_ERROR"
    http_status_code = 403

    def __init__(
        self,
        message: str,
        user_id: str | None = None,
        required_permission: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if user_id:
            detail["user_id"] = user_id
        if required_permission:
            detail["required_permission"] = required_permission
        super().__init__(message, detail=detail, **kwargs)


# ========================================
# リソース関連の例外
# ========================================

class ResourceNotFoundError(JAIAException):
    """
    リソース未発見エラー。

    指定されたリソースが見つからない場合に発生します。
    """

    error_code = "RESOURCE_NOT_FOUND"
    http_status_code = 404

    def __init__(
        self,
        message: str,
        resource_type: str,
        resource_id: str,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["resource_type"] = resource_type
        detail["resource_id"] = resource_id
        super().__init__(message, detail=detail, **kwargs)


class ConflictError(JAIAException):
    """
    リソース競合エラー。

    リソースの状態が操作と矛盾する場合に発生します。
    """

    error_code = "CONFLICT"
    http_status_code = 409

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        current_state: str | None = None,
        expected_state: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if resource_type:
            detail["resource_type"] = resource_type
        if current_state:
            detail["current_state"] = current_state
        if expected_state:
            detail["expected_state"] = expected_state
        super().__init__(message, detail=detail, **kwargs)


class RateLimitError(JAIAException):
    """
    レート制限エラー。

    APIレート制限に達した場合に発生します。
    """

    error_code = "RATE_LIMIT_EXCEEDED"
    http_status_code = 429

    def __init__(
        self,
        message: str,
        limit: int | None = None,
        window_seconds: int | None = None,
        retry_after_seconds: int | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if limit is not None:
            detail["limit"] = limit
        if window_seconds is not None:
            detail["window_seconds"] = window_seconds
        if retry_after_seconds is not None:
            detail["retry_after_seconds"] = retry_after_seconds
        super().__init__(message, detail=detail, **kwargs)


# ========================================
# セキュリティ関連の例外
# ========================================

class SecurityError(JAIAException):
    """セキュリティエラーの基底クラス。"""

    error_code = "SECURITY_ERROR"
    http_status_code = 403


class AuthenticationError(SecurityError):
    """
    認証エラー。

    ユーザーの認証に失敗した場合に発生します。
    """

    error_code = "AUTHENTICATION_ERROR"
    http_status_code = 401

    def __init__(
        self,
        message: str,
        auth_method: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if auth_method:
            detail["auth_method"] = auth_method
        super().__init__(message, detail=detail, **kwargs)


class TokenExpiredError(SecurityError):
    """
    トークン期限切れエラー。

    認証トークンが期限切れの場合に発生します。
    """

    error_code = "TOKEN_EXPIRED"
    http_status_code = 401


class InvalidTokenError(SecurityError):
    """
    無効トークンエラー。

    認証トークンが無効な場合に発生します。
    """

    error_code = "INVALID_TOKEN"
    http_status_code = 401


class IPBlockedError(SecurityError):
    """
    IPブロックエラー。

    ブロックされたIPアドレスからのアクセスの場合に発生します。
    """

    error_code = "IP_BLOCKED"
    http_status_code = 403

    def __init__(
        self,
        message: str,
        ip_address: str | None = None,
        reason: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if ip_address:
            detail["ip_address"] = ip_address
        if reason:
            detail["reason"] = reason
        super().__init__(message, detail=detail, **kwargs)


class SuspiciousActivityError(SecurityError):
    """
    不審なアクティビティエラー。

    不審な操作パターンが検出された場合に発生します。
    """

    error_code = "SUSPICIOUS_ACTIVITY"
    http_status_code = 403

    def __init__(
        self,
        message: str,
        activity_type: str | None = None,
        user_id: str | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        if activity_type:
            detail["activity_type"] = activity_type
        if user_id:
            detail["user_id"] = user_id
        super().__init__(message, detail=detail, **kwargs)


# ========================================
# サーキットブレーカー関連の例外
# ========================================

class CircuitBreakerError(JAIAException):
    """
    サーキットブレーカーエラー。

    サービスへの接続がサーキットブレーカーによって遮断された場合に発生します。
    """

    error_code = "CIRCUIT_BREAKER_OPEN"
    http_status_code = 503

    def __init__(
        self,
        message: str,
        service: str,
        retry_after_seconds: int | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["service"] = service
        if retry_after_seconds is not None:
            detail["retry_after_seconds"] = retry_after_seconds
        super().__init__(message, detail=detail, **kwargs)


class ServiceUnavailableError(JAIAException):
    """
    サービス利用不可エラー。

    依存サービスが利用できない場合に発生します。
    """

    error_code = "SERVICE_UNAVAILABLE"
    http_status_code = 503

    def __init__(
        self,
        message: str,
        service: str,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["service"] = service
        super().__init__(message, detail=detail, **kwargs)


class TimeoutError(JAIAException):
    """
    タイムアウトエラー。

    操作がタイムアウトした場合に発生します。
    """

    error_code = "TIMEOUT"
    http_status_code = 504

    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: float | None = None,
        **kwargs
    ):
        detail = kwargs.pop("detail", {})
        detail["operation"] = operation
        if timeout_seconds is not None:
            detail["timeout_seconds"] = timeout_seconds
        super().__init__(message, detail=detail, **kwargs)
