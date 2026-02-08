"""Database schema definitions for DuckDB and SQLite.

This module contains all SQL schema definitions used by JAIA.
Schemas follow AICPA Audit Data Standards where applicable.
"""

# =============================================================================
# DuckDB Schema - Main OLAP Tables
# =============================================================================

DUCKDB_SCHEMA = """
-- =========================================
-- Core Tables (AICPA Compliant)
-- =========================================

-- Journal Entries (GL_Detail)
CREATE TABLE IF NOT EXISTS journal_entries (
    gl_detail_id VARCHAR PRIMARY KEY,
    business_unit_code VARCHAR(20) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    journal_id VARCHAR(50) NOT NULL,
    journal_id_line_number INTEGER NOT NULL,
    effective_date DATE NOT NULL,
    entry_date DATE NOT NULL,
    entry_time TIME,
    gl_account_number VARCHAR(20) NOT NULL,
    amount DECIMAL(18, 2) NOT NULL,
    amount_currency VARCHAR(3) DEFAULT 'JPY',
    functional_amount DECIMAL(18, 2),
    debit_credit_indicator VARCHAR(1) NOT NULL CHECK (debit_credit_indicator IN ('D', 'C')),
    je_line_description VARCHAR(500),
    source VARCHAR(50),
    vendor_code VARCHAR(50),
    dept_code VARCHAR(50),
    prepared_by VARCHAR(50),
    approved_by VARCHAR(50),
    approved_date DATE,
    last_modified_by VARCHAR(50),
    last_modified_date TIMESTAMP,
    -- Analysis columns
    risk_score DECIMAL(5, 2),
    anomaly_flags VARCHAR(100),
    rule_violations VARCHAR(200)
);

-- Chart of Accounts
CREATE TABLE IF NOT EXISTS chart_of_accounts (
    account_code VARCHAR(20) PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL,
    account_name_en VARCHAR(100),
    account_category VARCHAR(2) NOT NULL CHECK (account_category IN ('BS', 'PL')),
    account_type VARCHAR(10) NOT NULL,
    normal_balance VARCHAR(6) NOT NULL CHECK (normal_balance IN ('debit', 'credit')),
    level INTEGER NOT NULL,
    parent_code VARCHAR(20),
    is_posting BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Trial Balance
CREATE TABLE IF NOT EXISTS trial_balance (
    id INTEGER PRIMARY KEY,
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    gl_account_number VARCHAR(20) NOT NULL,
    beginning_balance DECIMAL(18, 2) DEFAULT 0,
    period_debit DECIMAL(18, 2) DEFAULT 0,
    period_credit DECIMAL(18, 2) DEFAULT 0,
    ending_balance DECIMAL(18, 2) DEFAULT 0,
    UNIQUE(fiscal_year, accounting_period, gl_account_number)
);

-- Department Master
CREATE TABLE IF NOT EXISTS departments (
    dept_code VARCHAR(20) PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL,
    dept_name_en VARCHAR(100),
    segment VARCHAR(20),
    parent_dept VARCHAR(20),
    level INTEGER DEFAULT 1,
    cost_center BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Vendor Master
CREATE TABLE IF NOT EXISTS vendors (
    vendor_code VARCHAR(20) PRIMARY KEY,
    vendor_name VARCHAR(200) NOT NULL,
    vendor_name_en VARCHAR(200),
    vendor_type VARCHAR(20) NOT NULL,
    country VARCHAR(2),
    segment VARCHAR(20),
    is_related_party BOOLEAN DEFAULT FALSE,
    credit_limit BIGINT,
    payment_terms INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    risk_flag VARCHAR(50)
);

-- User Master
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(20) PRIMARY KEY,
    user_name VARCHAR(100) NOT NULL,
    user_name_en VARCHAR(100),
    dept_code VARCHAR(20),
    position VARCHAR(50),
    approval_limit BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    can_approve BOOLEAN DEFAULT FALSE,
    role VARCHAR(20)
);

-- =========================================
-- Aggregation Tables for Dashboard
-- =========================================

-- Period x Account Aggregation
CREATE TABLE IF NOT EXISTS agg_by_period_account (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    gl_account_number VARCHAR(20) NOT NULL,
    entry_count INTEGER DEFAULT 0,
    journal_count INTEGER DEFAULT 0,
    debit_total DECIMAL(18, 2) DEFAULT 0,
    credit_total DECIMAL(18, 2) DEFAULT 0,
    net_amount DECIMAL(18, 2) DEFAULT 0,
    avg_amount DECIMAL(18, 2) DEFAULT 0,
    max_amount DECIMAL(18, 2) DEFAULT 0,
    min_amount DECIMAL(18, 2) DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (fiscal_year, accounting_period, gl_account_number)
);

-- Daily Aggregation
CREATE TABLE IF NOT EXISTS agg_by_date (
    effective_date DATE PRIMARY KEY,
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    is_weekend BOOLEAN DEFAULT FALSE,
    entry_count INTEGER DEFAULT 0,
    journal_count INTEGER DEFAULT 0,
    debit_total DECIMAL(18, 2) DEFAULT 0,
    credit_total DECIMAL(18, 2) DEFAULT 0,
    unique_accounts INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0
);

-- Monthly Trend (Month over Month)
CREATE TABLE IF NOT EXISTS agg_trend_mom (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    gl_account_number VARCHAR(20) NOT NULL,
    current_amount DECIMAL(18, 2) DEFAULT 0,
    previous_amount DECIMAL(18, 2) DEFAULT 0,
    change_amount DECIMAL(18, 2) DEFAULT 0,
    change_percent DECIMAL(10, 4),
    is_significant BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (fiscal_year, accounting_period, gl_account_number)
);

-- Year over Year Trend
CREATE TABLE IF NOT EXISTS agg_trend_yoy (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    gl_account_number VARCHAR(20) NOT NULL,
    current_amount DECIMAL(18, 2) DEFAULT 0,
    prior_year_amount DECIMAL(18, 2) DEFAULT 0,
    change_amount DECIMAL(18, 2) DEFAULT 0,
    change_percent DECIMAL(10, 4),
    is_significant BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (fiscal_year, accounting_period, gl_account_number)
);

-- Benford Analysis
CREATE TABLE IF NOT EXISTS agg_benford (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER,
    digit_position INTEGER NOT NULL,
    digit VARCHAR(1) NOT NULL,
    observed_count INTEGER DEFAULT 0,
    observed_frequency DECIMAL(10, 6) DEFAULT 0,
    expected_frequency DECIMAL(10, 6) DEFAULT 0,
    deviation DECIMAL(10, 6) DEFAULT 0,
    PRIMARY KEY (fiscal_year, COALESCE(accounting_period, 0), digit_position, digit)
);

-- User Pattern Aggregation
CREATE TABLE IF NOT EXISTS agg_by_user (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    user_id VARCHAR(20) NOT NULL,
    role VARCHAR(10) NOT NULL,  -- 'preparer' or 'approver'
    entry_count INTEGER DEFAULT 0,
    journal_count INTEGER DEFAULT 0,
    total_amount DECIMAL(18, 2) DEFAULT 0,
    avg_amount DECIMAL(18, 2) DEFAULT 0,
    max_amount DECIMAL(18, 2) DEFAULT 0,
    unique_accounts INTEGER DEFAULT 0,
    weekend_count INTEGER DEFAULT 0,
    late_night_count INTEGER DEFAULT 0,
    self_approved_count INTEGER DEFAULT 0,
    PRIMARY KEY (fiscal_year, accounting_period, user_id, role)
);

-- Time Distribution (Hour of day)
CREATE TABLE IF NOT EXISTS agg_by_hour (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    entry_hour INTEGER NOT NULL,
    entry_count INTEGER DEFAULT 0,
    total_amount DECIMAL(18, 2) DEFAULT 0,
    avg_amount DECIMAL(18, 2) DEFAULT 0,
    PRIMARY KEY (fiscal_year, accounting_period, entry_hour)
);

-- Risk Aggregation
CREATE TABLE IF NOT EXISTS agg_risk_summary (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    entry_count INTEGER DEFAULT 0,
    journal_count INTEGER DEFAULT 0,
    total_amount DECIMAL(18, 2) DEFAULT 0,
    PRIMARY KEY (fiscal_year, accounting_period, risk_level)
);

-- Rule Violation Summary
CREATE TABLE IF NOT EXISTS agg_rule_violations (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    rule_id VARCHAR(20) NOT NULL,
    violation_count INTEGER DEFAULT 0,
    affected_amount DECIMAL(18, 2) DEFAULT 0,
    PRIMARY KEY (fiscal_year, accounting_period, rule_id)
);

-- Vendor Aggregation
CREATE TABLE IF NOT EXISTS agg_by_vendor (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    vendor_code VARCHAR(20) NOT NULL,
    vendor_type VARCHAR(20),
    entry_count INTEGER DEFAULT 0,
    debit_total DECIMAL(18, 2) DEFAULT 0,
    credit_total DECIMAL(18, 2) DEFAULT 0,
    net_amount DECIMAL(18, 2) DEFAULT 0,
    is_new_vendor BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (fiscal_year, accounting_period, vendor_code)
);

-- Account Flow (for Sankey diagrams)
CREATE TABLE IF NOT EXISTS agg_account_flow (
    fiscal_year INTEGER NOT NULL,
    accounting_period INTEGER NOT NULL,
    source_account VARCHAR(20) NOT NULL,
    target_account VARCHAR(20) NOT NULL,
    flow_amount DECIMAL(18, 2) DEFAULT 0,
    transaction_count INTEGER DEFAULT 0,
    PRIMARY KEY (fiscal_year, accounting_period, source_account, target_account)
);

-- =========================================
-- Agent Audit Findings (Persistence)
-- =========================================

CREATE TABLE IF NOT EXISTS audit_findings (
    finding_id VARCHAR PRIMARY KEY,
    workflow_id VARCHAR NOT NULL,
    agent_type VARCHAR(20) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    finding_title VARCHAR(500) NOT NULL,
    finding_description TEXT,
    severity VARCHAR(10) DEFAULT 'MEDIUM',
    category VARCHAR(50),
    affected_amount DECIMAL(18, 2) DEFAULT 0,
    affected_count INTEGER DEFAULT 0,
    evidence TEXT,
    recommendation TEXT,
    status VARCHAR(20) DEFAULT 'open',
    reviewed_by VARCHAR(50),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_af_workflow ON audit_findings(workflow_id);
CREATE INDEX IF NOT EXISTS idx_af_fiscal_year ON audit_findings(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_af_severity ON audit_findings(severity);

-- =========================================
-- Indexes
-- =========================================

CREATE INDEX IF NOT EXISTS idx_je_effective_date ON journal_entries(effective_date);
CREATE INDEX IF NOT EXISTS idx_je_entry_date ON journal_entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_je_account ON journal_entries(gl_account_number);
CREATE INDEX IF NOT EXISTS idx_je_journal_id ON journal_entries(journal_id);
CREATE INDEX IF NOT EXISTS idx_je_period ON journal_entries(fiscal_year, accounting_period);
CREATE INDEX IF NOT EXISTS idx_je_prepared_by ON journal_entries(prepared_by);
CREATE INDEX IF NOT EXISTS idx_je_approved_by ON journal_entries(approved_by);
CREATE INDEX IF NOT EXISTS idx_je_vendor ON journal_entries(vendor_code);
CREATE INDEX IF NOT EXISTS idx_je_dept ON journal_entries(dept_code);
CREATE INDEX IF NOT EXISTS idx_je_risk ON journal_entries(risk_score);
CREATE INDEX IF NOT EXISTS idx_je_source ON journal_entries(source);
"""

