"""バッチ処理サービスのユニットテスト"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import polars as pl

from app.services.batch import (
    BatchConfig,
    BatchMode,
    BatchOrchestrator,
    BatchResult,
)

# ============================================================
# BatchMode / BatchConfig / BatchResult データクラステスト
# ============================================================


class TestBatchMode:
    """バッチモード列挙型のテスト"""

    def test_full_mode(self):
        assert BatchMode.FULL == "full"

    def test_incremental_mode(self):
        assert BatchMode.INCREMENTAL == "incremental"

    def test_quick_mode(self):
        assert BatchMode.QUICK == "quick"

    def test_ml_only_mode(self):
        assert BatchMode.ML_ONLY == "ml_only"

    def test_rules_only_mode(self):
        assert BatchMode.RULES_ONLY == "rules_only"


class TestBatchConfig:
    """バッチ設定のテスト"""

    def test_default_config(self):
        config = BatchConfig()
        assert config.mode == BatchMode.FULL
        assert config.fiscal_year is None
        assert config.parallel_execution is True
        assert config.max_workers == 4
        assert config.update_aggregations is True
        assert config.store_violations is True
        assert config.update_risk_scores is True

    def test_custom_config(self):
        config = BatchConfig(
            mode=BatchMode.QUICK,
            fiscal_year=2024,
            parallel_execution=False,
            max_workers=2,
        )
        assert config.mode == BatchMode.QUICK
        assert config.fiscal_year == 2024
        assert config.parallel_execution is False
        assert config.max_workers == 2


class TestBatchResult:
    """バッチ結果のテスト"""

    def test_default_result(self):
        result = BatchResult(batch_id="test-001", mode=BatchMode.FULL)
        assert result.batch_id == "test-001"
        assert result.mode == BatchMode.FULL
        assert result.total_entries == 0
        assert result.rules_executed == 0
        assert result.total_violations == 0
        assert result.errors == []

    def test_success_property_no_errors(self):
        result = BatchResult(
            batch_id="test-002",
            mode=BatchMode.FULL,
            completed_at=datetime.now(),
        )
        assert result.success is True

    def test_success_property_with_errors(self):
        result = BatchResult(
            batch_id="test-003",
            mode=BatchMode.FULL,
            completed_at=datetime.now(),
            errors=["Rule execution failed"],
        )
        assert result.success is False

    def test_success_property_not_completed(self):
        result = BatchResult(batch_id="test-004", mode=BatchMode.FULL)
        assert result.success is False

    def test_to_dict(self):
        result = BatchResult(
            batch_id="test-005",
            mode=BatchMode.FULL,
            total_entries=100,
            rules_executed=10,
            total_violations=5,
            scoring_completed=True,
            entries_scored=50,
        )
        d = result.to_dict()
        assert d["batch_id"] == "test-005"
        assert d["mode"] == "full"
        assert d["total_entries"] == 100
        assert d["rules_executed"] == 10
        assert d["total_violations"] == 5
        assert d["scoring_completed"] is True
        assert d["entries_scored"] == 50
        assert isinstance(d["started_at"], str)

    def test_to_dict_phase_timings_rounded(self):
        result = BatchResult(
            batch_id="test-006",
            mode=BatchMode.FULL,
            phase_timings={"load_data": 1.23456, "rule_execution": 99.99999},
        )
        d = result.to_dict()
        assert d["phase_timings"]["load_data"] == 1.23
        assert d["phase_timings"]["rule_execution"] == 100.0


# ============================================================
# BatchOrchestrator テスト
# ============================================================


class TestBatchOrchestrator:
    """バッチオーケストレーターのテスト"""

    @patch("app.services.batch.DuckDBManager")
    def test_initialization(self, mock_db_cls):
        """オーケストレーターの初期化"""
        mock_db = MagicMock()
        orch = BatchOrchestrator(db=mock_db)
        assert orch.db is mock_db
        assert orch.rule_engine is not None
        assert orch.scoring_service is not None
        assert orch.aggregation_service is not None

    @patch("app.services.batch.DuckDBManager")
    def test_register_rule_sets(self, mock_db_cls):
        """6カテゴリのルールセットが登録される"""
        mock_db = MagicMock()
        orch = BatchOrchestrator(db=mock_db)
        # rule_engine にルールセットが登録されていることを確認
        assert len(orch.rule_engine._rule_sets) >= 6

    @patch("app.services.batch.DuckDBManager")
    def test_execute_empty_data(self, mock_db_cls):
        """データがない場合の実行"""
        mock_db = MagicMock()
        mock_db.connect.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db.connect.return_value.__exit__ = MagicMock(return_value=False)

        orch = BatchOrchestrator(db=mock_db)

        # _load_data をモックして空DataFrameを返す
        with patch.object(orch, "_load_data", return_value=pl.DataFrame()):
            result = orch.execute(BatchConfig())
            assert result.total_entries == 0
            assert result.completed_at is not None
