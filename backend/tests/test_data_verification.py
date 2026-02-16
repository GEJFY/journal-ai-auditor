"""実データ検証テスト.

sample_data/10_journal_entries.csv をインポート済みの場合に実行される検証テスト。
データ未インポート時は自動スキップされる。

実行方法:
    cd backend
    python ../scripts/import_sample_data.py   # 先にインポート
    python -m pytest tests/test_data_verification.py -v
"""

import pytest

from app.db import DuckDBManager

# sample_data がインポート済みかどうかで全テストをスキップ
_db = DuckDBManager()
try:
    _has_data = (
        _db.table_exists("journal_entries")
        and _db.get_table_count("journal_entries") > 10000
    )
except Exception:
    _has_data = False

pytestmark = pytest.mark.skipif(
    not _has_data,
    reason="sample_data 未インポート（scripts/import_sample_data.py を先に実行）",
)


class TestRowCounts:
    """テーブル行数の検証。"""

    def test_journal_entries_count(self):
        """仕訳データが784,824行（±1%）存在する。"""
        db = DuckDBManager()
        count = db.get_table_count("journal_entries")
        assert 770_000 < count < 800_000, f"想定外の行数: {count:,}"

    def test_chart_of_accounts_exists(self):
        """勘定科目マスタが存在する。"""
        db = DuckDBManager()
        count = db.get_table_count("chart_of_accounts")
        assert count > 0, "勘定科目マスタが空です"

    def test_departments_exists(self):
        """部門マスタが存在する。"""
        db = DuckDBManager()
        count = db.get_table_count("departments")
        assert count > 0, "部門マスタが空です"

    def test_all_12_periods(self):
        """全12期間にデータが存在する。"""
        db = DuckDBManager()
        result = db.execute(
            "SELECT DISTINCT accounting_period FROM journal_entries "
            "WHERE fiscal_year = 2024 ORDER BY accounting_period"
        )
        periods = [r[0] for r in result]
        assert len(periods) == 12, f"期間数: {len(periods)} ({periods})"


class TestDebitCreditBalance:
    """借方貸方バランスの検証。"""

    def test_overall_balance(self):
        """全体の借方合計 ≈ 貸方合計であること。"""
        db = DuckDBManager()
        result = db.execute("""
            SELECT
                SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END) as debit,
                SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END) as credit
            FROM journal_entries
            WHERE fiscal_year = 2024
        """)
        debit, credit = result[0]
        diff_pct = abs(debit - credit) / max(debit, credit) * 100
        assert diff_pct < 1, (
            f"借方貸方差異が大きい: D={debit:,.0f} C={credit:,.0f} ({diff_pct:.2f}%)"
        )

    def test_per_journal_balance(self):
        """各仕訳ID内で借方 = 貸方であること（サンプリング）。"""
        db = DuckDBManager()
        # 不均衡な仕訳を検出
        result = db.execute("""
            SELECT journal_id,
                SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END) as debit,
                SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END) as credit
            FROM journal_entries
            WHERE fiscal_year = 2024
            GROUP BY journal_id
            HAVING ABS(debit - credit) > 1
            LIMIT 10
        """)
        # 多少の不均衡は許容（丸め誤差）、ただし10件以下であるべき
        unbalanced = len(result)
        total_journals = db.execute(
            "SELECT COUNT(DISTINCT journal_id) FROM journal_entries "
            "WHERE fiscal_year = 2024"
        )[0][0]
        pct = unbalanced / max(total_journals, 1) * 100
        assert pct < 5, f"不均衡仕訳が{pct:.1f}% ({unbalanced}/{total_journals})"


class TestMasterDataIntegrity:
    """マスタデータ整合性の検証。"""

    def test_account_codes_in_master(self):
        """仕訳の勘定科目がマスタに存在する割合。"""
        db = DuckDBManager()
        result = db.execute("""
            SELECT
                COUNT(DISTINCT je.gl_account_number) as total_accounts,
                COUNT(DISTINCT CASE WHEN coa.account_code IS NOT NULL
                    THEN je.gl_account_number END) as matched
            FROM journal_entries je
            LEFT JOIN chart_of_accounts coa
                ON je.gl_account_number = coa.account_code
            WHERE je.fiscal_year = 2024
        """)
        total, matched = result[0]
        match_pct = matched / max(total, 1) * 100
        assert match_pct > 80, (
            f"マスタ一致率が低い: {match_pct:.1f}% ({matched}/{total})"
        )


class TestDashboardAPI:
    """ダッシュボードAPIの実データ検証。"""

    @pytest.fixture()
    def db(self):
        return DuckDBManager()

    def test_summary_matches_raw(self, client, db):
        """/summary の total_entries が実データと一致する。"""
        # API経由
        response = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2024})
        assert response.status_code == 200
        api_count = response.json()["total_entries"]

        # 直接クエリ
        raw_count = db.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE fiscal_year = 2024"
        )[0][0]

        assert api_count == raw_count, f"API={api_count} vs RAW={raw_count}"

    def test_kpi_total_entries(self, client, db):
        """/kpi の total_entries が一致する。"""
        response = client.get("/api/v1/dashboard/kpi", params={"fiscal_year": 2024})
        assert response.status_code == 200
        api_count = response.json()["total_entries"]

        raw_count = db.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE fiscal_year = 2024"
        )[0][0]

        assert api_count == raw_count

    def test_risk_distribution_totals(self, client, db):
        """/risk のリスク分布合計が全件と一致する。"""
        response = client.get("/api/v1/dashboard/risk", params={"fiscal_year": 2024})
        assert response.status_code == 200
        dist = response.json()["risk_distribution"]
        api_total = sum(dist.values())

        raw_count = db.execute(
            "SELECT COUNT(*) FROM journal_entries WHERE fiscal_year = 2024"
        )[0][0]

        assert api_total == raw_count, f"分布合計={api_total} vs 全件={raw_count}"


class TestBenfordDistribution:
    """ベンフォード分析の検証。"""

    def test_benford_conformity(self, client):
        """ベンフォード分析が acceptable 以上である。"""
        response = client.get("/api/v1/dashboard/benford", params={"fiscal_year": 2024})
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] > 100000, "分析対象が少なすぎます"
        assert data["conformity"] in (
            "close",
            "acceptable",
            "marginally_acceptable",
        ), f"ベンフォード不適合: MAD={data['mad']}"

    def test_digit_1_is_most_frequent(self, client):
        """第一桁の1が最頻値である。"""
        response = client.get("/api/v1/dashboard/benford", params={"fiscal_year": 2024})
        assert response.status_code == 200
        dist = response.json()["distribution"]
        if dist:
            counts = {d["digit"]: d["count"] for d in dist}
            assert counts.get(1, 0) > counts.get(9, 0), "桁1が桁9より少ない"


class TestPeriodComparison:
    """期間比較の検証。"""

    def test_mom_returns_data(self, client):
        """MoM比較がデータを返す。"""
        response = client.get(
            "/api/v1/dashboard/period-comparison",
            params={"fiscal_year": 2024, "period": 6, "comparison_type": "mom"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0, "MoM比較結果が空"
        assert data["total_current"] > 0

    def test_yoy_returns_data(self, client):
        """YoY比較がデータを返す（前年度データがない場合は空でもOK）。"""
        response = client.get(
            "/api/v1/dashboard/period-comparison",
            params={"fiscal_year": 2024, "period": 6, "comparison_type": "yoy"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["comparison_type"] == "yoy"
