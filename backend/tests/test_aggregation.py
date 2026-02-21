"""集計サービスのユニットテスト"""

from unittest.mock import MagicMock

from app.services.aggregation import AggregationResult, AggregationService


class TestAggregationResult:
    """集計結果データクラスのテスト"""

    def test_success_result(self):
        result = AggregationResult(
            table_name="agg_by_date",
            rows_affected=100,
            execution_time_ms=15.5,
            success=True,
        )
        assert result.table_name == "agg_by_date"
        assert result.rows_affected == 100
        assert result.success is True
        assert result.error is None

    def test_error_result(self):
        result = AggregationResult(
            table_name="agg_by_user",
            rows_affected=0,
            execution_time_ms=5.0,
            success=False,
            error="Table not found",
        )
        assert result.success is False
        assert result.error == "Table not found"


class TestAggregationService:
    """集計サービスのテスト"""

    def test_initialization_with_db(self):
        """カスタムDBで初期化"""
        mock_db = MagicMock()
        service = AggregationService(db=mock_db)
        assert service.db is mock_db

    def test_update_all_returns_list(self):
        """update_allがAggregationResultのリストを返す"""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = MagicMock(return_value=False)
        # COUNT(*) クエリの結果を設定
        mock_conn.execute.return_value.fetchone.return_value = [0]

        service = AggregationService(db=mock_db)
        results = service.update_all(fiscal_year=2024)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, AggregationResult) for r in results)

    def test_update_all_covers_17_tables(self):
        """17テーブルすべてが処理される"""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchone.return_value = [0]

        service = AggregationService(db=mock_db)
        results = service.update_all()

        # 17テーブル + agg_account_flow = 18テーブル
        assert len(results) == 18

    def test_execute_aggregation_success(self):
        """集計クエリの成功パス"""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchone.return_value = [42]

        service = AggregationService(db=mock_db)
        result = service._execute_aggregation(
            "agg_test", "INSERT INTO agg_test SELECT 1"
        )

        assert result.success is True
        assert result.rows_affected == 42
        assert result.execution_time_ms > 0

    def test_execute_aggregation_failure(self):
        """集計クエリの失敗パス"""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.side_effect = Exception("Table does not exist")

        service = AggregationService(db=mock_db)
        result = service._execute_aggregation("bad_table", "SELECT 1")

        assert result.success is False
        assert "Table does not exist" in result.error

    def test_update_all_without_fiscal_year(self):
        """fiscal_year未指定でも動作"""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchone.return_value = [0]

        service = AggregationService(db=mock_db)
        results = service.update_all(fiscal_year=None)

        assert isinstance(results, list)
        assert len(results) == 18
