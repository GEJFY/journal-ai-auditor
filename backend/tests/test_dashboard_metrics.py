
import pytest
from app.db import DuckDBManager

class TestDashboardMetrics:
    """Test /financial-metrics endpoint."""

    @pytest.fixture
    def setup_data(self):
        """Insert sample data for testing."""
        db = DuckDBManager()
        
        # Insert Chart of Accounts
        db.execute("DELETE FROM chart_of_accounts")
        db.execute("""
            INSERT INTO chart_of_accounts (
                account_code, account_name, account_type, account_class, 
                account_category, normal_balance, level
            ) VALUES
            ('1111', 'Cash', 'Asset', 'Current Asset', 'BS', 'debit', 1),
            ('2111', 'Accounts Payable', 'Liability', 'Current Liability', 'BS', 'credit', 1),
            ('3111', 'Capital', 'Equity', 'Equity', 'BS', 'credit', 1),
            ('4111', 'Sales', 'Revenue', 'Operating Revenue', 'PL', 'credit', 1),
            ('5111', 'Cost of Goods Sold', 'Expense', 'Cost of Sales', 'PL', 'debit', 1),
            ('6111', 'Rent Expense', 'Expense', 'Operating Expense', 'PL', 'debit', 1)
        """)

        # Insert Journal Entries
        # Fiscal Year 2024
        db.execute("DELETE FROM journal_entries")
        
        # Using simple values, ignoring unrelated columns
        base_query = """
            INSERT INTO journal_entries (
                journal_id, fiscal_year, accounting_period, 
                gl_account_number, amount, debit_credit_indicator,
                effective_date, entry_date, business_unit_code, journal_id_line_number,
                gl_detail_id
            ) VALUES (?, ?, ?, ?, ?, ?, '2024-04-01', '2024-04-01', 'BU1', 1, ?)
        """
        
        entries = [
            # ID, FY, Period, Account, Amount, D/C, DetailID
            ('JE01', 2024, 1, '4111', 1000, 'C', 'JE01-1'),
            ('JE01', 2024, 1, '1111', 1000, 'D', 'JE01-2'),
            
            ('JE02', 2024, 1, '5111', 600, 'D', 'JE02-1'),
            ('JE02', 2024, 1, '1111', 600, 'C', 'JE02-2'),
            
            ('JE03', 2024, 1, '6111', 200, 'D', 'JE03-1'),
            ('JE03', 2024, 1, '1111', 200, 'C', 'JE03-2'),
        ]
        
        for entry in entries:
            db.execute(base_query, entry)
            
        yield
        
        # Cleanup
        db.execute("DELETE FROM journal_entries")
        db.execute("DELETE FROM chart_of_accounts")

    def test_get_financial_metrics(self, client, setup_data):
        """Test getting financial metrics."""
        response = client.get("/api/v1/dashboard/financial-metrics", params={"fiscal_year": 2024})
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify PL Metrics
        pl = {item['label']: item for item in data['pl_metrics']}
        
        assert pl['Net Sales']['amount'] == 1000.0
        assert pl['Cost of Sales']['amount'] == 600.0
        assert pl['Gross Profit']['amount'] == 400.0
        assert pl['Operating Expenses']['amount'] == 200.0
        assert pl['Operating Income']['amount'] == 200.0
        assert pl['Net Income']['amount'] == 200.0
        
        # Verify BS Metrics
        bs = data['bs_metrics']
        # Cash = 1000 - 600 - 200 = 200
        assert bs['assets'] == 200.0
        assert bs['liabilities'] == 0.0
        assert bs['equity'] == 0.0
        
    def test_get_financial_metrics_empty(self, client):
        """Test with no data."""
        # Assuming database is empty or different FY
        response = client.get("/api/v1/dashboard/financial-metrics", params={"fiscal_year": 2099})
        assert response.status_code == 200
        data = response.json()
        
        bs = data['bs_metrics']
        assert bs['assets'] == 0.0
