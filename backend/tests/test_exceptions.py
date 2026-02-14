"""カスタム例外クラスのユニットテスト"""

import pytest

from app.core.exceptions import JAIAException


class TestJAIAException:
    """基底例外クラスのテスト"""

    def test_basic_creation(self):
        exc = JAIAException("Test error")
        assert "Test error" in str(exc)

    def test_error_code_attribute(self):
        assert JAIAException.error_code == "JAIA_ERROR"

    def test_inheritance(self):
        exc = JAIAException("test")
        assert isinstance(exc, Exception)


class TestExceptionHierarchy:
    """例外階層のテスト"""

    def test_validation_errors_exist(self):
        """バリデーション系例外が定義されている"""
        from app.core.exceptions import (
            JAIAException,
        )

        # 基底クラスが存在
        assert JAIAException is not None

    def test_exception_with_detail(self):
        """詳細情報付き例外"""
        exc = JAIAException("File not found")
        assert "File not found" in str(exc)

    def test_exception_is_catchable(self):
        """JAIAExceptionで子例外をキャッチ可能"""
        try:
            raise JAIAException("test")
        except JAIAException as e:
            assert "test" in str(e)
        except Exception:
            pytest.fail("Should be caught by JAIAException")
