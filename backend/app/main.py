"""
JAIA FastAPI Application Entry Point

JAIAアプリケーションのメインエントリーポイントです。

機能:
- FastAPIアプリケーションの作成と設定
- ミドルウェアの設定（CORS、ロギング、エラーハンドリング）
- データベースの初期化
- APIルーターの登録

使用方法:
    開発環境:
        uvicorn app.main:app --reload --log-level debug

    本番環境:
        uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8090
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.core.config import settings
from app.core.logging import audit_log, get_logger, setup_logging
from app.core.middleware import setup_audit_middleware, setup_middleware
from app.db import DuckDBManager, SQLiteManager

# ロギングシステムを初期化
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    アプリケーションのライフサイクル管理。

    起動時の初期化処理とシャットダウン時のクリーンアップ処理を行います。

    Args:
        app: FastAPIアプリケーションインスタンス

    Yields:
        None: アプリケーション実行期間
    """
    # ========================================
    # スタートアップ処理
    # ========================================
    startup_time = datetime.now()
    logger.info(
        f"{settings.app_name} v{settings.app_version} を起動します",
        extra={"environment": settings.environment},
    )

    # 監査ログに記録
    audit_log.info(
        "アプリケーション起動",
        extra={
            "event_type": "application_startup",
            "app_version": settings.app_version,
            "environment": settings.environment,
        },
    )

    # データディレクトリの確保
    logger.info("データディレクトリを確認しています...")
    settings.ensure_data_dir()
    logger.info(f"データディレクトリ: {settings.data_dir}")

    # データベースの初期化
    logger.info("データベースを初期化しています...")
    try:
        duckdb = DuckDBManager()
        sqlite = SQLiteManager()

        duckdb.initialize_schema()
        logger.info(f"DuckDB スキーマを初期化しました: {settings.duckdb_path}")

        sqlite.initialize_schema()
        logger.info(f"SQLite スキーマを初期化しました: {settings.sqlite_path}")

    except Exception as e:
        logger.error(f"データベースの初期化に失敗しました: {e}", exc_info=True)
        raise

    # 起動完了
    startup_duration = (datetime.now() - startup_time).total_seconds()
    logger.info(
        f"{settings.app_name} の起動が完了しました",
        extra={"startup_duration_seconds": startup_duration},
    )

    yield

    # ========================================
    # シャットダウン処理
    # ========================================
    logger.info(f"{settings.app_name} をシャットダウンします...")

    # 監査ログに記録
    audit_log.info(
        "アプリケーションシャットダウン",
        extra={
            "event_type": "application_shutdown",
        },
    )

    logger.info(f"{settings.app_name} のシャットダウンが完了しました")


def create_app() -> FastAPI:
    """
    FastAPIアプリケーションを作成・設定します。

    以下の設定を行います:
    - アプリケーション基本設定（タイトル、バージョン等）
    - CORSミドルウェア
    - ロギングミドルウェア
    - エラーハンドリングミドルウェア
    - 監査ログミドルウェア
    - APIルーター

    Returns:
        FastAPI: 設定済みのFastAPIアプリケーションインスタンス
    """
    logger.info("FastAPIアプリケーションを作成しています...")

    # FastAPIインスタンスを作成
    app = FastAPI(
        title=settings.app_name,
        description="""
        # JAIA - Journal entry AI Analyzer

        AI駆動の仕訳データ分析・内部監査支援システム

        ## 主な機能

        - **データインポート**: Excel/CSVファイルからの仕訳データ取り込み
        - **ダッシュボード**: KPI、リスク分布、時系列分析の可視化
        - **リスク分析**: 58の監査ルールによる違反検出
        - **AI分析**: AIエージェントによる自律的な分析
        - **レポート生成**: PPT/PDF形式での監査報告書出力

        ## APIバージョン

        現在のAPIバージョン: v1
        """,
        version=settings.app_version,
        lifespan=lifespan,
        # 本番環境ではSwagger UIを無効化（セキュリティ上の理由）
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
    )

    # ========================================
    # CORSミドルウェア
    # ========================================
    # 開発環境ではローカルホストからのアクセスを許可
    cors_origins = [
        "http://localhost:5290",
        "http://127.0.0.1:5290",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Processing-Time-Ms"],
    )
    logger.debug(f"CORSミドルウェアを設定しました: {cors_origins}")

    # ========================================
    # カスタムミドルウェア
    # ========================================
    # リクエストロギング・エラーハンドリング
    setup_middleware(app)

    # 監査ログミドルウェア
    setup_audit_middleware(app)

    # ========================================
    # APIルーター
    # ========================================
    app.include_router(api_router, prefix="/api/v1")
    logger.debug("APIルーターを登録しました: /api/v1")

    # ========================================
    # ルートエンドポイント
    # ========================================
    @app.get("/health", tags=["System"])
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    @app.get("/", tags=["System"])
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "description": "AI駆動の仕訳データ分析・内部監査支援システム",
            "version": settings.app_version,
            "docs_url": "/docs" if settings.debug else None,
            "api_url": "/api/v1",
        }

    logger.info("FastAPIアプリケーションの作成が完了しました")

    return app


# アプリケーションインスタンス
app = create_app()
