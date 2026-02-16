"""サンプルデータ一括インポートスクリプト.

sample_data/ 配下のCSVファイルをDuckDBとSQLiteにインポートする。
マスタデータ（勘定科目、部門、仕入先、ユーザー）＋仕訳データの順に読み込む。
冪等性あり（既存データをDROPして再作成）。

使い方:
    cd backend
    python ../scripts/import_sample_data.py
"""

import os
import sys
import time
from pathlib import Path

# パス設定
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sample_dir = project_root / "sample_data"

os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from app.core.config import settings  # noqa: E402, I001
from app.db import DuckDBManager  # noqa: E402


# CSV → テーブル マッピング
MASTER_FILES = [
    ("01_chart_of_accounts.csv", "chart_of_accounts"),
    ("02_department_master.csv", "departments"),
    ("03_vendor_master.csv", "vendors"),
    ("04_user_master.csv", "users"),
]

JE_FILE = ("10_journal_entries.csv", "journal_entries")


def import_csv(db: DuckDBManager, csv_path: Path, table: str) -> int:
    """CSVをDuckDBテーブルにインポートする."""
    csv_str = str(csv_path).replace("\\", "/")
    with db.connect() as cursor:
        # 既存データをクリアして再インポート
        cursor.execute(f"DELETE FROM {table}")
        cursor.execute(f"INSERT INTO {table} SELECT * FROM read_csv_auto('{csv_str}')")
        # DuckDBのINSERT...SELECTはcount返さないのでCOUNTで確認
    count = db.get_table_count(table)
    return count


def main() -> int:
    """メイン処理."""
    print("=" * 60)
    print("JAIA サンプルデータインポート")
    print("=" * 60)

    # ファイル存在確認
    missing = []
    for fname, _ in MASTER_FILES + [JE_FILE]:
        if not (sample_dir / fname).exists():
            missing.append(fname)
    if missing:
        print(f"エラー: ファイルが見つかりません: {missing}")
        return 1

    settings.ensure_data_dir()
    db = DuckDBManager()
    print(f"DB: {settings.duckdb_path.absolute()}")

    # スキーマ初期化
    print("\nスキーマ初期化中...")
    db.initialize_schema()
    print("  完了")

    total_start = time.time()

    # マスタデータ
    print("\n--- マスタデータ ---")
    for fname, table in MASTER_FILES:
        csv_path = sample_dir / fname
        start = time.time()
        count = import_csv(db, csv_path, table)
        elapsed = time.time() - start
        print(f"  {table}: {count:,}行 ({elapsed:.1f}s)")

    # 仕訳データ
    print("\n--- 仕訳データ ---")
    csv_path = sample_dir / JE_FILE[0]
    start = time.time()
    count = import_csv(db, csv_path, JE_FILE[1])
    elapsed = time.time() - start
    print(f"  journal_entries: {count:,}行 ({elapsed:.1f}s)")

    total_elapsed = time.time() - total_start
    db_size = settings.duckdb_path.stat().st_size / (1024 * 1024)
    print(f"\n完了: {total_elapsed:.1f}s / DB: {db_size:.1f}MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
