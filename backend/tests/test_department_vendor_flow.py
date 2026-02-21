"""部門・取引先分析 + 勘定科目フローのテスト.

Agent tools, Dashboard API, Aggregation を検証する。
"""

from unittest.mock import MagicMock, patch

import polars as pl
import pytest

# ============================================================
# Agent Tools テスト
# ============================================================


class TestAgentToolsDepartment:
    """analyze_department_patterns ツールのテスト."""

    def test_returns_json(self):
        """部門パターン分析がJSON文字列を返すこと."""
        mock_db = MagicMock()
        mock_db.execute_df.return_value = pl.DataFrame(
            {
                "dept_code": ["D001", "D002"],
                "entry_count": [100, 50],
                "avg_risk_score": [30.0, 55.0],
            }
        )

        with patch("app.agents.tools.duckdb_manager", mock_db):
            from app.agents.tools import analyze_department_patterns

            result = analyze_department_patterns.invoke(
                {
                    "fiscal_year": 2024,
                }
            )
            assert isinstance(result, str)
            assert "D001" in result

    def test_handles_error(self):
        """DBエラー時にエラーメッセージを返すこと."""
        mock_db = MagicMock()
        mock_db.execute_df.side_effect = Exception("table not found")

        with patch("app.agents.tools.duckdb_manager", mock_db):
            from app.agents.tools import analyze_department_patterns

            result = analyze_department_patterns.invoke(
                {
                    "fiscal_year": 2024,
                }
            )
            assert "error" in result


class TestAgentToolsVendor:
    """analyze_vendor_concentration ツールのテスト."""

    def test_returns_json(self):
        """取引先集中分析がJSON文字列を返すこと."""
        mock_db = MagicMock()
        mock_db.execute_df.return_value = pl.DataFrame(
            {
                "vendor_code": ["V001"],
                "transaction_count": [200],
                "total_amount": [50_000_000.0],
            }
        )

        with patch("app.agents.tools.duckdb_manager", mock_db):
            from app.agents.tools import analyze_vendor_concentration

            result = analyze_vendor_concentration.invoke(
                {
                    "fiscal_year": 2024,
                    "top_n": 10,
                }
            )
            assert "V001" in result


class TestAgentToolsAccountFlow:
    """analyze_account_flow ツールのテスト."""

    def test_returns_json(self):
        """勘定科目フロー分析がJSON文字列を返すこと."""
        mock_db = MagicMock()
        mock_db.execute_df.return_value = pl.DataFrame(
            {
                "source_account": ["1111"],
                "target_account": ["4111"],
                "transaction_count": [50],
                "flow_amount": [10_000_000.0],
            }
        )

        with patch("app.agents.tools.duckdb_manager", mock_db):
            from app.agents.tools import analyze_account_flow

            result = analyze_account_flow.invoke(
                {
                    "fiscal_year": 2024,
                }
            )
            assert "1111" in result


# ============================================================
# Tool Collection テスト
# ============================================================


class TestToolCollections:
    """ツールコレクションに新ツールが含まれること."""

    def test_analysis_tools_include_new(self):
        from app.agents.tools import ANALYSIS_TOOLS

        names = [t.name for t in ANALYSIS_TOOLS]
        assert "analyze_department_patterns" in names
        assert "analyze_vendor_concentration" in names
        assert "analyze_account_flow" in names

    def test_investigation_tools_include_new(self):
        from app.agents.tools import INVESTIGATION_TOOLS

        names = [t.name for t in INVESTIGATION_TOOLS]
        assert "analyze_department_patterns" in names
        assert "analyze_vendor_concentration" in names
        assert "analyze_account_flow" in names


# ============================================================
# Dashboard API テスト
# ============================================================


class TestDashboardDepartments:
    """GET /departments エンドポイントのテスト."""

    @pytest.mark.asyncio
    async def test_returns_departments(self):
        mock_db = MagicMock()
        mock_db.execute.return_value = [
            ("D001", 100, 50, 5_000_000, 5_000_000, 50_000, 3, 25.0, 5, 2),
            ("D002", 50, 25, 2_000_000, 2_000_000, 40_000, 2, 45.0, 10, 8),
        ]

        # Import first to ensure module is loaded
        from app.api.endpoints import dashboard as dashboard_mod

        with patch.object(dashboard_mod, "get_db", return_value=mock_db):
            result = await dashboard_mod.get_department_analysis(
                fiscal_year=2024,
                limit=50,
            )

            assert result["total"] == 2
            assert result["departments"][0]["dept_code"] == "D001"
            assert result["departments"][1]["self_approval_rate"] == 16.0


class TestDashboardVendors:
    """GET /vendors エンドポイントのテスト."""

    @pytest.mark.asyncio
    async def test_returns_vendors(self):
        mock_db = MagicMock()
        mock_db.execute.return_value = [
            (
                "V001",
                200,
                100,
                50_000_000,
                250_000,
                5_000_000,
                30.0,
                75.0,
                5,
                "2024-04-01",
                "2025-03-31",
            ),
        ]

        from app.api.endpoints import dashboard as dashboard_mod

        with patch.object(dashboard_mod, "get_db", return_value=mock_db):
            result = await dashboard_mod.get_vendor_analysis(
                fiscal_year=2024,
                limit=50,
            )

            assert result["total"] == 1
            assert result["vendors"][0]["vendor_code"] == "V001"
            assert result["vendors"][0]["total_amount"] == 50_000_000


class TestDashboardAccountFlow:
    """GET /account-flow エンドポイントのテスト."""

    @pytest.mark.asyncio
    async def test_returns_flows(self):
        mock_db = MagicMock()
        mock_db.execute.return_value = [
            ("1111", "4111", 50, 10_000_000, 200_000),
            ("5111", "2121", 30, 5_000_000, 166_667),
        ]

        from app.api.endpoints import dashboard as dashboard_mod

        with patch.object(dashboard_mod, "get_db", return_value=mock_db):
            result = await dashboard_mod.get_account_flow(
                fiscal_year=2024,
                min_amount=0,
                limit=50,
            )

            assert result["total"] == 2
            assert result["flows"][0]["source_account"] == "1111"
            assert result["flows"][0]["target_account"] == "4111"

    @pytest.mark.asyncio
    async def test_handles_error(self):
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("table error")

        from app.api.endpoints import dashboard as dashboard_mod

        with patch.object(dashboard_mod, "get_db", return_value=mock_db):
            result = await dashboard_mod.get_account_flow(
                fiscal_year=2024,
                min_amount=0,
                limit=50,
            )
            assert result["flows"] == []
