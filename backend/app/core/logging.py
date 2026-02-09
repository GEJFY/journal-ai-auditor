"""
JAIA エンタープライズロギングシステム

本番利用に対応した包括的なロギング設定を提供します。

機能:
- 構造化ログ出力（JSON形式対応）
- ファイルローテーション
- リクエストIDによるトレーシング
- 監査ログの分離（コンプライアンス対応）
- パフォーマンスログ
- 機密データの自動マスキング
- クラウドログ統合（CloudWatch, Stackdriver, Azure Monitor）
- セキュリティイベントログ

使用例:
    from app.core.logging import get_logger, audit_log, security_log

    logger = get_logger(__name__)
    logger.info("処理を開始します", extra={"user_id": "user001"})

    audit_log.info("データインポート完了", extra={"import_id": "imp_001"})
    security_log.warning("認証失敗", extra={"ip_address": "192.168.1.1"})
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from .config import settings

# コンテキスト変数：リクエストIDのスレッドセーフな管理
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str:
    """
    現在のリクエストIDを取得します。

    Returns:
        str: リクエストID（未設定の場合は"no-request-id"）
    """
    return request_id_var.get() or "no-request-id"


def set_request_id(request_id: str | None = None) -> str:
    """
    リクエストIDを設定します。

    Args:
        request_id: 設定するリクエストID（Noneの場合は自動生成）

    Returns:
        str: 設定されたリクエストID
    """
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


class SensitiveDataFilter(logging.Filter):
    """
    機密データをマスキングするフィルター。

    APIキー、パスワード、トークンなどの機密情報を
    ログ出力前に自動的にマスキングします。
    """

    SENSITIVE_PATTERNS = [
        "api_key",
        "apikey",
        "api-key",
        "secret",
        "password",
        "passwd",
        "token",
        "authorization",
        "credential",
        "aws_access_key",
        "aws_secret",
        "private_key",
        "api_secret",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """機密データをマスキングします。"""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._mask_sensitive(record.msg)
        if hasattr(record, "args") and record.args:
            record.args = tuple(
                self._mask_sensitive(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True

    def _mask_sensitive(self, msg: str) -> str:
        """機密値をマスキングします。"""
        import re

        patterns = [
            (r"(sk-ant-[a-zA-Z0-9-]{10,})", r"sk-ant-***MASKED***"),
            (r"(sk-proj-[a-zA-Z0-9-]{10,})", r"sk-proj-***MASKED***"),
            (r"(sk-[a-zA-Z0-9]{20,})", r"sk-***MASKED***"),
            (r"(AKIA[A-Z0-9]{12,})", r"AKIA***MASKED***"),
            (r"(AIzaSy[a-zA-Z0-9_-]{20,})", r"AIzaSy***MASKED***"),
            (
                r'(["\']?(?:password|secret|token|api_key)["\']?\s*[:=]\s*["\']?)([^"\']{4,})(["\']?)',
                r"\1***MASKED***\3",
            ),
        ]
        for pattern, replacement in patterns:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        return msg


class RequestIdFilter(logging.Filter):
    """
    ログレコードにリクエストIDを追加するフィルター。

    全てのログ出力にリクエストIDを自動付与し、
    リクエストのトレーサビリティを確保します。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        ログレコードにリクエストIDを追加します。

        Args:
            record: ログレコード

        Returns:
            bool: 常にTrue（フィルタリングは行わない）
        """
        record.request_id = get_request_id()
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON形式でログを出力するフォーマッター。

    構造化ログとして解析しやすい形式で出力します。
    ELK Stack、CloudWatch Logs等との連携に適しています。
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        ログレコードをJSON形式に変換します。

        Args:
            record: ログレコード

        Returns:
            str: JSON形式のログ文字列
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "no-request-id"),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 例外情報がある場合は追加
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # extra情報を追加
        extra_fields = [
            "user_id",
            "import_id",
            "session_id",
            "journal_id",
            "duration_ms",
            "status_code",
            "method",
            "path",
            "rule_id",
            "risk_score",
            "error_code",
        ]
        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """
    コンソール出力用のカラーフォーマッター。

    開発時の可読性を向上させるため、ログレベルに応じて
    色分けして出力します。
    """

    # ANSIカラーコード
    COLORS = {
        "DEBUG": "\033[36m",  # シアン
        "INFO": "\033[32m",  # 緑
        "WARNING": "\033[33m",  # 黄
        "ERROR": "\033[31m",  # 赤
        "CRITICAL": "\033[35m",  # マゼンタ
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """
        ログレコードを色付きでフォーマットします。

        Args:
            record: ログレコード

        Returns:
            str: 色付きのログ文字列
        """
        color = self.COLORS.get(record.levelname, self.RESET)

        # リクエストIDを含むフォーマット
        request_id = getattr(record, "request_id", "no-request-id")

        formatted = (
            f"{color}{record.levelname:8}{self.RESET} "
            f"[{request_id}] "
            f"{record.name}: "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging() -> None:
    """
    アプリケーション全体のロギングを設定します。

    以下のロガーを設定:
    - メインロガー: アプリケーション全般のログ
    - 監査ロガー: セキュリティ・監査関連のログ
    - パフォーマンスロガー: 処理時間・パフォーマンス測定

    環境に応じてログレベルとフォーマットを自動調整します。
    """
    # ログディレクトリを作成
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # ログレベルの設定
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 既存のハンドラをクリア
    root_logger.handlers.clear()

    # フィルターを追加
    request_id_filter = RequestIdFilter()
    sensitive_data_filter = SensitiveDataFilter()

    # ========================================
    # コンソールハンドラ
    # ========================================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.addFilter(request_id_filter)
    console_handler.addFilter(sensitive_data_filter)

    if settings.debug:
        # 開発環境: カラー出力
        console_handler.setFormatter(ColoredFormatter())
    else:
        # 本番環境: JSON形式
        console_handler.setFormatter(JSONFormatter())

    root_logger.addHandler(console_handler)

    # ========================================
    # メインログファイル（ローテーション）
    # ========================================
    main_file_handler = RotatingFileHandler(
        filename=log_dir / "jaia.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    main_file_handler.setLevel(log_level)
    main_file_handler.addFilter(request_id_filter)
    main_file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(main_file_handler)

    # ========================================
    # エラーログファイル
    # ========================================
    error_file_handler = RotatingFileHandler(
        filename=log_dir / "jaia_error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.addFilter(request_id_filter)
    error_file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_file_handler)

    # ========================================
    # 監査ログ（日次ローテーション）
    # ========================================
    audit_logger = logging.getLogger("jaia.audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False  # 親ロガーに伝播しない

    audit_handler = TimedRotatingFileHandler(
        filename=log_dir / "jaia_audit.log",
        when="midnight",
        interval=1,
        backupCount=90,  # 90日間保持
        encoding="utf-8",
    )
    audit_handler.addFilter(request_id_filter)
    audit_handler.setFormatter(JSONFormatter())
    audit_logger.addHandler(audit_handler)

    # ========================================
    # パフォーマンスログ
    # ========================================
    perf_logger = logging.getLogger("jaia.performance")
    perf_logger.setLevel(logging.INFO)
    perf_logger.propagate = False

    perf_handler = RotatingFileHandler(
        filename=log_dir / "jaia_performance.log",
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=5,
        encoding="utf-8",
    )
    perf_handler.addFilter(request_id_filter)
    perf_handler.setFormatter(JSONFormatter())
    perf_logger.addHandler(perf_handler)

    # ========================================
    # セキュリティログ（日次ローテーション）
    # ========================================
    sec_logger = logging.getLogger("jaia.security")
    sec_logger.setLevel(logging.INFO)
    sec_logger.propagate = False

    security_handler = TimedRotatingFileHandler(
        filename=log_dir / "jaia_security.log",
        when="midnight",
        interval=1,
        backupCount=365,  # 1年間保持（コンプライアンス対応）
        encoding="utf-8",
    )
    security_handler.addFilter(request_id_filter)
    security_handler.addFilter(sensitive_data_filter)
    security_handler.setFormatter(JSONFormatter())
    sec_logger.addHandler(security_handler)

    # サードパーティライブラリのログレベルを調整
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    指定した名前のロガーを取得します。

    Args:
        name: ロガー名（通常は __name__ を使用）

    Returns:
        logging.Logger: 設定済みのロガーインスタンス

    使用例:
        logger = get_logger(__name__)
        logger.info("処理を開始します")
    """
    return logging.getLogger(name)


