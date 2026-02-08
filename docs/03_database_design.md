# JAIA データベース設計書

## 1. データベース構成概要

### 1.1 データベース分離方針

| データベース | 用途 | 技術 | ファイル |
|-------------|------|------|----------|
| メインDB | 仕訳・集計データ（OLAP） | DuckDB | `jaia.duckdb` |
| メタデータDB | 設定・ルール・セッション | SQLite | `metadata.sqlite` |
| キャッシュ | 集計結果の永続化 | Parquet | `cache/*.parquet` |

### 1.2 データベース選定理由

**DuckDB (メインDB)**
- OLAP特化の高速分析クエリ
- 1,000万件以上の仕訳データに対応
- Polarsとのシームレスな連携
- ファイルベースで配布が容易

**SQLite (メタデータDB)**
- 軽量・高信頼
- トランザクション対応
- 設定・セッション管理に最適

---

## 2. DuckDB スキーマ定義 (メインDB)

### 2.1 ER図

```
┌─────────────────────────────────────────────────────────────────┐
│                           MAIN DB (DuckDB)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │ fiscal_periods  │     │ chart_of_       │                   │
│  │ (会計期間)       │     │ accounts        │                   │
│  │                 │     │ (勘定科目)       │                   │
│  │ PK: period_id   │     │ PK: gl_account_ │                   │
│  │                 │     │     number      │                   │
│  └────────┬────────┘     └────────┬────────┘                   │
│           │                       │                             │
│           │ 1:N                   │ 1:N                         │
│           ▼                       ▼                             │
│  ┌─────────────────────────────────────────────────┐           │
│  │              journal_entries                     │           │
│  │              (仕訳明細 - AICPA準拠)              │           │
│  │                                                  │           │
│  │ PK: journal_id                                  │           │
│  │ FK: fiscal_year, accounting_period              │           │
│  │ FK: gl_account_number                           │           │
│  │ FK: entered_by, approved_by                     │           │
│  └─────────────────────────────────────────────────┘           │
│           │                       │                             │
│           │ 1:N                   │ 1:1                         │
│           ▼                       ▼                             │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │ journal_notes   │     │ risk_scores     │                   │
│  │ (メモ・タグ)     │     │ (リスク評価)    │                   │
│  │                 │     │                 │                   │
│  │ PK: note_id     │     │ PK: journal_id  │                   │
│  │ FK: journal_id  │     │                 │                   │
│  └─────────────────┘     └─────────────────┘                   │
│                                                                  │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │ trial_balance   │     │ users           │                   │
│  │ (試算表)         │     │ (ユーザー)      │                   │
│  │                 │     │                 │                   │
│  │ PK: (account,   │     │ PK: user_id     │                   │
│  │     period)     │     │                 │                   │
│  └─────────────────┘     └─────────────────┘                   │
│                                                                  │
│  ════════════════════ 集計テーブル ════════════════════          │
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ agg_by_period_     │  │ agg_by_date_       │                │
│  │ account            │  │ account            │                │
│  └────────────────────┘  └────────────────────┘                │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ agg_trend_mom      │  │ agg_trend_yoy      │                │
│  └────────────────────┘  └────────────────────┘                │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ agg_benford        │  │ agg_account_flow   │                │
│  └────────────────────┘  └────────────────────┘                │
│  ... (全17集計テーブル)                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 マスタテーブル

#### 2.2.1 fiscal_periods（会計期間）

```sql
CREATE TABLE fiscal_periods (
    period_id           VARCHAR(20) PRIMARY KEY,
    fiscal_year         VARCHAR(4) NOT NULL,
    period_type         VARCHAR(20) NOT NULL,  -- Annual, Quarterly, Monthly
    period_number       INTEGER NOT NULL,       -- 1-12 (Monthly), 1-4 (Quarterly), 13-14 (Adjustment)
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    is_adjustment       BOOLEAN DEFAULT FALSE,
    status              VARCHAR(20) DEFAULT 'Open',  -- Open, Closed, Locked
    prior_period_id     VARCHAR(20),
    same_period_prior_year_id VARCHAR(20),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_period_type CHECK (period_type IN ('Annual', 'Quarterly', 'Monthly')),
    CONSTRAINT chk_status CHECK (status IN ('Open', 'Closed', 'Locked')),
    CONSTRAINT chk_dates CHECK (start_date <= end_date)
);

