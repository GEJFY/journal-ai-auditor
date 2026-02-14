"""SQLiteマネージャーのユニットテスト"""

import sqlite3

import pytest

from app.db.sqlite import SQLiteManager


@pytest.fixture
def sqlite_db(tmp_path):
    """テスト用SQLiteマネージャーを作成"""
    db_path = tmp_path / "test_meta.db"
    return SQLiteManager(db_path=db_path)


class TestSQLiteManager:
    """SQLiteManagerの基本操作テスト"""

    def test_initialization(self, sqlite_db):
        """初期化・ディレクトリ作成"""
        assert sqlite_db.db_path.parent.exists()

    def test_initialization_creates_directory(self, tmp_path):
        """存在しないディレクトリが作成される"""
        db_path = tmp_path / "subdir" / "nested" / "test.db"
        SQLiteManager(db_path=db_path)
        assert db_path.parent.exists()

    def test_connect_context_manager(self, sqlite_db):
        """コネクション取得・解放"""
        with sqlite_db.connect() as conn:
            assert isinstance(conn, sqlite3.Connection)
            # Row factory が設定されている
            assert conn.row_factory == sqlite3.Row

    def test_execute_create_table(self, sqlite_db):
        """テーブル作成"""
        with sqlite_db.connect() as conn:
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            conn.commit()

        rows = sqlite_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test'"
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "test"

    def test_execute_with_params(self, sqlite_db):
        """パラメータ付きクエリ"""
        with sqlite_db.connect() as conn:
            conn.execute("CREATE TABLE kv (key TEXT, value TEXT)")
            conn.execute("INSERT INTO kv VALUES ('a', '1')")
            conn.execute("INSERT INTO kv VALUES ('b', '2')")
            conn.commit()

        rows = sqlite_db.execute("SELECT * FROM kv WHERE key = ?", ("a",))
        assert len(rows) == 1
        assert rows[0]["value"] == "1"

    def test_execute_many(self, sqlite_db):
        """一括挿入"""
        with sqlite_db.connect() as conn:
            conn.execute("CREATE TABLE items (id INTEGER, name TEXT)")
            conn.commit()

        sqlite_db.execute_many(
            "INSERT INTO items (id, name) VALUES (?, ?)",
            [(1, "item1"), (2, "item2"), (3, "item3")],
        )
        rows = sqlite_db.execute("SELECT COUNT(*) as cnt FROM items")
        assert rows[0]["cnt"] == 3

    def test_insert(self, sqlite_db):
        """単一行挿入"""
        with sqlite_db.connect() as conn:
            conn.execute(
                "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age INTEGER)"
            )
            conn.commit()

        row_id = sqlite_db.insert("users", {"name": "Alice", "age": 30})
        assert row_id >= 1

        rows = sqlite_db.execute("SELECT * FROM users WHERE name = 'Alice'")
        assert len(rows) == 1
        assert rows[0]["age"] == 30

    def test_update(self, sqlite_db):
        """行更新"""
        with sqlite_db.connect() as conn:
            conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, status TEXT)")
            conn.execute("INSERT INTO items VALUES (1, 'pending')")
            conn.execute("INSERT INTO items VALUES (2, 'pending')")
            conn.commit()

        updated = sqlite_db.update(
            "items",
            {"status": "done"},
            "id = ?",
            (1,),
        )
        assert updated == 1

        rows = sqlite_db.execute("SELECT * FROM items WHERE id = 1")
        assert rows[0]["status"] == "done"

        # 未更新行は変わらない
        rows = sqlite_db.execute("SELECT * FROM items WHERE id = 2")
        assert rows[0]["status"] == "pending"


class TestSQLiteSchema:
    """スキーマ初期化のテスト"""

    def test_initialize_schema(self, sqlite_db):
        """全テーブルが作成される"""
        sqlite_db.initialize_schema()

        expected_tables = [
            "app_settings",
            "audit_rules",
            "analysis_sessions",
            "insights",
            "je_notes",
            "je_tags",
            "import_history",
            "filter_presets",
        ]

        for table in expected_tables:
            rows = sqlite_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            assert len(rows) == 1, f"Table {table} not created"

    def test_initialize_schema_idempotent(self, sqlite_db):
        """スキーマ初期化は冪等"""
        sqlite_db.initialize_schema()
        sqlite_db.initialize_schema()  # 2回目でもエラーにならない

        rows = sqlite_db.execute(
            "SELECT COUNT(*) as cnt FROM sqlite_master WHERE type='table'"
        )
        assert rows[0]["cnt"] >= 8

    def test_schema_insert_and_query(self, sqlite_db):
        """スキーマ初期化後のCRUD操作"""
        sqlite_db.initialize_schema()

        # app_settings にデータ挿入
        sqlite_db.insert(
            "app_settings",
            {"key": "theme", "value": "dark", "data_type": "string"},
        )

        rows = sqlite_db.execute("SELECT value FROM app_settings WHERE key = 'theme'")
        assert rows[0]["value"] == "dark"

    def test_schema_import_history(self, sqlite_db):
        """import_history テーブルのCRUD"""
        sqlite_db.initialize_schema()

        row_id = sqlite_db.insert(
            "import_history",
            {
                "filename": "test.csv",
                "file_type": "csv",
                "file_size": 1024,
                "row_count": 100,
                "status": "completed",
            },
        )
        assert row_id >= 1

        rows = sqlite_db.execute("SELECT * FROM import_history")
        assert len(rows) == 1
        assert rows[0]["filename"] == "test.csv"