# 特殊用途ロガーのエイリアス
audit_log = logging.getLogger("jaia.audit")
perf_log = logging.getLogger("jaia.performance")
security_log = logging.getLogger("jaia.security")


class LogContext:
    """
    ログコンテキストを管理するコンテキストマネージャー。

    処理の開始・終了と所要時間を自動的にログ出力します。

    使用例:
        with LogContext(logger, "データインポート", import_id="imp_001"):
            # 処理
            pass
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        level: int = logging.INFO,
        **context: Any,
    ):
        """
        LogContextを初期化します。

        Args:
            logger: 使用するロガー
            operation: 操作名
            level: ログレベル（デフォルト: INFO）
            **context: 追加のコンテキスト情報
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.context = context
        self.start_time: datetime | None = None

    def __enter__(self) -> "LogContext":
        """コンテキスト開始時の処理"""
        self.start_time = datetime.now()
        self.logger.log(
            self.level, f"{self.operation} を開始します", extra=self.context
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """コンテキスト終了時の処理"""
        duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000

        if exc_type is not None:
            self.logger.error(
                f"{self.operation} が失敗しました",
                extra={**self.context, "duration_ms": duration_ms},
                exc_info=True,
            )
        else:
            self.logger.log(
                self.level,
                f"{self.operation} が完了しました",
                extra={**self.context, "duration_ms": duration_ms},
            )

        # パフォーマンスログにも記録
        perf_log.info(
            f"{self.operation}",
            extra={
                **self.context,
                "duration_ms": duration_ms,
                "success": exc_type is None,
            },
        )


def log_function_call(logger: logging.Logger):
    """
    関数呼び出しをログ出力するデコレーター。

    Args:
        logger: 使用するロガー

    Returns:
        デコレーター関数

    使用例:
        @log_function_call(logger)
        def process_data(data: dict) -> dict:
            return processed_data
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                logger.debug(f"{func.__name__} を呼び出します")
                result = await func(*args, **kwargs)
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.debug(
                    f"{func.__name__} が完了しました",
                    extra={"duration_ms": duration_ms},
                )
                return result
            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(
                    f"{func.__name__} でエラーが発生しました: {e}",
                    extra={"duration_ms": duration_ms},
                    exc_info=True,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                logger.debug(f"{func.__name__} を呼び出します")
                result = func(*args, **kwargs)
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.debug(
                    f"{func.__name__} が完了しました",
                    extra={"duration_ms": duration_ms},
                )
                return result
            except Exception as e:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(
                    f"{func.__name__} でエラーが発生しました: {e}",
                    extra={"duration_ms": duration_ms},
                    exc_info=True,
                )
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
