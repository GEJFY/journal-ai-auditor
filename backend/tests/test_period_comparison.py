"""期間比較APIのテスト."""

import pytest


class TestPeriodComparisonAPI:
    """期間比較エンドポイントのテスト。"""

    def test_mom_comparison(self, client):
        """前月比の正常レスポンスを確認する。"""
        response = client.get(
            "/api/v1/dashboard/period-comparison",
            params={
                "fiscal_year": 2024,
                "period": 2,
                "comparison_type": "mom",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["comparison_type"] == "mom"
        assert "items" in data
        assert "current_period" in data
        assert "previous_period" in data
        assert isinstance(data["items"], list)

    def test_yoy_comparison(self, client):
        """前年同月比の正常レスポンスを確認する。"""
        response = client.get(
            "/api/v1/dashboard/period-comparison",
            params={
                "fiscal_year": 2024,
                "period": 3,
                "comparison_type": "yoy",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["comparison_type"] == "yoy"

    def test_mom_period_1(self, client):
        """第1期の前月比は空リストを返す。"""
        response = client.get(
            "/api/v1/dashboard/period-comparison",
            params={
                "fiscal_year": 2024,
                "period": 1,
                "comparison_type": "mom",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["previous_period"] == "N/A"

    def test_invalid_comparison_type(self, client):
        """無効な比較タイプはバリデーションエラー。"""
        response = client.get(
            "/api/v1/dashboard/period-comparison",
            params={
                "fiscal_year": 2024,
                "period": 2,
                "comparison_type": "invalid",
            },
        )
        assert response.status_code == 422

    def test_missing_period(self, client):
        """period未指定はバリデーションエラー。"""
        response = client.get(
            "/api/v1/dashboard/period-comparison",
            params={
                "fiscal_year": 2024,
                "comparison_type": "mom",
            },
        )
        assert response.status_code == 422

    def test_response_structure(self, client):
        """レスポンス構造の確認。"""
        response = client.get(
            "/api/v1/dashboard/period-comparison",
            params={
                "fiscal_year": 2024,
                "period": 6,
                "comparison_type": "mom",
                "limit": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_current" in data
        assert "total_previous" in data
        # items内のフィールド確認
        for item in data["items"]:
            assert "account_code" in item
            assert "account_name" in item
            assert "current_amount" in item
            assert "previous_amount" in item
            assert "change_amount" in item
            assert "change_percent" in item
