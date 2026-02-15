"""
JAIA ミドルウェア

FastAPIアプリケーションに適用するミドルウェアを定義します。

機能:
- リクエストID生成・伝播
- リクエスト/レスポンスロギング
- エラーハンドリング
- パフォーマンス測定
- セキュリティ対策（レート制限、IP制限、ヘッダー保護）

使用例:
    from fastapi import FastAPI
    from app.core.middleware import setup_middleware

    app = FastAPI()
    setup_middleware(app)
"""

import time
import traceback
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from threading import Lock

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import (
    JAIAException,
)
from app.core.logging import (
    audit_log,
    get_logger,
    get_request_id,
    perf_log,
    security_log,
    set_request_id,
)

logger = get_logger(__name__)


# =============================================================================
# セキュリティ設定
# =============================================================================


class SecurityConfig:
    """セキュリティ設定を管理するクラス"""

    # レート制限設定
    RATE_LIMIT_REQUESTS = 100  # リクエスト数
    RATE_LIMIT_WINDOW_SECONDS = 60  # 時間ウィンドウ（秒）

    # IPブロック設定
    BLOCKED_IPS: set[str] = set()  # 永久ブロックIP
    TEMP_BLOCK_THRESHOLD = 10  # 一時ブロックまでの違反回数
    TEMP_BLOCK_DURATION_MINUTES = 15  # 一時ブロック期間（分）

    # 疑わしいパターン
    SUSPICIOUS_PATTERNS = [
        "../",
        "..\\",  # ディレクトリトラバーサル
        "<script",
        "</script>",  # XSS
        "' OR ",
        '" OR ',  # SQL Injection
        "${",
        "#{",  # Template Injection
        "{{",
        "}}",  # SSTI
    ]

    # セキュリティヘッダー
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    # ホワイトリストパス（レート制限除外）
    RATE_LIMIT_WHITELIST = [
        "/health",
        "/api/v1/health",
        "/docs",
        "/openapi.json",
    ]


# =============================================================================
# レート制限ミドルウェア
# =============================================================================