CREATE INDEX idx_fiscal_periods_year ON fiscal_periods(fiscal_year);
```

#### 2.2.2 chart_of_accounts（勘定科目マスタ）

```sql
CREATE TABLE chart_of_accounts (
    gl_account_number   VARCHAR(100) PRIMARY KEY,
    gl_account_name     VARCHAR(200) NOT NULL,
    fs_caption          VARCHAR(200),           -- 財務諸表表示科目
    account_type        VARCHAR(20) NOT NULL,   -- Asset, Liability, Equity, Revenue, Expense
    account_subtype     VARCHAR(50),            -- Current, NonCurrent, Operating, etc.
    normal_balance      VARCHAR(10) NOT NULL,   -- Debit, Credit
    parent_account      VARCHAR(100),
    account_level       INTEGER DEFAULT 1,
    posting_indicator   CHAR(1) DEFAULT 'Y',    -- Y/N
    disclosure_category VARCHAR(50),
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_account_type CHECK (
        account_type IN ('Asset', 'Liability', 'Equity', 'Revenue', 'Expense')
    ),
    CONSTRAINT chk_normal_balance CHECK (normal_balance IN ('Debit', 'Credit'))
);

CREATE INDEX idx_coa_type ON chart_of_accounts(account_type);
CREATE INDEX idx_coa_fs_caption ON chart_of_accounts(fs_caption);
CREATE INDEX idx_coa_parent ON chart_of_accounts(parent_account);
```

#### 2.2.3 users（ユーザーマスタ）

```sql
CREATE TABLE users (
    user_id             VARCHAR(100) PRIMARY KEY,
    user_name           VARCHAR(200),
    department          VARCHAR(100),
    role                VARCHAR(50),
    email               VARCHAR(200),
    approval_limit      DECIMAL(18, 2),
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_dept ON users(department);
```

### 2.3 トランザクションテーブル

#### 2.3.1 journal_entries（仕訳明細 - AICPA準拠）

```sql
CREATE TABLE journal_entries (
    -- 主キー
    journal_id          VARCHAR(150) PRIMARY KEY,  -- JE_Number + '_' + JE_Line_Number

    -- AICPA Level 1 必須項目
    je_number           VARCHAR(100) NOT NULL,
    je_line_number      INTEGER NOT NULL,
    fiscal_year         VARCHAR(4) NOT NULL,
    accounting_period   INTEGER NOT NULL,
    effective_date      DATE NOT NULL,
    entry_date          DATE NOT NULL,
    gl_account_number   VARCHAR(100) NOT NULL,
    amount              DECIMAL(18, 2) NOT NULL,   -- 借方+, 貸方-
    functional_amount   DECIMAL(18, 2),
    je_line_description VARCHAR(1000),
    source              VARCHAR(25),
    entered_by          VARCHAR(100),

    -- AICPA Level 2 推奨項目
    je_header_description VARCHAR(1000),
    approved_by         VARCHAR(100),
    approved_date       DATE,
    last_modified_date  TIMESTAMP,
    last_modified_by    VARCHAR(100),
    business_unit       VARCHAR(50),
    segment01           VARCHAR(50),
    segment02           VARCHAR(50),
    segment03           VARCHAR(50),
    segment04           VARCHAR(50),
    segment05           VARCHAR(50),
    segment06           VARCHAR(50),
    segment07           VARCHAR(50),
    segment08           VARCHAR(50),
    segment09           VARCHAR(50),
    segment10           VARCHAR(50),
    document_number     VARCHAR(100),
    currency_code       CHAR(3),

    -- 計算項目
    debit_amount        DECIMAL(18, 2) GENERATED ALWAYS AS (
        CASE WHEN amount > 0 THEN amount ELSE 0 END
    ) STORED,
    credit_amount       DECIMAL(18, 2) GENERATED ALWAYS AS (
        CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END
    ) STORED,
    amount_abs          DECIMAL(18, 2) GENERATED ALWAYS AS (ABS(amount)) STORED,

    -- メタデータ
    import_batch_id     VARCHAR(36),
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 制約
    CONSTRAINT chk_period CHECK (accounting_period BETWEEN 1 AND 14),
    CONSTRAINT fk_account FOREIGN KEY (gl_account_number)
        REFERENCES chart_of_accounts(gl_account_number)
);

-- パフォーマンス用インデックス
CREATE INDEX idx_je_date ON journal_entries(effective_date);
CREATE INDEX idx_je_period ON journal_entries(fiscal_year, accounting_period);
CREATE INDEX idx_je_account ON journal_entries(gl_account_number);
CREATE INDEX idx_je_user ON journal_entries(entered_by);
CREATE INDEX idx_je_approver ON journal_entries(approved_by);
CREATE INDEX idx_je_source ON journal_entries(source);
CREATE INDEX idx_je_amount ON journal_entries(amount_abs);

-- 複合インデックス
CREATE INDEX idx_je_period_account ON journal_entries(fiscal_year, accounting_period, gl_account_number);
CREATE INDEX idx_je_date_account ON journal_entries(effective_date, gl_account_number);
```

#### 2.3.2 trial_balance（試算表）

```sql
CREATE TABLE trial_balance (
    gl_account_number   VARCHAR(100) NOT NULL,
    fiscal_year         VARCHAR(4) NOT NULL,
    accounting_period   INTEGER NOT NULL,
    opening_balance     DECIMAL(18, 2) NOT NULL DEFAULT 0,
    period_debit        DECIMAL(18, 2) NOT NULL DEFAULT 0,
    period_credit       DECIMAL(18, 2) NOT NULL DEFAULT 0,
    closing_balance     DECIMAL(18, 2) NOT NULL DEFAULT 0,
    budget_amount       DECIMAL(18, 2),
    import_batch_id     VARCHAR(36),
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (gl_account_number, fiscal_year, accounting_period),
    CONSTRAINT fk_tb_account FOREIGN KEY (gl_account_number)
        REFERENCES chart_of_accounts(gl_account_number)
);

CREATE INDEX idx_tb_period ON trial_balance(fiscal_year, accounting_period);
```

#### 2.3.3 risk_scores（リスクスコア）

```sql
CREATE TABLE risk_scores (
    journal_id              VARCHAR(150) PRIMARY KEY,

    -- ルールベーススコア
    rule_risk_score         INTEGER NOT NULL DEFAULT 0,
    rule_violations         JSON,  -- [{rule_id, score, details}]

    -- MLスコア
    anomaly_score_if        FLOAT,  -- Isolation Forest
    anomaly_score_lof       FLOAT,  -- Local Outlier Factor
    anomaly_score_svm       FLOAT,  -- One-Class SVM
    reconstruction_error    FLOAT,  -- Autoencoder
    benford_score           FLOAT,  -- Benford分析

    -- 統合スコア
    ml_risk_score           FLOAT,
    integrated_risk_score   FLOAT NOT NULL,
    risk_level              VARCHAR(10) NOT NULL,  -- Critical, High, Medium, Low

    -- 詳細情報
    top_risk_factors        JSON,  -- 上位リスク要因
    anomaly_flags           JSON,  -- 異常フラグリスト

    scored_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_risk_journal FOREIGN KEY (journal_id)
        REFERENCES journal_entries(journal_id),
    CONSTRAINT chk_risk_level CHECK (
        risk_level IN ('Critical', 'High', 'Medium', 'Low')
    )
);

CREATE INDEX idx_risk_level ON risk_scores(risk_level);
CREATE INDEX idx_risk_score ON risk_scores(integrated_risk_score DESC);
```

#### 2.3.4 journal_notes（仕訳メモ・タグ）

```sql
CREATE TABLE journal_notes (
    note_id             VARCHAR(36) PRIMARY KEY,
    journal_id          VARCHAR(150) NOT NULL,
    note_text           TEXT,
    note_type           VARCHAR(20) NOT NULL,  -- Question, Comment, Issue, Resolution
    created_by          VARCHAR(100),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_resolved         BOOLEAN DEFAULT FALSE,

    CONSTRAINT fk_note_journal FOREIGN KEY (journal_id)
        REFERENCES journal_entries(journal_id),
    CONSTRAINT chk_note_type CHECK (
        note_type IN ('Question', 'Comment', 'Issue', 'Resolution')
    )
);

CREATE TABLE journal_tags (
    journal_id          VARCHAR(150) NOT NULL,
    tag_id              VARCHAR(36) NOT NULL,
    tagged_by           VARCHAR(100),
    tagged_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (journal_id, tag_id),
    CONSTRAINT fk_jt_journal FOREIGN KEY (journal_id)
        REFERENCES journal_entries(journal_id)
);

CREATE INDEX idx_jn_journal ON journal_notes(journal_id);
CREATE INDEX idx_jn_type ON journal_notes(note_type);
CREATE INDEX idx_jt_tag ON journal_tags(tag_id);
```

### 2.4 集計テーブル

#### 2.4.1 期間×勘定科目集計

```sql
CREATE TABLE agg_by_period_account (
    fiscal_year         VARCHAR(4) NOT NULL,
    accounting_period   INTEGER NOT NULL,
    gl_account_number   VARCHAR(100) NOT NULL,

    -- 基本集計
    je_count            INTEGER NOT NULL,
    sum_debit           DECIMAL(18, 2) NOT NULL,
    sum_credit          DECIMAL(18, 2) NOT NULL,
    sum_amount          DECIMAL(18, 2) NOT NULL,
    avg_amount          DECIMAL(18, 2),
    std_amount          DECIMAL(18, 2),
    min_amount          DECIMAL(18, 2),
    max_amount          DECIMAL(18, 2),

    -- リスク集計
    risk_count_critical INTEGER DEFAULT 0,
    risk_count_high     INTEGER DEFAULT 0,
    risk_count_medium   INTEGER DEFAULT 0,
    risk_count_low      INTEGER DEFAULT 0,

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (fiscal_year, accounting_period, gl_account_number)
);

CREATE INDEX idx_agg_pa_period ON agg_by_period_account(fiscal_year, accounting_period);
CREATE INDEX idx_agg_pa_account ON agg_by_period_account(gl_account_number);
```

#### 2.4.2 期間×表示科目集計

```sql
CREATE TABLE agg_by_period_fs_caption (
    fiscal_year         VARCHAR(4) NOT NULL,
    accounting_period   INTEGER NOT NULL,
    fs_caption          VARCHAR(200) NOT NULL,

    je_count            INTEGER NOT NULL,
    sum_debit           DECIMAL(18, 2) NOT NULL,
    sum_credit          DECIMAL(18, 2) NOT NULL,
    sum_amount          DECIMAL(18, 2) NOT NULL,
    account_count       INTEGER NOT NULL,  -- 含まれる勘定科目数

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (fiscal_year, accounting_period, fs_caption)
);
```

#### 2.4.3 トレンド分析用集計

```sql
-- 前月比トレンド
CREATE TABLE agg_trend_mom (
    fiscal_year         VARCHAR(4) NOT NULL,
    accounting_period   INTEGER NOT NULL,
    gl_account_number   VARCHAR(100) NOT NULL,

    current_amount      DECIMAL(18, 2),
    prior_amount        DECIMAL(18, 2),
    variance_amount     DECIMAL(18, 2),
    variance_rate       DECIMAL(10, 4),  -- 増減率

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (fiscal_year, accounting_period, gl_account_number)
);

-- 前年同期比トレンド
CREATE TABLE agg_trend_yoy (
    fiscal_year         VARCHAR(4) NOT NULL,
    accounting_period   INTEGER NOT NULL,
    gl_account_number   VARCHAR(100) NOT NULL,

    current_amount      DECIMAL(18, 2),
    prior_year_amount   DECIMAL(18, 2),
    variance_amount     DECIMAL(18, 2),
    variance_rate       DECIMAL(10, 4),

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (fiscal_year, accounting_period, gl_account_number)
);
```

#### 2.4.4 ベンフォード分析用集計

```sql
CREATE TABLE agg_benford (
    gl_account_number   VARCHAR(100) NOT NULL,
    fiscal_year         VARCHAR(4) NOT NULL,

    -- 第1桁分布（1-9）
    digit1_count_1      INTEGER DEFAULT 0,
    digit1_count_2      INTEGER DEFAULT 0,
    digit1_count_3      INTEGER DEFAULT 0,
    digit1_count_4      INTEGER DEFAULT 0,
    digit1_count_5      INTEGER DEFAULT 0,
    digit1_count_6      INTEGER DEFAULT 0,
    digit1_count_7      INTEGER DEFAULT 0,
    digit1_count_8      INTEGER DEFAULT 0,
    digit1_count_9      INTEGER DEFAULT 0,

    -- 第2桁分布（0-9）
    digit2_count_0      INTEGER DEFAULT 0,
    digit2_count_1      INTEGER DEFAULT 0,
    digit2_count_2      INTEGER DEFAULT 0,
    digit2_count_3      INTEGER DEFAULT 0,
    digit2_count_4      INTEGER DEFAULT 0,
    digit2_count_5      INTEGER DEFAULT 0,
    digit2_count_6      INTEGER DEFAULT 0,
    digit2_count_7      INTEGER DEFAULT 0,
    digit2_count_8      INTEGER DEFAULT 0,
    digit2_count_9      INTEGER DEFAULT 0,

    total_count         INTEGER NOT NULL,
    chi_square_digit1   FLOAT,  -- χ²統計量
    chi_square_digit2   FLOAT,
    p_value_digit1      FLOAT,
    p_value_digit2      FLOAT,

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (gl_account_number, fiscal_year)
);
```

#### 2.4.5 資金フロー（サンキー用）

```sql
CREATE TABLE agg_account_flow (
    fiscal_year         VARCHAR(4) NOT NULL,
    accounting_period   INTEGER NOT NULL,
    debit_account       VARCHAR(100) NOT NULL,
    credit_account      VARCHAR(100) NOT NULL,

    flow_count          INTEGER NOT NULL,
    flow_amount         DECIMAL(18, 2) NOT NULL,

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (fiscal_year, accounting_period, debit_account, credit_account)
);

CREATE INDEX idx_agg_flow_debit ON agg_account_flow(debit_account);
CREATE INDEX idx_agg_flow_credit ON agg_account_flow(credit_account);
```

#### 2.4.6 時間分布集計

```sql
CREATE TABLE agg_time_distribution (
    fiscal_year         VARCHAR(4) NOT NULL,
    day_of_week         INTEGER NOT NULL,  -- 0=Monday, 6=Sunday
    hour_of_day         INTEGER NOT NULL,  -- 0-23

    je_count            INTEGER NOT NULL,
    sum_amount          DECIMAL(18, 2) NOT NULL,
    risk_count          INTEGER DEFAULT 0,

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (fiscal_year, day_of_week, hour_of_day)
);
```

#### 2.4.7 ユーザーパターン集計

```sql
CREATE TABLE agg_user_pattern (
    fiscal_year         VARCHAR(4) NOT NULL,
    entered_by          VARCHAR(100) NOT NULL,
    gl_account_number   VARCHAR(100) NOT NULL,

    je_count            INTEGER NOT NULL,
    sum_amount          DECIMAL(18, 2) NOT NULL,
    avg_amount          DECIMAL(18, 2),
    risk_count          INTEGER DEFAULT 0,

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (fiscal_year, entered_by, gl_account_number)
);

CREATE INDEX idx_agg_user ON agg_user_pattern(entered_by);
```

### 2.5 財務指標テーブル

```sql
CREATE TABLE financial_metrics (
    fiscal_year         VARCHAR(4) NOT NULL,
    accounting_period   INTEGER NOT NULL,

    -- 回転期間
    ar_turnover_days    DECIMAL(10, 2),  -- 売掛金回転期間
    ap_turnover_days    DECIMAL(10, 2),  -- 買掛金回転期間
    inv_turnover_days   DECIMAL(10, 2),  -- 棚卸資産回転期間
    ccc_days            DECIMAL(10, 2),  -- CCC

    -- 流動性
    current_ratio       DECIMAL(10, 4),  -- 流動比率
    quick_ratio         DECIMAL(10, 4),  -- 当座比率

    -- 収益性
    gross_margin        DECIMAL(10, 4),  -- 売上総利益率
    operating_margin    DECIMAL(10, 4),  -- 営業利益率

    -- 基礎データ
    sales               DECIMAL(18, 2),
    cogs                DECIMAL(18, 2),
    gross_profit        DECIMAL(18, 2),
    operating_income    DECIMAL(18, 2),
    ar_balance          DECIMAL(18, 2),
    ap_balance          DECIMAL(18, 2),
    inventory_balance   DECIMAL(18, 2),
    current_assets      DECIMAL(18, 2),
    current_liabilities DECIMAL(18, 2),

    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (fiscal_year, accounting_period)
);
```

---

## 3. SQLite スキーマ定義 (メタデータDB)

### 3.1 設定テーブル

```sql
-- アプリケーション設定
CREATE TABLE app_settings (
    setting_key         TEXT PRIMARY KEY,
    setting_value       TEXT NOT NULL,
    setting_type        TEXT NOT NULL,  -- string, number, boolean, json
    description         TEXT,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LLMプロバイダー設定
CREATE TABLE llm_config (
    config_id           TEXT PRIMARY KEY DEFAULT 'default',
    provider            TEXT NOT NULL,  -- aws_bedrock, vertex_ai, azure_openai, anthropic_direct
    model_id            TEXT NOT NULL,
    region              TEXT,
    endpoint            TEXT,
    max_tokens          INTEGER DEFAULT 4096,
    temperature         REAL DEFAULT 0.3,
    timeout_seconds     INTEGER DEFAULT 60,
    retry_count         INTEGER DEFAULT 3,
    fallback_enabled    INTEGER DEFAULT 0,
    fallback_provider   TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 ルール定義テーブル

```sql
CREATE TABLE audit_rules (
    rule_id             TEXT PRIMARY KEY,
    category            TEXT NOT NULL,  -- 金額, 時間, 勘定, 承認, 摘要, パターン, 趨勢
    rule_name           TEXT NOT NULL,
    description         TEXT,
    severity            TEXT NOT NULL,  -- Critical, High, Medium, Low
    base_score          INTEGER NOT NULL,
    is_enabled          INTEGER DEFAULT 1,
    parameters          TEXT,  -- JSON形式
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ルール閾値設定
CREATE TABLE rule_thresholds (
    threshold_id        TEXT PRIMARY KEY,
    rule_id             TEXT NOT NULL,
    threshold_name      TEXT NOT NULL,
    threshold_value     REAL NOT NULL,
    description         TEXT,
    FOREIGN KEY (rule_id) REFERENCES audit_rules(rule_id)
);
```

### 3.3 タグマスタ

```sql
CREATE TABLE tags (
    tag_id              TEXT PRIMARY KEY,
    tag_name            TEXT NOT NULL UNIQUE,
    tag_color           TEXT NOT NULL,  -- #RRGGBB
    tag_category        TEXT NOT NULL,  -- Review, Risk, Status, Custom
    description         TEXT,
    is_system           INTEGER DEFAULT 0,  -- システム定義タグ
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- デフォルトタグ挿入
INSERT INTO tags (tag_id, tag_name, tag_color, tag_category, is_system) VALUES
    ('tag_confirm', '要確認', '#FFC107', 'Review', 1),
    ('tag_investigate', '要調査', '#FF5722', 'Review', 1),
    ('tag_anomaly', '異常', '#F44336', 'Risk', 1),
    ('tag_verified', '確認済', '#4CAF50', 'Status', 1),
    ('tag_ok', '問題なし', '#2196F3', 'Status', 1),
    ('tag_client', 'クライアント確認', '#9C27B0', 'Review', 1);
```

### 3.4 分析セッションテーブル

```sql
CREATE TABLE analysis_sessions (
    session_id          TEXT PRIMARY KEY,
    started_at          TIMESTAMP NOT NULL,
    completed_at        TIMESTAMP,
    status              TEXT NOT NULL,  -- running, completed, failed, cancelled
    current_phase       TEXT,

    -- 分析計画・結果（JSON）
    analysis_plan       TEXT,
    findings            TEXT,
    visited_views       TEXT,
    applied_filters     TEXT,
    verification_results TEXT,
    false_positives     TEXT,
    human_feedback      TEXT,

    -- 統計
    total_charts_viewed INTEGER DEFAULT 0,
    total_filters_applied INTEGER DEFAULT 0,
    total_findings      INTEGER DEFAULT 0,
    total_journals_tagged INTEGER DEFAULT 0,

    -- レポート
    report_ppt_path     TEXT,
    report_pdf_path     TEXT,

    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_status ON analysis_sessions(status);
CREATE INDEX idx_session_date ON analysis_sessions(started_at);
```

### 3.5 洞察テーブル

```sql
CREATE TABLE insights (
    insight_id          TEXT PRIMARY KEY,
    session_id          TEXT,
    category            TEXT NOT NULL,
    title               TEXT NOT NULL,
    executive_summary   TEXT,
    detailed_narrative  TEXT,
    supporting_data     TEXT,  -- JSON
    visualization_type  TEXT,
    visualization_config TEXT,  -- JSON
    recommendations     TEXT,  -- JSON
    priority_score      INTEGER,
    target_audience     TEXT,  -- executive, audit_director, both
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES analysis_sessions(session_id)
);

CREATE INDEX idx_insight_session ON insights(session_id);
CREATE INDEX idx_insight_priority ON insights(priority_score DESC);
```

### 3.6 監査ログテーブル

```sql
CREATE TABLE audit_log (
    log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type          TEXT NOT NULL,
    event_details       TEXT,  -- JSON
    user_id             TEXT,
    session_id          TEXT,
    ip_address          TEXT,
    timestamp           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_event ON audit_log(event_type);
CREATE INDEX idx_audit_time ON audit_log(timestamp);
```

### 3.7 フィルタプリセットテーブル

```sql
CREATE TABLE filter_presets (
    preset_id           TEXT PRIMARY KEY,
    preset_name         TEXT NOT NULL,
    filter_config       TEXT NOT NULL,  -- JSON
    is_default          INTEGER DEFAULT 0,
    created_by          TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.8 インポート履歴テーブル

```sql
CREATE TABLE import_history (
    import_id           TEXT PRIMARY KEY,
    file_name           TEXT NOT NULL,
    file_type           TEXT NOT NULL,
    file_size           INTEGER,
    record_count        INTEGER,
    error_count         INTEGER DEFAULT 0,
    warning_count       INTEGER DEFAULT 0,
    status              TEXT NOT NULL,  -- pending, processing, completed, failed
    validation_report   TEXT,  -- JSON
    started_at          TIMESTAMP,
    completed_at        TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_import_status ON import_history(status);
CREATE INDEX idx_import_date ON import_history(created_at);
```

---

## 4. インデックス設計方針

### 4.1 クエリパターン別インデックス

| クエリパターン | 使用テーブル | インデックス |
|---------------|-------------|-------------|
| 期間フィルタ | journal_entries | idx_je_period |
| 勘定科目フィルタ | journal_entries | idx_je_account |
| 日付範囲検索 | journal_entries | idx_je_date |
| リスクレベルフィルタ | risk_scores | idx_risk_level |
| ハイリスク抽出 | risk_scores | idx_risk_score |
| ユーザー検索 | journal_entries | idx_je_user |
| 集計参照 | agg_by_period_account | idx_agg_pa_period |

### 4.2 パーティショニング検討

```sql
-- DuckDBはネイティブパーティションをサポートしていないが、
-- ファイル分割で擬似的に対応可能

-- 年度別ファイル分割例:
-- data/db/jaia_FY2024.duckdb
-- data/db/jaia_FY2025.duckdb
-- data/db/jaia_FY2026.duckdb

-- ATTACHで統合クエリ
ATTACH 'jaia_FY2024.duckdb' AS fy2024;
ATTACH 'jaia_FY2025.duckdb' AS fy2025;
```

---

## 5. データ整合性

### 5.1 外部キー制約

```sql
-- journal_entries → chart_of_accounts
-- risk_scores → journal_entries
-- journal_notes → journal_entries
-- trial_balance → chart_of_accounts
```

### 5.2 チェック制約

```sql
-- 会計期間: 1-14
-- リスクレベル: Critical, High, Medium, Low
-- 勘定科目タイプ: Asset, Liability, Equity, Revenue, Expense
-- メモタイプ: Question, Comment, Issue, Resolution
```

### 5.3 網羅性チェッククエリ

```sql
-- TB/JE照合: JE集計額 = TB発生額
SELECT
    je.gl_account_number,
    je.fiscal_year,
    je.accounting_period,
    je.sum_debit AS je_debit,
    je.sum_credit AS je_credit,
    tb.period_debit AS tb_debit,
    tb.period_credit AS tb_credit,
    je.sum_debit - tb.period_debit AS diff_debit,
    je.sum_credit - tb.period_credit AS diff_credit
FROM (
    SELECT
        gl_account_number,
        fiscal_year,
        accounting_period,
        SUM(debit_amount) AS sum_debit,
        SUM(credit_amount) AS sum_credit
    FROM journal_entries
    GROUP BY gl_account_number, fiscal_year, accounting_period
) je
JOIN trial_balance tb
    ON je.gl_account_number = tb.gl_account_number
    AND je.fiscal_year = tb.fiscal_year
    AND je.accounting_period = tb.accounting_period
WHERE ABS(je.sum_debit - tb.period_debit) > 0.01
   OR ABS(je.sum_credit - tb.period_credit) > 0.01;
```

---

## 6. マイグレーション管理

### 6.1 マイグレーションファイル構成

```
backend/db/migrations/
├── 001_initial_schema.sql
├── 002_add_risk_scores.sql
├── 003_add_aggregation_tables.sql
├── 004_add_financial_metrics.sql
└── 005_add_analysis_sessions.sql
```

### 6.2 マイグレーション実行

```python
# scripts/migrate.py
import duckdb
from pathlib import Path

def run_migrations(db_path: str, migrations_dir: str):
    """マイグレーション実行"""
    conn = duckdb.connect(db_path)

    # マイグレーション履歴テーブル
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 適用済みバージョン取得
    applied = set(
        row[0] for row in
        conn.execute("SELECT version FROM _migrations").fetchall()
    )

    # 未適用マイグレーション実行
    for migration_file in sorted(Path(migrations_dir).glob("*.sql")):
        version = int(migration_file.stem.split("_")[0])
        if version not in applied:
            print(f"Applying migration: {migration_file.name}")
            sql = migration_file.read_text()
            conn.execute(sql)
            conn.execute(
                "INSERT INTO _migrations (version, name) VALUES (?, ?)",
                [version, migration_file.name]
            )

    conn.close()
```

---

**次のステップ**: [04_api_design.md](04_api_design.md) でAPI詳細設計を行います。
