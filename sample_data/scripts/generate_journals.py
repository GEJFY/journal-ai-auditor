#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Journal Entry Generator for JAIA Sample Data
グローバル塗料株式会社 - 仕訳データ生成スクリプト

This script generates realistic journal entries with embedded
fraud and anomaly patterns for testing the JAIA audit system.
"""

import csv
import random
import uuid
from datetime import datetime, timedelta, time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SCRIPT_DIR / "config.yaml"


def load_config() -> dict:
    """Load configuration from YAML file."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_master_data() -> Tuple[Dict, Dict, Dict, Dict]:
    """Load all master data files."""
    accounts = {}
    with open(DATA_DIR / "01_chart_of_accounts.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["is_posting"] == "1" and row["is_active"] == "1":
                accounts[row["account_code"]] = row

    departments = {}
    with open(DATA_DIR / "02_department_master.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["is_active"] == "1":
                departments[row["dept_code"]] = row

    vendors = {}
    with open(DATA_DIR / "03_vendor_master.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["is_active"] == "1":
                vendors[row["vendor_code"]] = row

    users = {}
    with open(DATA_DIR / "04_user_master.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["is_active"] == "1":
                users[row["user_id"]] = row

    return accounts, departments, vendors, users


class JournalGenerator:
    """Main journal entry generator class."""

    def __init__(self, config: dict, accounts: dict, departments: dict,
                 vendors: dict, users: dict):
        self.config = config
        self.accounts = accounts
        self.departments = departments
        self.vendors = vendors
        self.users = users
        self.journals: List[dict] = []
        self.fraud_catalog: List[dict] = []
        self.anomaly_catalog: List[dict] = []

        # Set random seed for reproducibility
        random.seed(config.get("random_seed", 42))

        # Parse fiscal dates
        self.fiscal_start = datetime.strptime(
            config["fiscal"]["start_date"], "%Y-%m-%d"
        )
        self.fiscal_end = datetime.strptime(
            config["fiscal"]["end_date"], "%Y-%m-%d"
        )

        # Prepare user lists
        self.approvers = [
            uid for uid, u in users.items() if u["can_approve"] == "1"
        ]
        self.staff = [
            uid for uid, u in users.items()
            if u["can_approve"] == "0" or u["role"] == "STAFF"
        ]
        self.all_users = list(users.keys())

        # Customer and supplier lists
        self.customers = [
            vc for vc, v in vendors.items() if v["vendor_type"] == "CUSTOMER"
        ]
        self.suppliers = [
            vc for vc, v in vendors.items() if v["vendor_type"] == "SUPPLIER"
        ]
        self.intercompany = [
            vc for vc, v in vendors.items() if v["vendor_type"] == "INTERCOMPANY"
        ]

    def generate_journal_id(self) -> str:
        """Generate a unique journal ID."""
        return f"JE{uuid.uuid4().hex[:12].upper()}"

    def get_random_date(self, month: Optional[int] = None) -> datetime:
        """Get a random date within the fiscal year."""
        if month:
            # Convert month to fiscal year month (Apr=4, Mar=3)
            if month >= 4:
                year = self.fiscal_start.year
            else:
                year = self.fiscal_end.year
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year, 12, 31)
            elif month in [4, 6, 9, 11]:
                end = datetime(year, month, 30)
            elif month == 2:
                end = datetime(year, month, 28)
            else:
                end = datetime(year, month, 31)
        else:
            start = self.fiscal_start
            end = self.fiscal_end

        delta = (end - start).days
        return start + timedelta(days=random.randint(0, delta))

    def get_random_time(self, late_night: bool = False) -> time:
        """Get a random time of day."""
        if late_night:
            hour = random.randint(22, 23)
        else:
            hour = random.randint(8, 18)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        return time(hour, minute, second)

    def get_random_amount(self, min_val: int = 1, max_val: int = None,
                          round_number: bool = False) -> int:
        """Get a random amount based on distribution."""
        dist = self.config["amount_distribution"]

        if max_val:
            # Use specified range
            amount = random.randint(min_val, max_val)
        else:
            # Use configured distribution
            r = random.random()
            cumulative = 0
            for bucket in dist:
                cumulative += bucket["weight"]
                if r <= cumulative:
                    amount = random.randint(bucket["range"][0], bucket["range"][1])
                    break
            else:
                amount = random.randint(1, 100000)

        if round_number:
            # Round to nice numbers for anomaly pattern
            magnitude = len(str(amount)) - 1
            divisor = 10 ** magnitude
            amount = (amount // divisor) * divisor

        return amount

    def create_journal_entry(
        self,
        effective_date: datetime,
        entries: List[Tuple[str, str, int]],  # (account_code, dc_indicator, amount)
        description: str,
        prepared_by: str,
        approved_by: Optional[str] = None,
        vendor_code: Optional[str] = None,
        dept_code: Optional[str] = None,
        entry_time: Optional[time] = None,
        source: str = "MANUAL",
        fraud_flag: Optional[str] = None,
        anomaly_flag: Optional[str] = None
    ) -> str:
        """Create a complete journal entry with multiple lines."""
        journal_id = self.generate_journal_id()
        entry_date = effective_date
        if entry_time is None:
            entry_time = self.get_random_time()

        # Determine approval
        if approved_by is None:
            # Find appropriate approver
            total_amount = sum(e[2] for e in entries if e[1] == "D")
            for uid in self.approvers:
                limit = int(self.users[uid]["approval_limit"])
                if total_amount <= limit:
                    approved_by = uid
                    break
            if approved_by is None:
                approved_by = "U200"  # CFO

        approval_date = effective_date + timedelta(days=random.randint(0, 2))

        for line_num, (account_code, dc_indicator, amount) in enumerate(entries, 1):
            if account_code not in self.accounts:
                continue

            record = {
                "gl_detail_id": f"{journal_id}-{line_num:03d}",
                "business_unit_code": self.config["company"]["code"],
                "fiscal_year": self.config["fiscal"]["year"],
                "accounting_period": effective_date.month,
                "journal_id": journal_id,
                "journal_id_line_number": line_num,
                "effective_date": effective_date.strftime("%Y-%m-%d"),
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "entry_time": entry_time.strftime("%H:%M:%S"),
                "gl_account_number": account_code,
                "amount": amount,
                "amount_currency": "JPY",
                "functional_amount": amount,
                "debit_credit_indicator": dc_indicator,
                "je_line_description": description,
                "source": source,
                "vendor_code": vendor_code or "",
                "dept_code": dept_code or "",
                "prepared_by": prepared_by,
                "approved_by": approved_by,
                "approved_date": approval_date.strftime("%Y-%m-%d"),
                "last_modified_by": prepared_by,
                "last_modified_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fraud_flag": fraud_flag or "",
                "anomaly_flag": anomaly_flag or ""
            }
            self.journals.append(record)

        return journal_id

    # ========================================
    # Normal Business Transaction Generators
    # ========================================

    def generate_sales_entries(self, count: int):
        """Generate normal sales journal entries."""
        print(f"Generating {count} sales entries...")

        customers_normal = [c for c in self.customers if not c.startswith("V90")]
        sales_accounts = ["4111", "4112", "4113", "4114", "4115", "4120", "4130"]

        for _ in range(count):
            customer = random.choice(customers_normal)
            sales_account = random.choice(sales_accounts)
            amount = self.get_random_amount()
            date = self.get_random_date()
            user = random.choice(self.staff)
            dept = random.choice(["2110", "2120", "2210", "2310", "2410"])

            # Sales entry: Dr. AR, Cr. Sales
            self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("1131", "D", amount),
                    (sales_account, "C", amount)
                ],
                description=f"売上計上 {self.vendors[customer]['vendor_name']}",
                prepared_by=user,
                vendor_code=customer,
                dept_code=dept,
                source="SALES"
            )

    def generate_purchase_entries(self, count: int):
        """Generate normal purchase journal entries."""
        print(f"Generating {count} purchase entries...")

        for _ in range(count):
            supplier = random.choice(self.suppliers)
            amount = self.get_random_amount()
            date = self.get_random_date()
            user = random.choice(self.staff)

            # Purchase entry: Dr. Materials/Expense, Cr. AP
            if random.random() < 0.7:
                # Raw materials
                debit_account = "1154"
                desc = f"原材料仕入 {self.vendors[supplier]['vendor_name']}"
            else:
                # Services/other
                debit_account = random.choice(["5243", "5244", "5235"])
                desc = f"経費計上 {self.vendors[supplier]['vendor_name']}"

            self.create_journal_entry(
                effective_date=date,
                entries=[
                    (debit_account, "D", amount),
                    ("2121", "C", amount)
                ],
                description=desc,
                prepared_by=user,
                vendor_code=supplier,
                dept_code="4410",
                source="PURCHASE"
            )

    def generate_expense_entries(self, count: int):
        """Generate normal expense journal entries."""
        print(f"Generating {count} expense entries...")

        expense_accounts = [
            "5230", "5231", "5232", "5233", "5234", "5235", "5236",
            "5240", "5241", "5260", "5261", "5270"
        ]
        expense_descs = {
            "5230": "出張旅費",
            "5231": "通信費",
            "5232": "水道光熱費",
            "5233": "消耗品費",
            "5234": "事務用品費",
            "5235": "修繕費",
            "5236": "保険料",
            "5240": "地代家賃",
            "5241": "リース料",
            "5260": "接待交際費",
            "5261": "会議費",
            "5270": "雑費"
        }

        for _ in range(count):
            account = random.choice(expense_accounts)
            amount = self.get_random_amount(max_val=3000000)
            date = self.get_random_date()
            user = random.choice(self.staff)
            dept = random.choice(list(self.departments.keys()))

            self.create_journal_entry(
                effective_date=date,
                entries=[
                    (account, "D", amount),
                    ("2140", "C", amount)
                ],
                description=expense_descs.get(account, "経費"),
                prepared_by=user,
                dept_code=dept,
                source="EXPENSE"
            )

    def generate_payroll_entries(self, count: int):
        """Generate payroll journal entries."""
        print(f"Generating {count} payroll entries...")

        for _ in range(count // 12):  # Monthly
            for month in range(4, 13):
                date = datetime(2023, month, 25)
                amount = random.randint(80000000, 120000000)

                # Payroll: Dr. Salaries, Cr. Cash + Withholding
                withholding = int(amount * 0.15)
                social = int(amount * 0.15)
                net = amount - withholding - social

                self.create_journal_entry(
                    effective_date=date,
                    entries=[
                        ("5211", "D", amount),
                        ("1112", "C", net),
                        ("2171", "C", withholding),
                        ("2172", "C", social)
                    ],
                    description=f"{month}月分給与支給",
                    prepared_by="U002",
                    approved_by="U001",
                    dept_code="1310",
                    source="PAYROLL"
                )

            # Jan-Mar of next year
            for month in range(1, 4):
                date = datetime(2024, month, 25)
                amount = random.randint(80000000, 120000000)
                withholding = int(amount * 0.15)
                social = int(amount * 0.15)
                net = amount - withholding - social

                self.create_journal_entry(
                    effective_date=date,
                    entries=[
                        ("5211", "D", amount),
                        ("1112", "C", net),
                        ("2171", "C", withholding),
                        ("2172", "C", social)
                    ],
                    description=f"{month}月分給与支給",
                    prepared_by="U002",
                    approved_by="U001",
                    dept_code="1310",
                    source="PAYROLL"
                )

    def generate_depreciation_entries(self, count: int):
        """Generate depreciation journal entries."""
        print(f"Generating {count} depreciation entries...")

        depr_pairs = [
            ("1221", "5238", "建物減価償却費"),
            ("1222", "5238", "建物附属設備減価償却費"),
            ("1224", "5125", "機械装置減価償却費"),
            ("1225", "5238", "車両減価償却費"),
            ("1226", "5238", "工具器具備品減価償却費")
        ]

        for month in range(4, 13):
            date = datetime(2023, month, 28)
            for accum, expense, desc in depr_pairs:
                amount = random.randint(10000000, 50000000)
                self.create_journal_entry(
                    effective_date=date,
                    entries=[
                        (expense, "D", amount),
                        (accum, "C", amount)
                    ],
                    description=f"{month}月分{desc}",
                    prepared_by="U003",
                    approved_by="U002",
                    dept_code="1210",
                    source="DEPRECIATION"
                )

        for month in range(1, 4):
            date = datetime(2024, month, 28)
            for accum, expense, desc in depr_pairs:
                amount = random.randint(10000000, 50000000)
                self.create_journal_entry(
                    effective_date=date,
                    entries=[
                        (expense, "D", amount),
                        (accum, "C", amount)
                    ],
                    description=f"{month}月分{desc}",
                    prepared_by="U003",
                    approved_by="U002",
                    dept_code="1210",
                    source="DEPRECIATION"
                )

    # ========================================
    # Fraud Pattern Generators
    # ========================================

    def generate_fraud_f01_self_approval(self, count: int):
        """F01: Self-approval journal entries."""
        print(f"Generating {count} F01 (self-approval) entries...")

        for i in range(count):
            # User approves their own entry
            user = random.choice(self.approvers)
            amount = self.get_random_amount(min_val=5000000)
            date = self.get_random_date()

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("5260", "D", amount),  # Entertainment
                    ("1112", "C", amount)
                ],
                description="接待交際費（自己承認）",
                prepared_by=user,
                approved_by=user,  # Same person
                dept_code="2110",
                source="MANUAL",
                fraud_flag="F01"
            )

            self.fraud_catalog.append({
                "pattern_id": "F01",
                "journal_id": journal_id,
                "description": "自己承認仕訳",
                "risk_level": "HIGH",
                "amount": amount,
                "user_id": user
            })

    def generate_fraud_f02_fictitious_sales(self, count: int):
        """F02: Fictitious sales to fake vendors."""
        print(f"Generating {count} F02 (fictitious sales) entries...")

        fake_vendors = ["V9001", "V9002"]

        for i in range(count):
            vendor = random.choice(fake_vendors)
            amount = random.randint(10000000, 100000000)
            date = self.get_random_date()
            user = "U901"  # Suspicious user

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("1131", "D", amount),
                    ("4111", "C", amount)
                ],
                description=f"売上計上 {self.vendors[vendor]['vendor_name']}",
                prepared_by=user,
                vendor_code=vendor,
                dept_code="2110",
                source="MANUAL",
                fraud_flag="F02"
            )

            self.fraud_catalog.append({
                "pattern_id": "F02",
                "journal_id": journal_id,
                "description": "架空売上計上",
                "risk_level": "CRITICAL",
                "amount": amount,
                "vendor_code": vendor
            })

    def generate_fraud_f03_circular_trading(self, count: int):
        """F03: Circular trading pattern."""
        print(f"Generating {count} F03 (circular trading) entries...")

        # Create circular pattern: IC1 -> IC2 -> IC3 -> IC1
        ic_chain = ["V2001", "V2002", "V2003"]

        for i in range(count // 3):
            amount = random.randint(50000000, 500000000)
            base_date = self.get_random_date()

            for j, (from_ic, to_ic) in enumerate([
                (ic_chain[0], ic_chain[1]),
                (ic_chain[1], ic_chain[2]),
                (ic_chain[2], ic_chain[0])
            ]):
                date = base_date + timedelta(days=j * 5)

                journal_id = self.create_journal_entry(
                    effective_date=date,
                    entries=[
                        ("1133", "D", amount),  # IC Receivable
                        ("4140", "C", amount)   # IC Sales
                    ],
                    description=f"グループ間売上 {self.vendors[to_ic]['vendor_name']}",
                    prepared_by="U007",
                    vendor_code=to_ic,
                    dept_code="2510",
                    source="INTERCOMPANY",
                    fraud_flag="F03"
                )

                self.fraud_catalog.append({
                    "pattern_id": "F03",
                    "journal_id": journal_id,
                    "description": "循環取引",
                    "risk_level": "CRITICAL",
                    "amount": amount,
                    "from_entity": from_ic,
                    "to_entity": to_ic
                })

    def generate_fraud_f04_period_end_sales(self, count: int):
        """F04: Period-end concentrated sales."""
        print(f"Generating {count} F04 (period-end sales) entries...")

        # Last 5 days of March
        for i in range(count):
            day = random.randint(27, 31)
            date = datetime(2024, 3, day)
            customer = random.choice(self.customers[:10])  # Major customers
            amount = random.randint(50000000, 300000000)

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("1131", "D", amount),
                    ("4111", "C", amount)
                ],
                description=f"期末売上計上 {self.vendors[customer]['vendor_name']}",
                prepared_by="U033",
                vendor_code=customer,
                dept_code="2110",
                source="SALES",
                fraud_flag="F04"
            )

            self.fraud_catalog.append({
                "pattern_id": "F04",
                "journal_id": journal_id,
                "description": "期末偏重売上",
                "risk_level": "MEDIUM",
                "amount": amount,
                "entry_date": date.strftime("%Y-%m-%d")
            })

    def generate_fraud_f05_related_party(self, count: int):
        """F05: Related party manipulation."""
        print(f"Generating {count} F05 (related party) entries...")

        for i in range(count):
            ic_vendor = random.choice(self.intercompany)
            # Unusual pricing - either too high or too low
            normal_amount = random.randint(10000000, 100000000)
            # Apply unusual markup/discount
            if random.random() < 0.5:
                amount = int(normal_amount * 1.5)  # 50% markup
                desc = "グループ間仕入（高値）"
            else:
                amount = int(normal_amount * 0.6)  # 40% discount
                desc = "グループ間売上（低値）"

            date = self.get_random_date()

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("1133", "D", amount),
                    ("4140", "C", amount)
                ],
                description=f"{desc} {self.vendors[ic_vendor]['vendor_name']}",
                prepared_by="U007",
                vendor_code=ic_vendor,
                dept_code="2510",
                source="INTERCOMPANY",
                fraud_flag="F05"
            )

            self.fraud_catalog.append({
                "pattern_id": "F05",
                "journal_id": journal_id,
                "description": "関連当事者操作",
                "risk_level": "HIGH",
                "amount": amount,
                "vendor_code": ic_vendor
            })

    def generate_fraud_f06_suspense_aged(self, count: int):
        """F06: Long-outstanding suspense accounts."""
        print(f"Generating {count} F06 (aged suspense) entries...")

        # Create old suspense entries at the start of fiscal year
        for i in range(count):
            date = datetime(2023, 4, random.randint(1, 15))
            amount = random.randint(1000000, 10000000)

            # Suspense debit with no clearing
            if random.random() < 0.5:
                account = "1195"  # Suspense payments
                desc = "仮払金（長期滞留）"
            else:
                account = "2190"  # Suspense receipts
                desc = "仮受金（長期滞留）"

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    (account, "D" if account == "1195" else "C", amount),
                    ("1112", "C" if account == "1195" else "D", amount)
                ],
                description=desc,
                prepared_by="U008",
                dept_code="1210",
                source="MANUAL",
                fraud_flag="F06"
            )

            self.fraud_catalog.append({
                "pattern_id": "F06",
                "journal_id": journal_id,
                "description": "仮勘定長期滞留",
                "risk_level": "MEDIUM",
                "amount": amount,
                "account_code": account
            })

    def generate_fraud_f07_expense_splitting(self, count: int):
        """F07: Expense splitting to avoid approval limits."""
        print(f"Generating {count} F07 (expense splitting) entries...")

        for i in range(count // 3):
            # Split a large expense into 3 smaller ones
            total_amount = random.randint(15000000, 30000000)
            split_amounts = [
                total_amount // 3 - random.randint(10000, 100000),
                total_amount // 3,
                total_amount // 3 + random.randint(10000, 100000)
            ]

            base_date = self.get_random_date()
            user = random.choice(self.staff)

            for j, split_amount in enumerate(split_amounts):
                # Each split just under 5M approval limit
                date = base_date + timedelta(days=j)

                journal_id = self.create_journal_entry(
                    effective_date=date,
                    entries=[
                        ("5233", "D", split_amount),  # Supplies
                        ("2140", "C", split_amount)
                    ],
                    description=f"消耗品費（分割{j+1}/3）",
                    prepared_by=user,
                    dept_code="1210",
                    source="EXPENSE",
                    fraud_flag="F07"
                )

                self.fraud_catalog.append({
                    "pattern_id": "F07",
                    "journal_id": journal_id,
                    "description": "経費分割",
                    "risk_level": "MEDIUM",
                    "amount": split_amount,
                    "split_sequence": f"{j+1}/3"
                })

    def generate_fraud_f08_weekend_high_value(self, count: int):
        """F08: Weekend/holiday high-value entries."""
        print(f"Generating {count} F08 (weekend high-value) entries...")

        for i in range(count):
            # Find a weekend date
            date = self.get_random_date()
            while date.weekday() < 5:  # Not weekend
                date = self.get_random_date()

            amount = random.randint(5000000, 50000000)
            user = random.choice(self.staff)

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("5243", "D", amount),
                    ("2140", "C", amount)
                ],
                description="外注費（休日入力）",
                prepared_by=user,
                entry_time=time(random.randint(10, 20), random.randint(0, 59)),
                dept_code="4410",
                source="MANUAL",
                fraud_flag="F08"
            )

            self.fraud_catalog.append({
                "pattern_id": "F08",
                "journal_id": journal_id,
                "description": "休日高額仕訳",
                "risk_level": "MEDIUM",
                "amount": amount,
                "day_of_week": date.strftime("%A")
            })

    def generate_fraud_f09_missing_description(self, count: int):
        """F09: Missing description on high-value entries."""
        print(f"Generating {count} F09 (missing description) entries...")

        for i in range(count):
            amount = random.randint(1000000, 20000000)
            date = self.get_random_date()
            user = random.choice(self.staff)
            account = random.choice(["5243", "5260", "5270", "5340"])

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    (account, "D", amount),
                    ("2140", "C", amount)
                ],
                description="",  # Empty description
                prepared_by=user,
                dept_code="1210",
                source="MANUAL",
                fraud_flag="F09"
            )

            self.fraud_catalog.append({
                "pattern_id": "F09",
                "journal_id": journal_id,
                "description": "摘要欠損",
                "risk_level": "LOW",
                "amount": amount,
                "account_code": account
            })

    def generate_fraud_f10_benford_violation(self, count: int):
        """F10: Benford's Law violation amounts."""
        print(f"Generating {count} F10 (Benford violation) entries...")

        # Generate amounts that violate Benford's Law
        # Normal first digit distribution: 1=30.1%, 2=17.6%, etc.
        # Create unnatural distribution with 5,6,7,8,9 overrepresented

        for i in range(count):
            # Force first digit to be 5-9 (unnatural)
            first_digit = random.choice([5, 6, 7, 8, 9])
            magnitude = random.randint(5, 8)  # 100K to 100M
            rest = random.randint(0, 10 ** (magnitude - 1) - 1)
            amount = first_digit * (10 ** (magnitude - 1)) + rest

            date = self.get_random_date()
            user = random.choice(self.staff)

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("5233", "D", amount),
                    ("2140", "C", amount)
                ],
                description="消耗品費",
                prepared_by=user,
                dept_code="1210",
                source="EXPENSE",
                fraud_flag="F10"
            )

            self.fraud_catalog.append({
                "pattern_id": "F10",
                "journal_id": journal_id,
                "description": "ベンフォード違反",
                "risk_level": "LOW",
                "amount": amount,
                "first_digit": first_digit
            })

    # ========================================
    # Anomaly Pattern Generators
    # ========================================

    def generate_anomaly_a01_round_amounts(self, count: int):
        """A01: Round number amounts."""
        print(f"Generating {count} A01 (round amounts) entries...")

        for i in range(count):
            amount = self.get_random_amount(round_number=True)
            date = self.get_random_date()
            user = random.choice(self.staff)

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("5233", "D", amount),
                    ("2140", "C", amount)
                ],
                description="消耗品費",
                prepared_by=user,
                dept_code="1210",
                source="EXPENSE",
                anomaly_flag="A01"
            )

            self.anomaly_catalog.append({
                "pattern_id": "A01",
                "journal_id": journal_id,
                "description": "金額の切り上げ",
                "risk_level": "LOW",
                "amount": amount
            })

    def generate_anomaly_a02_reversals(self, count: int):
        """A02: Frequent reversals."""
        print(f"Generating {count} A02 (reversals) entries...")

        for i in range(count // 2):
            amount = self.get_random_amount()
            date = self.get_random_date()
            user = random.choice(self.staff)

            # Original entry
            self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("5233", "D", amount),
                    ("2140", "C", amount)
                ],
                description="消耗品費",
                prepared_by=user,
                dept_code="1210",
                source="EXPENSE"
            )

            # Reversal entry (same day or next day)
            rev_date = date + timedelta(days=random.randint(0, 1))

            journal_id = self.create_journal_entry(
                effective_date=rev_date,
                entries=[
                    ("2140", "D", amount),
                    ("5233", "C", amount)
                ],
                description="消耗品費（取消）",
                prepared_by=user,
                dept_code="1210",
                source="REVERSAL",
                anomaly_flag="A02"
            )

            self.anomaly_catalog.append({
                "pattern_id": "A02",
                "journal_id": journal_id,
                "description": "逆仕訳多発",
                "risk_level": "LOW",
                "amount": amount
            })

    def generate_anomaly_a03_late_night(self, count: int):
        """A03: Late night entries."""
        print(f"Generating {count} A03 (late night) entries...")

        for i in range(count):
            amount = self.get_random_amount()
            date = self.get_random_date()
            user = random.choice(self.staff)

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("5230", "D", amount),
                    ("2140", "C", amount)
                ],
                description="出張旅費",
                prepared_by=user,
                entry_time=self.get_random_time(late_night=True),
                dept_code="2110",
                source="EXPENSE",
                anomaly_flag="A03"
            )

            self.anomaly_catalog.append({
                "pattern_id": "A03",
                "journal_id": journal_id,
                "description": "深夜入力",
                "risk_level": "LOW",
                "amount": amount
            })

    def generate_anomaly_a04_month_end(self, count: int):
        """A04: Month-end concentration."""
        print(f"Generating {count} A04 (month-end concentration) entries...")

        entries_per_month = count // 12

        for month in list(range(4, 13)) + list(range(1, 4)):
            if month >= 4:
                year = 2023
            else:
                year = 2024

            # Get last 3 days of month
            if month == 12:
                last_day = 31
            elif month in [4, 6, 9, 11]:
                last_day = 30
            elif month == 2:
                last_day = 29 if year % 4 == 0 else 28
            else:
                last_day = 31

            for i in range(entries_per_month):
                day = random.randint(last_day - 2, last_day)
                date = datetime(year, month, day)
                amount = self.get_random_amount()
                user = random.choice(self.staff)

                journal_id = self.create_journal_entry(
                    effective_date=date,
                    entries=[
                        ("5270", "D", amount),
                        ("2140", "C", amount)
                    ],
                    description="月末経費計上",
                    prepared_by=user,
                    dept_code="1210",
                    source="EXPENSE",
                    anomaly_flag="A04"
                )

                self.anomaly_catalog.append({
                    "pattern_id": "A04",
                    "journal_id": journal_id,
                    "description": "月末集中",
                    "risk_level": "LOW",
                    "amount": amount,
                    "month_day": f"{month}/{day}"
                })

    def generate_anomaly_a05_revenue_ar_mismatch(self, count: int):
        """A05: Revenue and AR mismatch."""
        print(f"Generating {count} A05 (revenue-AR mismatch) entries...")

        for i in range(count):
            # Revenue up but AR down - suspicious
            revenue_amount = random.randint(50000000, 200000000)
            ar_decrease = random.randint(60000000, 250000000)
            date = self.get_random_date()
            customer = random.choice(self.customers[:5])

            # Revenue entry
            self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("1131", "D", revenue_amount),
                    ("4111", "C", revenue_amount)
                ],
                description=f"売上計上 {self.vendors[customer]['vendor_name']}",
                prepared_by="U033",
                vendor_code=customer,
                dept_code="2110",
                source="SALES"
            )

            # AR write-off (larger than revenue)
            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("5251", "D", ar_decrease),
                    ("1131", "C", ar_decrease)
                ],
                description="売掛金償却（不審）",
                prepared_by="U033",
                vendor_code=customer,
                dept_code="2110",
                source="ADJUSTMENT",
                anomaly_flag="A05"
            )

            self.anomaly_catalog.append({
                "pattern_id": "A05",
                "journal_id": journal_id,
                "description": "売上債権逆相関",
                "risk_level": "MEDIUM",
                "revenue_amount": revenue_amount,
                "ar_decrease": ar_decrease
            })

    def generate_anomaly_a06_user_dominance(self, count: int):
        """A06: Single user dominance."""
        print(f"Generating {count} A06 (user dominance) entries...")

        suspicious_users = ["U900", "U901"]

        for i in range(count):
            user = random.choice(suspicious_users)
            amount = self.get_random_amount(min_val=5000000)
            date = self.get_random_date()

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    ("5260", "D", amount),
                    ("2140", "C", amount)
                ],
                description="接待交際費",
                prepared_by=user,
                dept_code="2110",
                source="EXPENSE",
                anomaly_flag="A06"
            )

            self.anomaly_catalog.append({
                "pattern_id": "A06",
                "journal_id": journal_id,
                "description": "特定担当者偏り",
                "risk_level": "MEDIUM",
                "amount": amount,
                "user_id": user
            })

    def generate_anomaly_a09_fx(self, count: int):
        """A09: FX gain/loss anomaly."""
        print(f"Generating {count} A09 (FX anomaly) entries...")

        for i in range(count):
            amount = random.randint(10000000, 100000000)
            date = self.get_random_date()

            # Unusual FX gain or loss
            if random.random() < 0.5:
                account = "4330"  # FX Gain
                desc = "為替差益（異常）"
            else:
                account = "5320"  # FX Loss
                desc = "為替差損（異常）"

            journal_id = self.create_journal_entry(
                effective_date=date,
                entries=[
                    (account, "D" if account == "5320" else "C", amount),
                    ("1115", "C" if account == "5320" else "D", amount)
                ],
                description=desc,
                prepared_by="U012",
                dept_code="1220",
                source="FX_ADJUSTMENT",
                anomaly_flag="A09"
            )

            self.anomaly_catalog.append({
                "pattern_id": "A09",
                "journal_id": journal_id,
                "description": "為替差損益異常",
                "risk_level": "MEDIUM",
                "amount": amount,
                "fx_type": "gain" if account == "4330" else "loss"
            })

    def generate_all(self):
        """Generate all journal entries."""
        target_count = self.config["scale"]["journal_count"]

        # Calculate counts for each type
        # Based on spec: sales 180K, purchase 120K, expense 85K, payroll 24K,
        # fixed asset 8K, financial 15K, adjustments 18K
        sales_count = int(target_count * 0.40)
        purchase_count = int(target_count * 0.27)
        expense_count = int(target_count * 0.19)
        payroll_count = 288  # 24 months * 12
        depreciation_count = 720  # 60 entries * 12 months

        # Generate normal entries
        print("=" * 50)
        print("Generating normal business entries...")
        print("=" * 50)

        self.generate_sales_entries(sales_count)
        self.generate_purchase_entries(purchase_count)
        self.generate_expense_entries(expense_count)
        self.generate_payroll_entries(payroll_count)
        self.generate_depreciation_entries(depreciation_count)

        # Generate fraud patterns
        print("\n" + "=" * 50)
        print("Embedding fraud patterns...")
        print("=" * 50)

        fraud_config = self.config.get("fraud_patterns", {})
        if fraud_config.get("enabled", True):
            patterns = fraud_config.get("patterns", {})
            self.generate_fraud_f01_self_approval(patterns.get("F01_self_approval", {}).get("count", 150))
            self.generate_fraud_f02_fictitious_sales(patterns.get("F02_fictitious_sales", {}).get("count", 30))
            self.generate_fraud_f03_circular_trading(patterns.get("F03_circular_trading", {}).get("count", 45))
            self.generate_fraud_f04_period_end_sales(patterns.get("F04_period_end_sales", {}).get("count", 80))
            self.generate_fraud_f05_related_party(patterns.get("F05_related_party", {}).get("count", 25))
            self.generate_fraud_f06_suspense_aged(patterns.get("F06_suspense_aged", {}).get("count", 60))
            self.generate_fraud_f07_expense_splitting(patterns.get("F07_expense_splitting", {}).get("count", 120))
            self.generate_fraud_f08_weekend_high_value(patterns.get("F08_weekend_high_value", {}).get("count", 40))
            self.generate_fraud_f09_missing_description(patterns.get("F09_missing_description", {}).get("count", 200))
            self.generate_fraud_f10_benford_violation(patterns.get("F10_benford_violation", {}).get("count", 350))

        # Generate anomaly patterns
        print("\n" + "=" * 50)
        print("Embedding anomaly patterns...")
        print("=" * 50)

        anomaly_config = self.config.get("anomaly_patterns", {})
        if anomaly_config.get("enabled", True):
            patterns = anomaly_config.get("patterns", {})
            self.generate_anomaly_a01_round_amounts(patterns.get("A01_round_amounts", {}).get("count", 500))
            self.generate_anomaly_a02_reversals(patterns.get("A02_frequent_reversals", {}).get("count", 180))
            self.generate_anomaly_a03_late_night(patterns.get("A03_late_night_entry", {}).get("count", 75))
            self.generate_anomaly_a04_month_end(patterns.get("A04_month_end_concentration", {}).get("count", 2500))
            self.generate_anomaly_a05_revenue_ar_mismatch(patterns.get("A05_revenue_ar_mismatch", {}).get("count", 40))
            self.generate_anomaly_a06_user_dominance(patterns.get("A06_single_user_dominance", {}).get("count", 300))
            self.generate_anomaly_a09_fx(patterns.get("A09_fx_anomaly", {}).get("count", 45))

        print(f"\nTotal journals generated: {len(self.journals)}")
        print(f"Fraud patterns embedded: {len(self.fraud_catalog)}")
        print(f"Anomaly patterns embedded: {len(self.anomaly_catalog)}")

    def export_csv(self):
        """Export journals to CSV."""
        output_file = DATA_DIR / "10_journal_entries.csv"

        fieldnames = [
            "gl_detail_id", "business_unit_code", "fiscal_year", "accounting_period",
            "journal_id", "journal_id_line_number", "effective_date", "entry_date",
            "entry_time", "gl_account_number", "amount", "amount_currency",
            "functional_amount", "debit_credit_indicator", "je_line_description",
            "source", "vendor_code", "dept_code", "prepared_by", "approved_by",
            "approved_date", "last_modified_by", "last_modified_date",
            "fraud_flag", "anomaly_flag"
        ]

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.journals)

        print(f"Exported journals to: {output_file}")

    def export_fraud_catalog(self):
        """Export fraud pattern catalog."""
        output_file = DATA_DIR / "90_fraud_catalog.csv"

        if not self.fraud_catalog:
            print("No fraud patterns to export.")
            return

        # Gather all unique field names across all records
        all_fields = set()
        for record in self.fraud_catalog:
            all_fields.update(record.keys())
        fieldnames = sorted(list(all_fields))

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.fraud_catalog)

        print(f"Exported fraud catalog to: {output_file}")

    def export_anomaly_catalog(self):
        """Export anomaly pattern catalog."""
        output_file = DATA_DIR / "91_anomaly_catalog.csv"

        if not self.anomaly_catalog:
            print("No anomaly patterns to export.")
            return

        # Gather all unique field names across all records
        all_fields = set()
        for record in self.anomaly_catalog:
            all_fields.update(record.keys())
        fieldnames = sorted(list(all_fields))

        with open(output_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.anomaly_catalog)

        print(f"Exported anomaly catalog to: {output_file}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("JAIA Sample Data Generator")
    print("グローバル塗料株式会社 - 仕訳データ生成")
    print("=" * 60)

    # Load configuration
    print("\nLoading configuration...")
    config = load_config()

    # Load master data
    print("Loading master data...")
    accounts, departments, vendors, users = load_master_data()
    print(f"  Accounts: {len(accounts)}")
    print(f"  Departments: {len(departments)}")
    print(f"  Vendors: {len(vendors)}")
    print(f"  Users: {len(users)}")

    # Create generator
    generator = JournalGenerator(config, accounts, departments, vendors, users)

    # Generate all data
    generator.generate_all()

    # Export
    print("\n" + "=" * 50)
    print("Exporting data...")
    print("=" * 50)

    generator.export_csv()
    generator.export_fraud_catalog()
    generator.export_anomaly_catalog()

    print("\n" + "=" * 60)
    print("Generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