# =============================================================================
# SQLite Schema - Metadata and Application State
# =============================================================================

SQLITE_SCHEMA = """
-- =========================================
-- Application Settings
-- =========================================

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    data_type TEXT DEFAULT 'string',
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- Audit Rules Configuration
-- =========================================

CREATE TABLE IF NOT EXISTS audit_rules (
    rule_id TEXT PRIMARY KEY,
    rule_name TEXT NOT NULL,
    rule_name_en TEXT,
    category TEXT NOT NULL,
    description TEXT,
    description_en TEXT,
    sql_condition TEXT,
    python_function TEXT,
    severity TEXT DEFAULT 'MEDIUM' CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    is_enabled BOOLEAN DEFAULT TRUE,
    parameters TEXT,  -- JSON
    thresholds TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- Analysis Sessions
-- =========================================

CREATE TABLE IF NOT EXISTS analysis_sessions (
    session_id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
    fiscal_year INTEGER,
    period_from INTEGER,
    period_to INTEGER,
    filters TEXT,  -- JSON
    total_entries_analyzed INTEGER DEFAULT 0,
    total_rules_checked INTEGER DEFAULT 0,
    total_violations_found INTEGER DEFAULT 0,
    total_insights INTEGER DEFAULT 0,
    summary TEXT,
    error_message TEXT
);

-- =========================================
-- Insights
-- =========================================

CREATE TABLE IF NOT EXISTS insights (
    insight_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'INFO' CHECK (severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    evidence TEXT,  -- JSON
    affected_journals TEXT,  -- JSON array
    affected_count INTEGER DEFAULT 0,
    affected_amount REAL DEFAULT 0,
    recommendation TEXT,
    is_acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_insights_session ON insights(session_id);
CREATE INDEX IF NOT EXISTS idx_insights_category ON insights(category);
CREATE INDEX IF NOT EXISTS idx_insights_severity ON insights(severity);

-- =========================================
-- Journal Entry Notes
-- =========================================

CREATE TABLE IF NOT EXISTS je_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id TEXT NOT NULL,
    note_text TEXT NOT NULL,
    note_type TEXT DEFAULT 'general',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notes_journal ON je_notes(journal_id);

-- =========================================
-- Journal Entry Tags
-- =========================================

CREATE TABLE IF NOT EXISTS je_tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    tag_color TEXT DEFAULT '#6B7280',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(journal_id, tag_name)
);

CREATE INDEX IF NOT EXISTS idx_tags_journal ON je_tags(journal_id);
CREATE INDEX IF NOT EXISTS idx_tags_name ON je_tags(tag_name);

-- =========================================
-- Import History
-- =========================================

CREATE TABLE IF NOT EXISTS import_history (
    import_id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER,
    row_count INTEGER,
    imported_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'validating', 'importing', 'completed', 'failed')),
    column_mapping TEXT,  -- JSON
    validation_errors TEXT,  -- JSON
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- =========================================
-- Filter Presets
-- =========================================

CREATE TABLE IF NOT EXISTS filter_presets (
    preset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_name TEXT NOT NULL UNIQUE,
    description TEXT,
    filters TEXT NOT NULL,  -- JSON
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- Report Templates
-- =========================================

CREATE TABLE IF NOT EXISTS report_templates (
    template_id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name TEXT NOT NULL UNIQUE,
    template_type TEXT NOT NULL CHECK (template_type IN ('PPT', 'PDF')),
    description TEXT,
    config TEXT NOT NULL,  -- JSON
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- Generated Reports
-- =========================================

CREATE TABLE IF NOT EXISTS generated_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    template_id INTEGER,
    report_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    fiscal_year INTEGER,
    period_from INTEGER,
    period_to INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(session_id),
    FOREIGN KEY (template_id) REFERENCES report_templates(template_id)
);

-- =========================================
-- Schema Version (for migrations)
-- =========================================

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial version
INSERT OR IGNORE INTO schema_version (version, description) VALUES (1, 'Initial schema');
"""

