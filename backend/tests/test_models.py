"""Pydanticモデルのユニットテスト"""

from datetime import date, time

import pytest
from pydantic import ValidationError

from app.models.journal import JournalEntryBase


class TestJournalEntryBase:
    """仕訳エントリモデルのバリデーションテスト"""

    def _valid_entry_data(self, **overrides):
        """有効なテストデータを生成"""
        data = {
            "business_unit_code": "GP001",
            "fiscal_year": 2024,
            "accounting_period": 1,
            "journal_id": "JE001",
            "journal_id_line_number": 1,
            "effective_date": date(2024, 4, 1),
            "entry_date": date(2024, 4, 1),
            "gl_account_number": "1111",
            "amount": 100000,
            "debit_credit_indicator": "D",
        }
        data.update(overrides)
        return data

    def test_valid_entry(self):
        """正常なデータでインスタンス生成"""
        entry = JournalEntryBase(**self._valid_entry_data())
        assert entry.business_unit_code == "GP001"
        assert entry.fiscal_year == 2024
        assert entry.journal_id == "JE001"

    def test_fiscal_year_min(self):
        """会計年度の下限バリデーション"""
        with pytest.raises(ValidationError):
            JournalEntryBase(**self._valid_entry_data(fiscal_year=1899))

    def test_fiscal_year_max(self):
        """会計年度の上限バリデーション"""
        with pytest.raises(ValidationError):
            JournalEntryBase(**self._valid_entry_data(fiscal_year=2101))

    def test_accounting_period_min(self):
        """会計期間の下限バリデーション"""
        with pytest.raises(ValidationError):
            JournalEntryBase(**self._valid_entry_data(accounting_period=0))

    def test_accounting_period_max(self):
        """会計期間の上限（13=調整期）"""
        entry = JournalEntryBase(**self._valid_entry_data(accounting_period=13))
        assert entry.accounting_period == 13

    def test_accounting_period_over_max(self):
        """会計期間が14以上はエラー"""
        with pytest.raises(ValidationError):
            JournalEntryBase(**self._valid_entry_data(accounting_period=14))

    def test_line_number_min(self):
        """行番号の下限バリデーション"""
        with pytest.raises(ValidationError):
            JournalEntryBase(**self._valid_entry_data(journal_id_line_number=0))

    def test_optional_entry_time(self):
        """入力時刻はオプション"""
        entry = JournalEntryBase(**self._valid_entry_data())
        assert entry.entry_time is None

        entry_with_time = JournalEntryBase(
            **self._valid_entry_data(entry_time=time(9, 30))
        )
        assert entry_with_time.entry_time == time(9, 30)

    def test_required_fields_missing(self):
        """必須フィールドが欠けるとエラー"""
        with pytest.raises(ValidationError):
            JournalEntryBase(
                business_unit_code="GP001",
                fiscal_year=2024,
                # journal_id 欠落
            )


class TestConfigModels:
    """設定関連モデルのテスト"""

    def test_llm_models_dict(self):
        """LLM_MODELSが正しく定義されている"""
        from app.core.config import LLM_MODELS

        assert "anthropic" in LLM_MODELS
        assert "openai" in LLM_MODELS
        assert "bedrock" in LLM_MODELS
        assert "azure_foundry" in LLM_MODELS
        assert "vertex_ai" in LLM_MODELS
        assert "google" in LLM_MODELS
        assert "ollama" in LLM_MODELS
        assert "azure" in LLM_MODELS

    def test_recommended_models(self):
        """RECOMMENDED_MODELSが全ユースケースをカバー"""
        from app.core.config import RECOMMENDED_MODELS

        expected_keys = [
            "highest_accuracy",
            "high_accuracy",
            "balanced",
            "cost_effective",
            "ultra_fast",
            "local_dev",
        ]
        for key in expected_keys:
            assert key in RECOMMENDED_MODELS
            assert "provider" in RECOMMENDED_MODELS[key]
            assert "model" in RECOMMENDED_MODELS[key]

    def test_settings_defaults(self):
        """Settings のデフォルト値"""
        from app.core.config import settings

        assert settings.app_name == "JAIA"
        assert settings.port == 8001
        assert settings.llm_provider in [
            "anthropic",
            "openai",
            "google",
            "bedrock",
            "azure_foundry",
            "vertex_ai",
            "azure",
            "ollama",
        ]

    def test_settings_get_available_models(self):
        """利用可能モデル取得"""
        from app.core.config import settings

        models = settings.get_available_models()
        assert isinstance(models, dict)

    def test_settings_get_recommended_model(self):
        """推奨モデル取得"""
        from app.core.config import settings

        model = settings.get_recommended_model("balanced")
        assert "provider" in model
        assert "model" in model

    def test_settings_get_recommended_model_default(self):
        """不明なユースケースはbalancedにフォールバック"""
        from app.core.config import settings

        model = settings.get_recommended_model("nonexistent")
        assert model == settings.get_recommended_model("balanced")
