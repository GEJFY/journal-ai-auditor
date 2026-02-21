
import pytest
from app.db import DuckDBManager

@pytest.fixture
def setup_filter_data():
    db = DuckDBManager()
    
    # Clear existing data
    db.execute("DELETE FROM journal_entries")
    db.execute("DELETE FROM chart_of_accounts")

    # Insert Chart of Accounts
    # category, type, class, group, fs_line_item
    coa_data = [
        ('1001', 'Cash', 'BS', 'ASSET', 'Current Assets', 'Cash & Equivalents', 'Cash', 'debit', 1),
        ('1002', 'Bank', 'BS', 'ASSET', 'Current Assets', 'Cash & Equivalents', 'Cash', 'debit', 1),
        ('2001', 'Accounts Payable', 'BS', 'LIABILITY', 'Current Liabilities', 'Payables', 'Payables', 'credit', 1),
        ('4001', 'Sales', 'PL', 'REVENUE', 'Operating Revenue', 'Sales', 'Sales', 'credit', 1),
        ('5001', 'Cost of Goods Sold', 'PL', 'EXPENSE', 'Cost of Sales', 'Cost of Sales', 'COS', 'debit', 1),
    ]
    
    for row in coa_data:
        db.execute("""
            INSERT INTO chart_of_accounts (
                account_code, account_name, account_category, account_type, 
                account_class, account_group, fs_line_item, normal_balance, level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row)

    # Insert Journal Entries
    # Fiscal Year 2024
    # Columns: journal_id, gl_detail_id, fiscal_year, accounting_period, effective_date,
    # gl_account_number, amount, debit_credit_indicator, je_line_description, risk_score,
    # business_unit_code, entry_date, journal_id_line_number
    je_data = [
        # 1. Sales (Revenue)
        ('J001', 'J001-L001', 2024, 1, '2024-01-15', '1001', 1000, 'D', 'Sales Receipt', 10, 'BU1', '2024-01-15', 1),
        ('J001', 'J001-L002', 2024, 1, '2024-01-15', '4001', 1000, 'C', 'Sales Receipt', 10, 'BU1', '2024-01-15', 2),
        
        # 2. Payment (Expense)
        ('J002', 'J002-L001', 2024, 1, '2024-01-20', '2001', 500, 'D', 'Payment', 10, 'BU1', '2024-01-20', 1),
        ('J002', 'J002-L002', 2024, 1, '2024-01-20', '1002', 500, 'C', 'Payment', 10, 'BU1', '2024-01-20', 2),
        
        # 3. High Risk Entry
        ('J003', 'J003-L001', 2024, 2, '2024-02-01', '1001', 9999, 'D', 'Suspicious', 80, 'BU1', '2024-02-01', 1),
        ('J003', 'J003-L002', 2024, 2, '2024-02-01', '4001', 9999, 'C', 'Suspicious', 80, 'BU1', '2024-02-01', 2),
    ]

    for row in je_data:
        db.execute("""
            INSERT INTO journal_entries (
                journal_id, gl_detail_id, fiscal_year, accounting_period, effective_date,
                gl_account_number, amount, debit_credit_indicator,
                je_line_description, risk_score,
                business_unit_code, entry_date, journal_id_line_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row)

    yield
    
    # Cleanup
    db.execute("DELETE FROM journal_entries")
    db.execute("DELETE FROM chart_of_accounts")


def test_get_filter_options(client, setup_filter_data):
    response = client.get("/api/v1/dashboard/filter-options")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data['account_codes']) == 5
    assert "ASSET" in data['account_types']
    assert "Current Assets" in data['account_classes']
    assert "Sales" in data['fs_line_items']


def test_dashboard_summary_with_filters(client, setup_filter_data):
    # Filter by Account Type = REVENUE ('4001' only)
    # J001 (1000) and J003 (9999) hit 4001.
    response = client.get("/api/v1/dashboard/summary?fiscal_year=2024&account_types=REVENUE")
    assert response.status_code == 200
    data = response.json()
    
    # Total entries hitting REVENUE accounts: 2 lines
    assert data['total_entries'] == 2
    # Total amount: 1000 + 9999 = 10999
    assert data['total_amount'] == 10999


def test_dashboard_summary_with_multiple_filters(client, setup_filter_data):
    # Filter by Account Class = 'Current Assets' (1001, 1002)
    # J001 (1001: 1000), J002 (1002: 500), J003 (1001: 9999)
    # AND period_from = 2 (J003 only)
    response = client.get("/api/v1/dashboard/summary?fiscal_year=2024&account_classes=Current Assets&period_from=2")
    assert response.status_code == 200
    data = response.json()
    
    # Only J003 hits 1001 in period 2
    assert data['total_entries'] == 1
    assert data['total_amount'] == 9999.0


def test_time_series_with_filters(client, setup_filter_data):
    # Filter by Account Code 1001 (Cash)
    # J001 (Jan 15), J003 (Feb 01)
    response = client.get("/api/v1/dashboard/timeseries?fiscal_year=2024&account_codes=1001&aggregation=monthly")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data['data']) == 2
    # Jan
    assert data['data'][0]['date'].startswith('2024-01')
    assert data['data'][0]['amount'] == 1000.0
    # Feb
    assert data['data'][1]['date'].startswith('2024-02')
    assert data['data'][1]['amount'] == 9999.0


def test_risk_analysis_with_filters(client, setup_filter_data):
    # High risk query (>= 20)
    # J003 is score 80.
    # Filter by Account Group 'Cash & Equivalents' (1001, 1002)
    # J003 has line 1001 (Score 80).
    
    # Note: URL encoding for spaces and special chars is handled by params dict usually,
    # but here using encoded string in path or params.
    response = client.get(
        "/api/v1/dashboard/risk", 
        params={
            "fiscal_year": 2024,
            "account_groups": ["Cash & Equivalents"]
        }
    )
    assert response.status_code == 200
    data = response.json()

    # Should find J003
    assert len(data['high_risk']) == 1
    assert data['high_risk'][0]['journal_id'] == 'J003'