# Default audit rules to be inserted
DEFAULT_AUDIT_RULES = [
    # Amount Rules (AMOUNT_001 - AMOUNT_015)
    {
        "rule_id": "AMOUNT_001",
        "rule_name": "金額ゼロ仕訳",
        "category": "AMOUNT",
        "severity": "LOW",
        "description": "金額が0円の仕訳を検出",
    },
    {
        "rule_id": "AMOUNT_002",
        "rule_name": "丸め金額（端数なし）",
        "category": "AMOUNT",
        "severity": "LOW",
        "description": "金額が切りの良い数字（10万円単位等）の仕訳を検出",
    },
    {
        "rule_id": "AMOUNT_003",
        "rule_name": "承認基準ギリギリ",
        "category": "AMOUNT",
        "severity": "MEDIUM",
        "description": "承認基準額の90-100%の金額の仕訳を検出",
    },
    {
        "rule_id": "AMOUNT_004",
        "rule_name": "統計的外れ値",
        "category": "AMOUNT",
        "severity": "MEDIUM",
        "description": "同一科目の平均から3σ以上乖離した金額を検出",
    },
    {
        "rule_id": "AMOUNT_005",
        "rule_name": "高額仕訳",
        "category": "AMOUNT",
        "severity": "HIGH",
        "description": "設定閾値以上の高額仕訳を検出",
    },
    # Time Rules (TIME_001 - TIME_010)
    {
        "rule_id": "TIME_001",
        "rule_name": "月末集中",
        "category": "TIME",
        "severity": "MEDIUM",
        "description": "月末3日間に仕訳が30%以上集中",
    },
    {
        "rule_id": "TIME_002",
        "rule_name": "期末集中",
        "category": "TIME",
        "severity": "HIGH",
        "description": "期末最終週に仕訳が異常に集中",
    },
    {
        "rule_id": "TIME_003",
        "rule_name": "休日入力",
        "category": "TIME",
        "severity": "LOW",
        "description": "土日祝日に入力された仕訳を検出",
    },
    {
        "rule_id": "TIME_004",
        "rule_name": "深夜入力",
        "category": "TIME",
        "severity": "MEDIUM",
        "description": "22時以降に入力された仕訳を検出",
    },
    {
        "rule_id": "TIME_005",
        "rule_name": "バックデート",
        "category": "TIME",
        "severity": "HIGH",
        "description": "入力日が発効日より大幅に後の仕訳を検出",
    },
    # Approval Rules (APPROVAL_001 - APPROVAL_008)
    {
        "rule_id": "APPROVAL_001",
        "rule_name": "自己承認",
        "category": "APPROVAL",
        "severity": "HIGH",
        "description": "起票者と承認者が同一人物の仕訳を検出",
    },
    {
        "rule_id": "APPROVAL_002",
        "rule_name": "未承認高額",
        "category": "APPROVAL",
        "severity": "HIGH",
        "description": "高額にもかかわらず承認者が空欄の仕訳を検出",
    },
    {
        "rule_id": "APPROVAL_003",
        "rule_name": "承認限度超過",
        "category": "APPROVAL",
        "severity": "CRITICAL",
        "description": "承認者の承認限度額を超えた仕訳を検出",
    },
    # Account Rules (ACCOUNT_001 - ACCOUNT_020)
    {
        "rule_id": "ACCOUNT_001",
        "rule_name": "異常な科目組合せ",
        "category": "ACCOUNT",
        "severity": "MEDIUM",
        "description": "通常使用しない借方/貸方の科目組合せを検出",
    },
    {
        "rule_id": "ACCOUNT_002",
        "rule_name": "仮勘定長期滞留",
        "category": "ACCOUNT",
        "severity": "MEDIUM",
        "description": "仮払金・仮受金が長期間未清算",
    },
    {
        "rule_id": "ACCOUNT_003",
        "rule_name": "関連当事者取引",
        "category": "ACCOUNT",
        "severity": "HIGH",
        "description": "関連当事者との取引を検出",
    },
    # Pattern Rules (PATTERN_001 - PATTERN_010)
    {
        "rule_id": "PATTERN_001",
        "rule_name": "ベンフォード違反",
        "category": "PATTERN",
        "severity": "MEDIUM",
        "description": "金額の第一桁分布がベンフォードの法則から逸脱",
    },
    {
        "rule_id": "PATTERN_002",
        "rule_name": "逆仕訳多発",
        "category": "PATTERN",
        "severity": "MEDIUM",
        "description": "同一取引の逆仕訳が頻繁に発生",
    },
    {
        "rule_id": "PATTERN_003",
        "rule_name": "循環取引パターン",
        "category": "PATTERN",
        "severity": "CRITICAL",
        "description": "A→B→C→Aのような循環取引パターンを検出",
    },
    # Description Rules (DESC_001 - DESC_012)
    {
        "rule_id": "DESC_001",
        "rule_name": "摘要欠損",
        "category": "DESC",
        "severity": "LOW",
        "description": "摘要が空欄または短すぎる仕訳を検出",
    },
    {
        "rule_id": "DESC_002",
        "rule_name": "定型外摘要",
        "category": "DESC",
        "severity": "LOW",
        "description": "通常の摘要パターンと異なる記述を検出",
    },
]
