"""
JAIA テスト用共通フィクスチャ

pytest用の共通フィクスチャとヘルパー関数を提供します。
"""

import atexit
import os
import shutil
import tempfile
from collections.abc import Generator
from datetime import date, time
from pathlib import Path

import polars as pl
import pytest
from fastapi.testclient import TestClient

# テスト用環境変数（モジュールレベルで設定 - settings = Settings() より前に必要）
_test_data_dir = tempfile.mkdtemp(prefix="jaia_test_")
atexit.register(shutil.rmtree, _test_data_dir, ignore_errors=True)

os.environ["DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["DATA_DIR"] = _test_data_dir
os.environ["DUCKDB_PATH"] = str(Path(_test_data_dir) / "test.duckdb")
os.environ["SQLITE_PATH"] = str(Path(_test_data_dir) / "test.db")


@pytest.fixture(scope="session")
def temp_data_dir() -> Generator[Path, None, None]:
    """
    テスト用の一時データディレクトリを作成します。

    Yields:
        Path: 一時ディレクトリパス
    """
    yield Path(_test_data_dir)


@pytest.fixture(scope="session")
def test_settings():
    """
    テスト用の設定を取得します。
    """
    from app.core.config import Settings

    return Settings()


@pytest.fixture(scope="session")
def app(test_settings):
    """
    テスト用のFastAPIアプリケーションを作成します。
    """
    from app.main import create_app

    return create_app()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """テスト毎にレートリミッターをリセットし、429エラーを防止します。"""
    from app.core.middleware import rate_limiter

    rate_limiter.requests.clear()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """
    テスト用のHTTPクライアントを作成します。
    Context managerでlifespanイベントを起動します。

    Yields:
        TestClient: FastAPIテストクライアント
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_journal_entries() -> pl.DataFrame:
    """
    テスト用のサンプル仕訳データを生成します。

    Returns:
        pl.DataFrame: サンプル仕訳データ
    """
    data = {
        "gl_detail_id": [
            "JE001-001",
            "JE001-002",
            "JE002-001",
            "JE002-002",
            "JE003-001",
            "JE003-002",
            "JE004-001",
            "JE004-002",
            "JE005-001",
            "JE005-002",
        ],
        "business_unit_code": ["GP001"] * 10,
        "fiscal_year": [2024] * 10,
        "accounting_period": [1, 1, 2, 2, 3, 3, 3, 3, 4, 4],
        "journal_id": [
            "JE001",
            "JE001",
            "JE002",
            "JE002",
            "JE003",
            "JE003",
            "JE004",
            "JE004",
            "JE005",
            "JE005",
        ],
        "journal_id_line_number": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
        "effective_date": [
            date(2024, 4, 1),
            date(2024, 4, 1),
            date(2024, 5, 15),
            date(2024, 5, 15),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 7, 15),
            date(2024, 7, 15),
        ],
        "entry_date": [
            date(2024, 4, 1),
            date(2024, 4, 1),
            date(2024, 5, 15),
            date(2024, 5, 15),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 7, 15),
            date(2024, 7, 15),
        ],
        "entry_time": [
            time(9, 0),
            time(9, 0),
            time(10, 30),
            time(10, 30),
            time(23, 55),
            time(23, 55),  # 営業時間外
            time(14, 0),
            time(14, 0),
            time(11, 0),
            time(11, 0),
        ],
        "gl_account_number": [
            "1131",
            "4111",  # 売掛金/売上
            "1131",
            "4111",
            "1131",
            "4111",
            "5111",
            "2121",  # 費用/買掛金
            "1111",
            "1131",  # 現金/売掛金
        ],
        "amount": [
            100000,
            100000,
            500000,
            500000,
            150000000,
            150000000,  # 重要性基準超過
            50000,
            50000,
            1000000,
            1000000,
        ],
        "functional_amount": [
            100000,
            100000,
            500000,
            500000,
            150000000,
            150000000,
            50000,
            50000,
            1000000,
            1000000,
        ],
        "debit_credit_indicator": [
            "D",
            "C",
            "D",
            "C",
            "D",
            "C",
            "D",
            "C",
            "D",
            "C",
        ],
        "je_line_description": [
            "売上計上 顧客A",
            "売上計上 顧客A",
            "売上計上 顧客B",
            "売上計上 顧客B",
            "決算調整",
            "決算調整",
            "仕入計上",
            "仕入計上",
            "入金処理",
            "入金処理",
        ],
        "source": [
            "SALES",
            "SALES",
            "SALES",
            "SALES",
            "MANUAL",
            "MANUAL",
            "AP",
            "AP",
            "AR",
            "AR",
        ],
        "prepared_by": [
            "U001",
            "U001",
            "U002",
            "U002",
            "U001",
            "U001",
            "U003",
            "U003",
            "U001",
            "U001",
        ],
        "approved_by": [
            "U002",
            "U002",
            "U003",
            "U003",
            "U001",
            "U001",
            "U001",
            "U001",
            "U002",
            "U002",
        ],  # JE003は自己承認
        "approved_date": [
            date(2024, 4, 2),
            date(2024, 4, 2),
            date(2024, 5, 16),
            date(2024, 5, 16),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 6, 30),
            date(2024, 7, 16),
            date(2024, 7, 16),
        ],
    }

    return pl.DataFrame(data)


@pytest.fixture
def sample_journal_entries_with_anomalies() -> pl.DataFrame:
    """
    異常パターンを含むサンプル仕訳データを生成します。

    Returns:
        pl.DataFrame: 異常パターンを含むサンプルデータ
    """
    data = {
        "gl_detail_id": [f"ANOM{i:03d}-001" for i in range(1, 11)],
        "business_unit_code": ["GP001"] * 10,
        "fiscal_year": [2024] * 10,
        "accounting_period": [3] * 10,  # 全て期末
        "journal_id": [f"ANOM{i:03d}" for i in range(1, 11)],
        "journal_id_line_number": [1] * 10,
        "effective_date": [date(2024, 6, 30)] * 10,  # 期末集中
        "entry_date": [date(2024, 6, 30)] * 10,
        "entry_time": [
            time(23, 58),
            time(23, 59),  # 営業時間外
            time(2, 30),
            time(3, 45),  # 深夜
            time(9, 0),
            time(10, 0),
            time(11, 0),
            time(12, 0),
            time(13, 0),
            time(14, 0),
        ],
        "gl_account_number": [
            "1131",
            "1131",
            "1111",
            "5999",  # 異常科目組み合わせ
            "1131",
            "1131",
            "1131",
            "1131",
            "1131",
            "1131",
        ],
        "amount": [
            100000000,  # 丸め金額
            99999999,  # 端数異常
            1000000,
            500000,
            10000,
            20000,
            30000,
            40000,
            50000,
            60000,
        ],
        "functional_amount": [
            100000000,
            99999999,
            1000000,
            500000,
            10000,
            20000,
            30000,
            40000,
            50000,
            60000,
        ],
        "debit_credit_indicator": ["D"] * 10,
        "je_line_description": [
            "決算調整",
            "期末調整",
            "現金補正",
            "雑費",
            "売上",
            "売上",
            "売上",
            "売上",
            "売上",
            "売上",
        ],
        "source": ["MANUAL"] * 4 + ["SALES"] * 6,
        "prepared_by": ["U001"] * 10,
        "approved_by": ["U001"] * 4 + ["U002"] * 6,  # 最初の4件は自己承認
        "approved_date": [date(2024, 6, 30)] * 10,
    }

    return pl.DataFrame(data)


@pytest.fixture
def sample_chart_of_accounts() -> list[dict]:
    """
    テスト用の勘定科目マスタを生成します。

    Returns:
        list[dict]: 勘定科目データ
    """
    return [
        {
            "gl_account_number": "1111",
            "gl_account_name": "現金",
            "account_type": "Asset",
            "fs_caption": "現金及び預金",
        },
        {
            "gl_account_number": "1131",
            "gl_account_name": "売掛金",
            "account_type": "Asset",
            "fs_caption": "売掛金",
        },
        {
            "gl_account_number": "2121",
            "gl_account_name": "買掛金",
            "account_type": "Liability",
            "fs_caption": "買掛金",
        },
        {
            "gl_account_number": "4111",
            "gl_account_name": "売上高",
            "account_type": "Revenue",
            "fs_caption": "売上高",
        },
        {
            "gl_account_number": "5111",
            "gl_account_name": "売上原価",
            "account_type": "Expense",
            "fs_caption": "売上原価",
        },
        {
            "gl_account_number": "5999",
            "gl_account_name": "雑費",
            "account_type": "Expense",
            "fs_caption": "販管費",
        },
    ]


@pytest.fixture
def benford_test_data() -> list[float]:
    """
    Benford分析用のテストデータを生成します。

    正常なBenford分布に従うデータを生成。

    Returns:
        list[float]: テスト用金額データ
    """
    import random

    random.seed(42)
    data = []

    # Benfordの法則に従う分布を生成
    for _ in range(1000):
        # べき乗分布でBenfordの法則に近い分布を生成
        value = 10 ** (random.random() * 6)  # 1 ~ 1,000,000
        data.append(round(value, 2))

    return data


@pytest.fixture
def project_root() -> Path:
    """
    プロジェクトルートディレクトリを取得します。

    Returns:
        Path: プロジェクトルート
    """
    return Path(__file__).parent.parent.parent


@pytest.fixture
def sample_data_dir(project_root: Path) -> Path:
    """
    サンプルデータディレクトリを取得します。

    Returns:
        Path: サンプルデータディレクトリ
    """
    return project_root / "sample_data"


# ========================================
# ヘルパー関数
# ========================================


def assert_api_success(response) -> dict:
    """
    APIレスポンスが成功であることを確認し、データを返します。

    Args:
        response: HTTPレスポンス

    Returns:
        dict: レスポンスデータ
    """
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )
    data = response.json()
    assert data.get("success", True), f"API returned error: {data}"
    return data


def assert_api_error(response, expected_status: int = 400, expected_code: str = None):
    """
    APIレスポンスがエラーであることを確認します。

    Args:
        response: HTTPレスポンス
        expected_status: 期待するHTTPステータスコード
        expected_code: 期待するエラーコード
    """
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}"
    )
    data = response.json()
    assert not data.get("success") or "error" in data

    if expected_code:
        assert data.get("error", {}).get("error_code") == expected_code