class RateLimiter:
    """
    スライディングウィンドウ方式のレート制限。

    メモリ内でリクエスト履歴を管理し、
    設定されたウィンドウ内のリクエスト数を制限します。
    """

    def __init__(
        self,
        max_requests: int = SecurityConfig.RATE_LIMIT_REQUESTS,
        window_seconds: int = SecurityConfig.RATE_LIMIT_WINDOW_SECONDS,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        """
        リクエストが許可されるかどうかを判定します。

        Args:
            client_id: クライアント識別子（通常はIPアドレス）

        Returns:
            bool: 許可される場合True
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            # 古いリクエストを削除
            self.requests[client_id] = [
                ts for ts in self.requests[client_id] if ts > window_start
            ]

            # リクエスト数をチェック
            if len(self.requests[client_id]) >= self.max_requests:
                return False

            # 現在のリクエストを追加
            self.requests[client_id].append(now)
            return True

    def get_remaining(self, client_id: str) -> int:
        """残りリクエスト数を取得"""
        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            current_count = len(
                [ts for ts in self.requests[client_id] if ts > window_start]
            )
            return max(0, self.max_requests - current_count)

    def get_reset_time(self, client_id: str) -> int:
        """リセットまでの秒数を取得"""
        if not self.requests[client_id]:
            return 0

        oldest = min(self.requests[client_id])
        reset_time = oldest + self.window_seconds - time.time()
        return max(0, int(reset_time))


# グローバルレートリミッターインスタンス
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    レート制限ミドルウェア。

    IPアドレスベースでリクエスト数を制限し、
    過剰なリクエストを拒否します。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # ホワイトリストパスはスキップ
        if any(path.startswith(p) for p in SecurityConfig.RATE_LIMIT_WHITELIST):
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        if not rate_limiter.is_allowed(client_ip):
            security_log.warning(
                f"レート制限超過: {client_ip}",
                extra={
                    "event_type": "rate_limit_exceeded",
                    "client_ip": client_ip,
                    "path": path,
                },
            )

            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "リクエスト数が制限を超えました。しばらく待ってから再試行してください。",
                    },
                    "meta": {
                        "retry_after": rate_limiter.get_reset_time(client_ip),
                    },
                },
                headers={
                    "Retry-After": str(rate_limiter.get_reset_time(client_ip)),
                    "X-RateLimit-Limit": str(rate_limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)

        # レート制限ヘッダーを追加
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            rate_limiter.get_remaining(client_ip)
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """クライアントIPを取得（プロキシ対応）"""
        # X-Forwarded-For ヘッダーを確認（プロキシ経由の場合）
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 最初のIPを取得（実際のクライアントIP）
            return forwarded_for.split(",")[0].strip()

        # X-Real-IP ヘッダーを確認
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 直接接続のクライアントIP
        return request.client.host if request.client else "unknown"


# =============================================================================
# IP制限ミドルウェア
# =============================================================================


class IPBlockManager:
    """
    IPブロック管理クラス。

    永久ブロックと一時ブロックを管理し、
    違反回数に基づいて自動的にブロックします。
    """

    def __init__(self):
        self.permanent_blocks: set[str] = SecurityConfig.BLOCKED_IPS.copy()
        self.temp_blocks: dict[str, datetime] = {}
        self.violation_counts: dict[str, int] = defaultdict(int)
        self.lock = Lock()

    def is_blocked(self, ip: str) -> bool:
        """IPがブロックされているかどうかを確認"""
        # 永久ブロック確認
        if ip in self.permanent_blocks:
            return True

        # 一時ブロック確認
        with self.lock:
            if ip in self.temp_blocks:
                if datetime.now() < self.temp_blocks[ip]:
                    return True
                else:
                    # ブロック期限切れ
                    del self.temp_blocks[ip]
                    self.violation_counts[ip] = 0

        return False

    def record_violation(self, ip: str) -> None:
        """違反を記録し、必要に応じて一時ブロック"""
        with self.lock:
            self.violation_counts[ip] += 1

            if self.violation_counts[ip] >= SecurityConfig.TEMP_BLOCK_THRESHOLD:
                self.temp_blocks[ip] = datetime.now() + timedelta(
                    minutes=SecurityConfig.TEMP_BLOCK_DURATION_MINUTES
                )
                security_log.warning(
                    f"IP一時ブロック: {ip}（違反回数: {self.violation_counts[ip]}）",
                    extra={
                        "event_type": "ip_temp_blocked",
                        "client_ip": ip,
                        "violation_count": self.violation_counts[ip],
                        "block_duration_minutes": SecurityConfig.TEMP_BLOCK_DURATION_MINUTES,
                    },
                )

    def add_permanent_block(self, ip: str) -> None:
        """永久ブロックに追加"""
        with self.lock:
            self.permanent_blocks.add(ip)
            security_log.warning(
                f"IP永久ブロック追加: {ip}",
                extra={
                    "event_type": "ip_permanent_blocked",
                    "client_ip": ip,
                },
            )

    def remove_block(self, ip: str) -> None:
        """ブロックを解除"""
        with self.lock:
            self.permanent_blocks.discard(ip)
            self.temp_blocks.pop(ip, None)
            self.violation_counts[ip] = 0


# グローバルIPブロックマネージャー
ip_block_manager = IPBlockManager()


class IPBlockMiddleware(BaseHTTPMiddleware):
    """
    IPブロックミドルウェア。

    ブロックリストに登録されたIPからのリクエストを拒否します。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)

        if ip_block_manager.is_blocked(client_ip):
            security_log.warning(
                f"ブロックIP からのアクセス拒否: {client_ip}",
                extra={
                    "event_type": "blocked_ip_access",
                    "client_ip": client_ip,
                    "path": request.url.path,
                },
            )

            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {
                        "error_code": "IP_BLOCKED",
                        "message": "アクセスが制限されています。",
                    },
                },
            )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """クライアントIPを取得"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"


# =============================================================================
# セキュリティヘッダーミドルウェア
# =============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    セキュリティヘッダーを追加するミドルウェア。

    XSS、クリックジャッキング、MIMEタイプスニッフィングなどの
    攻撃を防ぐためのセキュリティヘッダーを追加します。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # セキュリティヘッダーを追加
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value

        return response


# =============================================================================
# 疑わしいリクエスト検出ミドルウェア
# =============================================================================


class SuspiciousActivityMiddleware(BaseHTTPMiddleware):
    """
    疑わしいリクエストを検出するミドルウェア。

    SQLインジェクション、XSS、ディレクトリトラバーサルなどの
    攻撃パターンを検出し、ログに記録します。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        path = request.url.path
        query_string = str(request.url.query) if request.url.query else ""

        # パスとクエリをチェック
        check_content = f"{path}?{query_string}".lower()

        for pattern in SecurityConfig.SUSPICIOUS_PATTERNS:
            if pattern.lower() in check_content:
                security_log.warning(
                    f"疑わしいリクエスト検出: {pattern}",
                    extra={
                        "event_type": "suspicious_request",
                        "client_ip": client_ip,
                        "path": path,
                        "query_string": query_string,
                        "pattern_matched": pattern,
                    },
                )

                # 違反を記録
                ip_block_manager.record_violation(client_ip)

                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": {
                            "error_code": "SUSPICIOUS_REQUEST",
                            "message": "不正なリクエストが検出されました。",
                        },
                    },
                )

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """クライアントIPを取得"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    リクエスト/レスポンスをログ出力するミドルウェア。

    全てのHTTPリクエストとレスポンスを記録し、
    リクエストIDによるトレーサビリティを提供します。
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        リクエストを処理し、ログを出力します。

        Args:
            request: HTTPリクエスト
            call_next: 次のミドルウェア/ハンドラ

        Returns:
            Response: HTTPレスポンス
        """
        # リクエストIDを設定（ヘッダーから取得または生成）
        request_id = request.headers.get("X-Request-ID")
        request_id = set_request_id(request_id)

        # 開始時刻を記録
        start_time = time.time()

        # リクエストの基本情報
        method = request.method
        path = request.url.path
        query_string = str(request.url.query) if request.url.query else ""
        client_ip = request.client.host if request.client else "unknown"

        # リクエスト開始をログ出力
        logger.info(
            f"リクエスト開始: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "query_string": query_string,
                "client_ip": client_ip,
            },
        )

        # リクエスト処理
        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            # 予期しないエラーの場合
            logger.error(
                f"予期しないエラー: {e}",
                exc_info=True,
                extra={
                    "method": method,
                    "path": path,
                },
            )
            raise

        # 処理時間を計算
        duration_ms = (time.time() - start_time) * 1000

        # レスポンスにリクエストIDヘッダーを追加
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Processing-Time-Ms"] = f"{duration_ms:.2f}"

        # リクエスト完了をログ出力
        log_level = logger.warning if status_code >= 400 else logger.info
        log_level(
            f"リクエスト完了: {method} {path} -> {status_code}",
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            },
        )

        # パフォーマンスログ
        perf_log.info(
            f"HTTP {method} {path}",
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

        return response


async def jaia_exception_handler(request: Request, exc: JAIAException) -> JSONResponse:
    """
    JAIA例外をJSONレスポンスに変換するハンドラ。

    Args:
        request: HTTPリクエスト
        exc: JAIA例外

    Returns:
        JSONResponse: エラー情報を含むJSONレスポンス
    """
    request_id = get_request_id()

    # エラーログを出力
    logger.error(
        f"JAIAException: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "detail": exc.detail,
        },
    )

    return JSONResponse(
        status_code=exc.http_status_code,
        content={
            "success": False,
            "error": exc.to_dict(),
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        },
        headers={"X-Request-ID": request_id},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    一般的な例外をJSONレスポンスに変換するハンドラ。

    Args:
        request: HTTPリクエスト
        exc: 例外

    Returns:
        JSONResponse: エラー情報を含むJSONレスポンス
    """
    request_id = get_request_id()

    # エラーログを出力（スタックトレース含む）
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)

    # 本番環境ではスタックトレースを隠す
    if settings.debug:
        detail = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        }
    else:
        detail = {}

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "error_code": "INTERNAL_ERROR",
                "message": "内部エラーが発生しました"
                if not settings.debug
                else str(exc),
                "detail": detail,
            },
            "meta": {
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        },
        headers={"X-Request-ID": request_id},
    )


def setup_middleware(app: FastAPI) -> None:
    """
    FastAPIアプリケーションにミドルウェアを設定します。

    ミドルウェアは登録順とは逆順に実行されます。
    つまり、最後に登録したミドルウェアが最初に実行されます。

    実行順序（リクエスト時）:
    1. SecurityHeadersMiddleware - セキュリティヘッダー
    2. IPBlockMiddleware - IPブロック
    3. RateLimitMiddleware - レート制限
    4. SuspiciousActivityMiddleware - 不正リクエスト検出
    5. RequestLoggingMiddleware - リクエストログ
    6. AuditLogMiddleware - 監査ログ

    Args:
        app: FastAPIアプリケーションインスタンス
    """
    # 監査ログミドルウェア（最後に実行）
    app.add_middleware(AuditLogMiddleware)

    # リクエストロギングミドルウェア
    app.add_middleware(RequestLoggingMiddleware)

    # 疑わしいリクエスト検出
    app.add_middleware(SuspiciousActivityMiddleware)

    # レート制限ミドルウェア
    app.add_middleware(RateLimitMiddleware)

    # IPブロックミドルウェア
    app.add_middleware(IPBlockMiddleware)

    # セキュリティヘッダーミドルウェア（最初に実行）
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS設定（本番環境では適切なオリジンを設定）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5290", "http://127.0.0.1:5290"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 例外ハンドラを登録
    app.add_exception_handler(JAIAException, jaia_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("ミドルウェアを設定しました（セキュリティ機能有効）")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    監査ログを出力するミドルウェア。

    特定のエンドポイントに対するアクセスを監査ログに記録します。
    """

    # 監査対象のパスパターン
    AUDIT_PATHS = [
        "/api/v1/import",
        "/api/v1/batch",
        "/api/v1/analysis",
        "/api/v1/reports",
        "/api/v1/agents",
        "/api/v1/settings",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        リクエストを処理し、必要に応じて監査ログを出力します。

        Args:
            request: HTTPリクエスト
            call_next: 次のミドルウェア/ハンドラ

        Returns:
            Response: HTTPレスポンス
        """
        path = request.url.path

        # 監査対象かどうかを確認
        should_audit = any(path.startswith(p) for p in self.AUDIT_PATHS)

        if should_audit:
            # リクエスト情報を収集
            method = request.method
            client_ip = request.client.host if request.client else "unknown"

            # 監査ログを出力
            audit_log.info(
                f"監査対象アクセス: {method} {path}",
                extra={
                    "event_type": "api_access",
                    "method": method,
                    "path": path,
                    "client_ip": client_ip,
                },
            )

        response = await call_next(request)

        if should_audit:
            # レスポンス後の監査ログ
            audit_log.info(
                f"監査対象レスポンス: {method} {path} -> {response.status_code}",
                extra={
                    "event_type": "api_response",
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                },
            )

        return response


def setup_audit_middleware(app: FastAPI) -> None:
    """
    監査ログミドルウェアを設定します。

    Args:
        app: FastAPIアプリケーションインスタンス
    """
    app.add_middleware(AuditLogMiddleware)
    logger.info("監査ログミドルウェアを設定しました")
