# JAIA (Journal entry AI Analyzer)
## 機能要件定義書 v5.0 - 最終統合版
### AICPA Audit Data Standards準拠 + 自律分析エージェント機能

**2026年2月 | PwC Japan GRC Advisory**

---

## 目次

1. [エグゼクティブサマリー](#1-エグゼクティブサマリー)
2. [システムアーキテクチャ](#2-システムアーキテクチャ)
3. [データ取込・インポート機能](#3-データ取込インポート機能)
4. [会計期間管理](#4-会計期間管理)
5. [バッチ処理機能要件](#5-バッチ処理機能要件)
6. [ルールベース仕訳リスク評価](#6-ルールベース仕訳リスク評価)
7. [機械学習異常検知](#7-機械学習異常検知)
8. [財務指標計算](#8-財務指標計算)
9. [オンライン処理機能要件](#9-オンライン処理機能要件)
10. [可視化ダッシュボード詳細仕様](#10-可視化ダッシュボード詳細仕様)
11. [仕訳メモ・タグ機能](#11-仕訳メモタグ機能)
12. [AIエージェント・自律分析仕様](#12-aiエージェント自律分析仕様)
13. [洞察生成・レポート出力機能](#13-洞察生成レポート出力機能)
14. [データモデル設計](#14-データモデル設計)
15. [非機能要件](#15-非機能要件)
16. [技術スタック](#16-技術スタック)

---

## 1. エグゼクティブサマリー

### 1.1 プロダクトビジョン

JAIA（Journal entry AI Analyzer）は、AICPA Audit Data Standardsに準拠したデータ取込、複数会計期間の趨勢分析、ルールベース（85ルール）＋機械学習（5手法）のハイブリッド異常検知、財務分析指標の可視化、**10エージェント構成のAIによる自律探索分析と洞察生成**、経営層・内部監査室長向けPPT/PDFレポート自動生成を統合した次世代監査支援ソリューションです。

### 1.2 主要機能

| 機能カテゴリ | 概要 |
|-------------|------|
| データ取込 | AICPA Audit Data Standards準拠、入力データ検証、科目マッピング、網羅性チェック |
| 会計期間管理 | 3期以上の複数期間対応、趨勢分析 |
| ダッシュボード | 11種類のタブによる仕訳データの多角的可視化 |
| 異常検知 | 85ルールのルールベース＋5手法の機械学習によるハイブリッド検知 |
| 財務分析 | 回転期間、流動性比率、収益性指標等の自動計算・可視化 |
| **自律AI分析** | **10エージェント構成のAIがダッシュボードを自律的に操作・分析・洞察生成** |
| レポート出力 | 経営者向けPPT（10スライド）、内部監査室長向けPDF（20-30ページ）の自動生成 |
| メモ・タグ | 仕訳へのメモ登録・タグ付け・レビュー管理 |

### 1.3 設計方針

- バッチ処理とオンライン処理を明確に分離し、事前計算による高速なUI応答とAIエージェントの即時分析を両立
- AICPA Audit Data Standardsへの完全準拠による監査データの標準化
- ローカル実行によるデータセキュリティの確保
- **エージェントの自律的な分析とHuman-in-the-Loopによる人間との協調**

---

## 2. システムアーキテクチャ

### 2.1 全体構成（6層）

| レイヤー | コンポーネント | 技術要素 |
|---------|---------------|---------|
| プレゼンテーション層 | ダッシュボード、チャットUI、レポートビューア | React, Recharts, D3.js, Nivo |
| **Dashboard Interface層** | **エージェント用API（チャート操作、フィルタ、ドリルダウン）** | **REST API** |
| レポート生成層 | PPT生成、PDF生成、テンプレートエンジン | pptxgenjs, ReportLab, Jinja2 |
| アプリケーション層 | AIエージェント、洞察生成、API、ルールエンジン | LangGraph, FastAPI |
| バッチ処理層 | ETL、集計、ML推論、財務計算 | Python, Polars, scikit-learn |
| データ層 | 仕訳DB、集計DB、洞察DB、ルールDB、テンプレートDB | DuckDB, SQLite, Parquet |

### 2.2 データフロー

```
1. 仕訳データ取込（CSV/Excel/ERP連携）→ 入力検証 → 生データDB
2. バッチ処理による集計・ルール評価・ML推論・スコアリング → 集計DB
3. オンライン処理（ダッシュボード表示、AI分析）
4. 自律エージェントによるダッシュボード操作・分析
5. 洞察生成 → PPT/PDFレポート自動生成
6. 分析結果出力（監査調書、レポート）
```

### 2.3 処理区分

| 処理区分 | 主な処理内容 | タイミング |
|---------|-------------|-----------|
| バッチ処理 | 集計、ルール評価、ML推論、財務指標計算 | 日次/週次/データ取込時 |
| オンライン処理 | 可視化表示、フィルタ適用、AI分析、レポート生成 | ユーザー操作時（200ms以下） |
| **自律分析** | **エージェントによるダッシュボード巡回・深掘り** | **ユーザー指示時（5-30分）** |

### 2.4 エージェントオーケストレーション構成

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Plan Engine │→ │ Task Queue  │→ │ State Mgmt  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              ↓ dispatch
┌─────────────────────────────────────────────────────────────────┐
│                    Specialist Agents (9種)                      │
│  Explorer, TrendAnalyzer, RiskAnalyzer, FinancialAnalyzer,     │
│  Investigator, Verifier, Hypothesis, Visualizer, Reporter       │
└─────────────────────────────────────────────────────────────────┘
                              ↓ tools
┌─────────────────────────────────────────────────────────────────┐
│                    Dashboard Interface Layer                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Chart API│ │Filter API│ │ Data API │ │Action API│          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. データ取込・インポート機能

### 3.1 AICPA Audit Data Standards準拠

#### 3.1.1 対応データファイル

| ファイル種別 | 説明 | AICPAテーブル名 |
|-------------|------|----------------|
| GL_Detail | 仕訳明細データ | GL_Detail_YYYYMMDD |
| Trial_Balance | 試算表データ | Trial_Balance_YYYYMMDD |
| Chart_of_Accounts | 勘定科目マスタ | Chart_Of_Accounts |
| User_Listing | ユーザーマスタ | User_Listing |
| Segment_Listing | セグメントマスタ | Segment_Listing |

#### 3.1.2 GL_Detail フィールド定義（AICPA準拠）

※ Level 1 = 必須項目、Level 2 = 推奨項目

| フィールド名 | 型 | Level | 説明 |
|-------------|---|-------|------|
| JE_Number | TEXT(100) | 1 | 仕訳番号（必須） |
| JE_Line_Number | INTEGER | 1 | 仕訳明細行番号 |
| Fiscal_Year | TEXT(4) | 1 | 会計年度（YYYY） |
| Accounting_Period | INTEGER | 1 | 会計期間（1-12, 13-14=調整期間） |
| Effective_Date | DATE | 1 | 効力発生日/転記日 |
| Entry_Date | DATE | 1 | 仕訳入力日 |
| GL_Account_Number | TEXT(100) | 1 | 勘定科目コード |
| Amount | DECIMAL | 1 | 金額（借方+/貸方-） |
| Functional_Amount | DECIMAL | 1 | 機能通貨金額 |
| JE_Line_Description | TEXT(1000) | 1 | 明細行摘要 |
| JE_Header_Description | TEXT(1000) | 2 | 仕訳ヘッダー摘要 |
| Source | TEXT(25) | 1 | ソースシステム/モジュール |
| Entered_By | TEXT(100) | 1 | 入力者ID |
| Approved_By | TEXT(100) | 2 | 承認者ID |
| Approved_Date | DATE | 2 | 承認日 |
| Last_Modified_Date | TIMESTAMP | 2 | 最終更新日時 |
| Last_Modified_By | TEXT(100) | 2 | 最終更新者ID |
| Business_Unit | TEXT(50) | 2 | 事業単位/部門 |
| Segment01-10 | TEXT(50) | 2 | セグメント1-10（任意） |
| Document_Number | TEXT(100) | 2 | 証憑番号 |
| Currency_Code | TEXT(3) | 2 | 取引通貨（ISO 4217） |

#### 3.1.3 Chart_of_Accounts フィールド定義

| フィールド名 | 型 | Level | 説明 |
|-------------|---|-------|------|
| GL_Account_Number | TEXT(100) | 1 | 勘定科目コード（PK） |
| GL_Account_Name | TEXT(200) | 1 | 勘定科目名 |
| FS_Caption | TEXT(200) | 1 | 財務諸表表示科目名 |
| Account_Type | TEXT(20) | 1 | 科目区分（Asset/Liability/Equity/Revenue/Expense） |
| Account_Subtype | TEXT(50) | 2 | 科目サブタイプ（Current/NonCurrent等） |
| Normal_Balance | TEXT(10) | 1 | 通常残高（Debit/Credit） |
| Parent_Account | TEXT(100) | 2 | 親勘定コード（階層用） |
| Account_Level | INTEGER | 2 | 階層レベル |
| Posting_Indicator | TEXT(1) | 2 | 転記可否（Y/N） |

#### 3.1.4 Trial_Balance フィールド定義

| フィールド名 | 型 | Level | 説明 |
|-------------|---|-------|------|
| GL_Account_Number | TEXT(100) | 1 | 勘定科目コード |
| Fiscal_Year | TEXT(4) | 1 | 会計年度 |
| Accounting_Period | INTEGER | 1 | 会計期間 |
| Opening_Balance | DECIMAL | 1 | 期首残高 |
| Period_Activity_Debit | DECIMAL | 1 | 期間借方発生額 |
| Period_Activity_Credit | DECIMAL | 1 | 期間貸方発生額 |
| Closing_Balance | DECIMAL | 1 | 期末残高 |
| Budget_Amount | DECIMAL | 2 | 予算金額 |

### 3.2 入力データ検証

#### 3.2.1 検証チェック一覧

| チェックID | チェック内容 | 重要度 | エラー時処理 |
|-----------|-------------|--------|-------------|
| VAL_001 | 必須フィールド（Level 1）の存在確認 | Critical | インポート中止 |
| VAL_002 | データ型の妥当性（日付、数値、文字列長） | Critical | 該当行スキップ |
| VAL_003 | 日付範囲の妥当性（会計期間内） | High | 警告＋確認 |
| VAL_004 | 金額の借方/貸方バランス（仕訳単位） | Critical | 該当仕訳スキップ |
| VAL_005 | 勘定科目コードのCoA存在確認 | High | 警告＋マッピング要求 |
| VAL_006 | 重複仕訳番号の検出 | High | 警告＋確認 |
| VAL_007 | 会計期間の妥当性（1-14） | Critical | インポート中止 |
| VAL_008 | 通貨コードの妥当性（ISO 4217） | Medium | 警告 |
| VAL_009 | ユーザーIDの存在確認（User_Listing） | Low | 警告 |
| VAL_010 | 文字エンコーディング（UTF-8） | Medium | 自動変換 |

#### 3.2.2 検証結果レポート

- インポート前にプレビュー画面で検証結果を表示
- エラー/警告件数のサマリー表示
- 問題行のCSVエクスポート機能
- 検証ログの保存（監査証跡用）

### 3.3 科目マッピング機能

#### 3.3.1 マッピング対象

| マッピング種別 | 説明 |
|--------------|------|
| FS_Caption（表示科目） | 勘定科目→財務諸表表示科目（売上高、売上原価、販管費等）へのマッピング |
| Account_Type | 勘定科目→BS/PL区分（Asset/Liability/Equity/Revenue/Expense） |
| Account_Subtype | 勘定科目→サブ区分（流動/固定、営業/営業外等） |
| Disclosure_Category | 開示レベル分類（セグメント、関係会社、重要勘定等） |

#### 3.3.2 マッピング方法

- **自動マッピング**: 勘定科目コード/名称のパターンマッチング
- **手動マッピング**: UIでドラッグ&ドロップまたは選択
- **テンプレート適用**: 過去のマッピング定義を再利用
- **AIサジェスト**: LLMによる科目名からの推奨マッピング

### 3.4 網羅性チェック（TB/CoA/JE照合）

#### 3.4.1 照合チェック一覧

| チェックID | チェック内容 | 検出時アクション |
|-----------|-------------|-----------------|
| REC_001 | TBの全勘定がCoAに存在するか | マッピング要求/エラー |
| REC_002 | JEの全勘定がCoAに存在するか | マッピング要求/エラー |
| REC_003 | JE集計額 = TB発生額（期間別） | 差異レポート表示 |
| REC_004 | TB期首残高 + JE発生額 = TB期末残高 | 差異レポート表示 |
| REC_005 | CoAの全転記可能勘定にJEが存在するか | 未使用勘定リスト表示 |
| REC_006 | BS勘定の借方/貸方合計がバランス | 差異レポート表示 |

### 3.5 対応データソース

| ソース種別 | 対応形式 | 備考 |
|-----------|---------|------|
| ファイル | CSV, Excel (.xlsx), 固定長テキスト, XML (XBRL) | 文字コード自動判定 |
| ERP連携 | SAP (RFC/BAPI), Oracle EBS, 勘定奉行, PCA会計 | API/DB直接接続 |
| クラウド会計 | freee, マネーフォワード, 弥生会計オンライン | API連携 |

### 3.6 データクレンジング処理

- 勘定科目コードの正規化（マスタとの突合、名寄せ）
- 金額フォーマットの統一（通貨、小数点、カンマ処理）
- 日付形式の正規化（和暦/西暦、各種フォーマット対応）
- 欠損値・異常値の検出とフラグ付け

---

## 4. 会計期間管理

### 4.1 期間登録・管理

#### 4.1.1 会計期間マスタ

| フィールド | 型 | 説明 |
|----------|---|------|
| period_id | VARCHAR(20) | 期間ID（例: FY2024Q1, FY2024M03） |
| fiscal_year | VARCHAR(4) | 会計年度（YYYY） |
| period_type | ENUM | 期間種別（Annual/Quarterly/Monthly） |
| period_number | INTEGER | 期間番号（月:1-12, 四半期:1-4, 調整:13-14） |
| start_date | DATE | 期間開始日 |
| end_date | DATE | 期間終了日 |
| is_adjustment_period | BOOLEAN | 調整期間フラグ |
| status | ENUM | ステータス（Open/Closed/Locked） |
| prior_period_id | VARCHAR(20) | 前期間ID（趨勢分析用リンク） |
| same_period_prior_year_id | VARCHAR(20) | 前年同期ID（YoY分析用リンク） |

### 4.2 複数期間対応（3期以上）

- 最低3会計期間の登録が可能（趨勢分析の要件）
- 最大10会計年度まで登録可能
- 月次/四半期/年次の粒度で期間定義可能
- 期間間のデータ比較・推移分析をサポート

### 4.3 趨勢分析対応

| 分析種別 | 説明 |
|---------|------|
| 前期比較（MoM） | 当月 vs 前月の増減額・増減率 |
| 前年同期比較（YoY） | 当月 vs 前年同月の増減額・増減率 |
| 四半期比較（QoQ） | 当四半期 vs 前四半期の比較 |
| 3期トレンド | 直近3期間の推移パターン（増加/減少/横ばい） |
| 移動平均比較 | 3期/6期/12期移動平均との乖離 |
| 季節性分析 | 過去の同期間との季節性パターン比較 |

---

## 5. バッチ処理機能要件

### 5.1 事前集計処理

#### 5.1.1 AICPA属性別事前集計テーブル

ダッシュボードのフィルタ操作時の応答時間を短縮するため、AICPA属性ごとに事前集計を実行。

| 集計テーブル | 集計キー | 更新頻度 |
|-------------|---------|---------|
| agg_by_period_account | Fiscal_Year, Accounting_Period, GL_Account_Number | 日次 |
| agg_by_period_fs_caption | Fiscal_Year, Accounting_Period, FS_Caption | 日次 |
| agg_by_period_account_type | Fiscal_Year, Accounting_Period, Account_Type | 日次 |
| agg_by_period_source | Fiscal_Year, Accounting_Period, Source | 日次 |
| agg_by_period_user | Fiscal_Year, Accounting_Period, Entered_By | 日次 |
| agg_by_period_segment | Fiscal_Year, Accounting_Period, Segment01-10 | 日次 |
| agg_by_period_business_unit | Fiscal_Year, Accounting_Period, Business_Unit | 日次 |
| agg_by_date_account | Effective_Date, GL_Account_Number | 日次 |
| agg_by_date_fs_caption | Effective_Date, FS_Caption | 日次 |
| agg_trend_mom | GL_Account_Number + 前月比増減 | 日次 |
| agg_trend_yoy | GL_Account_Number + 前年同期比増減 | 日次 |
| agg_account_flow | 借方勘定, 貸方勘定（サンキー用） | 日次 |
| agg_benford | GL_Account_Number + 第1/第2桁分布 | 週次 |
| agg_monthly_tb | 月次試算表（残高・発生額・累計） | 日次 |
| agg_monthly_bs_pl | 月次BS/PL表示科目別集計 | 日次 |
| agg_variance_mom/yoy | 前月比/前年同月比の増減額・率 | 日次 |
| agg_user_pattern | 起票者×勘定科目の組み合わせ頻度 | 日次 |
| agg_time_distribution | 時間帯別・曜日別の仕訳発生分布 | 日次 |

#### 5.1.2 集計カラム共通仕様

- count: 仕訳件数
- sum_debit: 借方合計
- sum_credit: 貸方合計
- sum_amount: 純額（借方-貸方）
- avg_amount: 平均金額
- std_amount: 標準偏差
- min_amount / max_amount: 最小/最大金額
- risk_count_critical / high / medium / low: リスクレベル別件数
- updated_at: 集計更新日時

---

## 6. ルールベース仕訳リスク評価

### 6.1 ルールカテゴリサマリー（全85ルール）

| カテゴリ | 概要 | ルール数 |
|---------|------|---------|
| 金額ルール | 閾値超過、端数パターン、異常金額検知 | 15件 |
| 時間ルール | 業務時間外、決算期集中、週末・祝日処理 | 10件 |
| 勘定ルール | 異常な勘定組み合わせ、禁止パターン | 20件 |
| 承認ルール | 自己承認、承認スキップ、権限逸脱 | 8件 |
| 摘要ルール | キーワード検知、摘要なし、定型外摘要 | 12件 |
| パターンルール | 分割入力、反復仕訳、相殺パターン | 10件 |
| 趨勢ルール | 前期比、前年比、トレンド異常 | 10件 |

### 6.2 金額ルール詳細

| ルールID | 検知条件 | 重要度 | スコア |
|---------|---------|--------|-------|
| AMT_001 | 金額 ≧ 重要性基準値（例: 1億円） | Critical | +40 |
| AMT_002 | 金額 ≧ 承認閾値（例: 1,000万円） | High | +25 |
| AMT_003 | 端数が000（キリ番）かつ100万円以上 | Medium | +15 |
| AMT_004 | 端数が999または99（閾値すれすれ） | High | +20 |
| AMT_005 | 同一勘定の平均±3σを超える金額 | High | +25 |
| AMT_006 | マイナス金額（通常発生しない勘定） | Medium | +15 |
| AMT_007 | 金額が過去最大値を更新 | Medium | +15 |

### 6.3 時間ルール詳細

| ルールID | 検知条件 | 重要度 | スコア |
|---------|---------|--------|-------|
| TIM_001 | 入力時刻が22:00〜6:00（深夜帯） | Medium | +15 |
| TIM_002 | 土日・祝日の入力 | Medium | +10 |
| TIM_003 | 決算日前後5日間の入力 | Low | +5 |
| TIM_004 | 転記日と入力日が30日以上乖離 | High | +20 |
| TIM_005 | 過年度仕訳（前期以前の転記日） | High | +25 |

### 6.4 勘定ルール詳細

| ルールID | 検知条件 | 重要度 | スコア |
|---------|---------|--------|-------|
| ACC_001 | 収益科目と費用科目の直接相殺 | Critical | +35 |
| ACC_002 | 現金科目の相手勘定が売上/仕入以外 | Medium | +15 |
| ACC_003 | 通常使用しない勘定科目への計上 | High | +20 |
| ACC_004 | 仮勘定の長期滞留 | Medium | +15 |
| ACC_005 | 雑収入/雑損失への高額計上 | High | +20 |
| ACC_006 | 過去に使用実績のない勘定組み合わせ | Medium | +15 |

### 6.5 承認ルール詳細

| ルールID | 検知条件 | 重要度 | スコア |
|---------|---------|--------|-------|
| APR_001 | 起票者と承認者が同一（自己承認） | Critical | +40 |
| APR_002 | 承認者が空欄（承認なし） | High | +30 |
| APR_003 | 承認者の権限レベルが不足 | High | +25 |
| APR_004 | 承認から転記まで1分未満（形式承認） | Medium | +15 |

### 6.6 摘要・パターンルール詳細

| ルールID | 検知条件 | 重要度 | スコア |
|---------|---------|--------|-------|
| DSC_001 | 摘要が空欄または1文字 | Medium | +15 |
| DSC_002 | 「調整」「修正」「訂正」を含む | Medium | +10 |
| DSC_003 | 「期末」「決算」を含む期中仕訳 | High | +20 |
| PTN_001 | 同一内容の仕訳が閾値直下で複数回（分割） | Critical | +35 |
| PTN_002 | 計上と取消の繰り返し（3回以上） | High | +25 |
| PTN_003 | 逆仕訳の相手仕訳なし | High | +20 |

### 6.7 趨勢ルール詳細

| ルールID | 検知条件 | 重要度 | スコア |
|---------|---------|--------|-------|
| TRD_001 | 前月比増減率 ≧ ±50%（金額100万円以上） | High | +25 |
| TRD_002 | 前年同期比増減率 ≧ ±30%（金額500万円以上） | High | +20 |
| TRD_003 | 3期連続増加/減少トレンド（各期 ≧ ±20%） | Medium | +15 |
| TRD_004 | 季節性パターンからの逸脱 ≧ 2σ | Medium | +15 |
| TRD_005 | 12期移動平均からの乖離 ≧ 3σ | High | +20 |
| TRD_006 | 売上高減少 but 売掛金増加（逆相関） | Critical | +35 |
| TRD_007 | 仕入高減少 but 買掛金増加（逆相関） | Critical | +35 |
| TRD_008 | 回転期間の急激な変化 ≧ ±30% | High | +25 |
| TRD_009 | 通常発生しない期間への計上（季節外れ） | Medium | +15 |
| TRD_010 | 決算月への費用集中（前月比3倍以上） | High | +20 |

---

## 7. 機械学習異常検知

### 7.1 異常検知アルゴリズム（5手法）

| 手法 | 検知対象 | 出力スコア |
|-----|---------|-----------|
| Isolation Forest | 金額・頻度の多変量外れ値 | anomaly_score_if: 0.0〜1.0 |
| Local Outlier Factor | 局所的なパターン逸脱 | anomaly_score_lof: 0.0〜1.0 |
| One-Class SVM | 正常パターンからの逸脱 | anomaly_score_svm: 0.0〜1.0 |
| Autoencoder | 複合特徴の再構成誤差 | reconstruction_error（正規化） |
| Benford Analysis | 金額の桁分布異常 | benford_score: χ²ベース |

### 7.2 統合リスクスコア

各異常検知スコアを統合した統合リスクスコア（integrated_risk_score）を算出。

```
integrated_risk_score = (rule_risk_score × 0.6) + (ml_risk_score × 0.4)
```

| リスクレベル | スコア範囲 | 推奨アクション |
|------------|----------|---------------|
| Critical | 81 - 100 | 即時調査必須 |
| High | 61 - 80 | 優先的に調査 |
| Medium | 31 - 60 | サンプル抽出対象 |
| Low | 0 - 30 | 通常監視 |

### 7.3 スコアリング出力テーブル

| カラム名 | 説明 |
|---------|------|
| journal_id | 仕訳ID（主キー） |
| integrated_risk_score | 統合リスクスコア (0-100) |
| risk_level | リスクレベル (Low/Medium/High/Critical) |
| anomaly_flags | 検出された異常フラグのJSON配列 |
| top_risk_factors | 上位リスク要因の説明（日本語） |
| scored_at | スコアリング実行日時 |

---

## 8. 財務指標計算

### 8.1 財務指標一覧

| 指標名 | 計算式 |
|-------|--------|
| 売掛金回転期間 | 売掛金残高 ÷ (売上高 ÷ 365) |
| 買掛金回転期間 | 買掛金残高 ÷ (仕入高 ÷ 365) |
| 棚卸資産回転期間 | 棚卸資産残高 ÷ (売上原価 ÷ 365) |
| CCC（キャッシュコンバージョンサイクル） | 売掛金回転期間 + 棚卸資産回転期間 - 買掛金回転期間 |
| 流動比率 | 流動資産 ÷ 流動負債 × 100 |
| 当座比率 | (流動資産 - 棚卸資産) ÷ 流動負債 × 100 |
| 売上総利益率 | 売上総利益 ÷ 売上高 × 100 |
| 営業利益率 | 営業利益 ÷ 売上高 × 100 |

---

## 9. オンライン処理機能要件

### 9.1 可視化ダッシュボード

#### 9.1.1 共通フィルタ機能（グローバルフィルタ）

サイドパネルに配置し、全タブに適用されるフィルタ群。

| フィルタ名 | UIタイプ | 選択方式 | 備考 |
|----------|---------|---------|------|
| 期間 | 日付ピッカー | 範囲選択 | プリセット（今月/前月/Q1等） |
| 勘定科目 | ツリーセレクタ | 複数/階層選択 | BS/PL/表示科目でグループ化 |
| 表示科目 | チェックボックス | 複数選択 | 財務諸表の表示科目レベル |
| 部門 | ドロップダウン | 複数選択 | 階層構造対応 |
| 金額範囲 | レンジスライダー | 最小-最大 | 対数スケール切替可 |
| リスクレベル | チェックボックス | 複数選択 | Critical/High/Medium/Low |
| 起票者/承認者 | 検索付きDD | 複数選択 | 部門でグループ化 |
| 摘要キーワード | テキスト入力 | 部分一致 | AND/OR条件対応 |
| ルールカテゴリ | チェックボックス | 複数選択 | 金額/時間/勘定/承認/摘要/パターン/趨勢 |

- フィルタ変更は即時反映（デバウンス200ms）
- 複数フィルタはAND条件で適用
- フィルタ状態はURLパラメータに反映（共有可能）
- フィルタプリセットの保存・呼び出し機能

### 9.2 チャットUI

#### 9.2.1 機能概要

ユーザーが自然言語でダッシュボードデータについて質問し、AIエージェントが回答・可視化を生成。

#### 9.2.2 対話シナリオ例

| ユーザー入力例 | 期待される応答 |
|--------------|---------------|
| 今月のハイリスク仕訳を見せて | リスクスコア上位の仕訳一覧＋サマリー |
| 交際費が急増している理由は？ | 時系列分析＋要因分析＋関連仕訳 |
| ベンフォード分析で異常な勘定は？ | χ²スコア上位の勘定＋分布グラフ |
| この仕訳の関連取引を探して | 同一取引先・類似金額の仕訳検索 |

### 9.3 Human-in-the-Loop（人間との協調）

完全自律ではなく、重要な判断点で人間に確認を求める機能。

#### 9.3.1 確認が必要なケース

| ケース | 説明 |
|-------|------|
| critical_finding | Critical発見時 |
| unclear_hypothesis | 仮説が不明確な場合 |
| conflicting_evidence | 矛盾する証拠がある場合 |
| business_context_needed | 業務背景の確認が必要 |
| before_report_generation | レポート生成前の承認 |

#### 9.3.2 質問テンプレート

| ケース | テンプレート |
|-------|-------------|
| critical_finding | 「Critical異常を検出しました。{detail}。この仕訳についてご存知の背景情報はありますか？」 |
| business_context | 「売上が{rate}%増加していますが、何か特別なビジネスイベントがありましたか？」 |
| approval_request | 「以下の発見事項をレポートに含めてよろしいですか？\n{findings}」 |

### 9.4 レスポンス要件

| 操作 | 目標 | 最大許容 |
|-----|------|---------|
| ダッシュボード初期表示 | 500ms | 1秒 |
| フィルタ適用・グラフ更新 | 200ms | 500ms |
| タブ切り替え | 300ms | 800ms |
| ドリルダウン | 400ms | 1秒 |
| AIチャット応答 | 2秒 | 5秒 |
| 自律探索分析 | 30秒 | 60秒 |
| 仕訳詳細検索（1万件以下） | 1秒 | 3秒 |

---

## 10. 可視化ダッシュボード詳細仕様

### 10.1 タブ構成一覧（11タブ）

| # | タブ名 | 分析目的 | チャート数 |
|---|-------|---------|-----------|
| 1 | サマリー | 全体概況、KPI、重要アラート | 6 |
| 2 | 時系列分析 | 日次/月次トレンド、前年比較、季節性 | 5 |
| 3 | 勘定科目分析 | 勘定別推移、構成比、異常検知結果 | 6 |
| 4 | 試算表・財務諸表 | 月次TB推移、BS/PL表示、増減分析 | 5 |
| 5 | 財務指標分析 | 回転期間、流動性、収益性指標推移 | 6 |
| 6 | 資金フロー分析 | 勘定間資金移動（サンキー）、CF | 4 |
| 7 | 異常検知・リスク | ハイリスク仕訳、ルール違反、MLスコア | 6 |
| 8 | ベンフォード分析 | 桁分布分析、不正検知 | 4 |
| 9 | ユーザー・承認 | 起票者パターン、承認フロー | 5 |
| 10 | 仕訳明細検索 | 個別仕訳検索、フィルタ、詳細 | 2 |
| 11 | AI分析レポート | AIエージェント自動分析結果 | 動的 |

### 10.2 Dashboard Interface Layer（エージェント用API）

エージェントがダッシュボードを「見る」「操作する」ためのAPI群。

| API | 機能 | 入出力例 |
|-----|------|---------|
| `view_chart(chart_id)` | チャートのデータ・画像を取得 | → {data: [...], image_base64, insights} |
| `view_table(table_id, filters)` | テーブルデータを取得 | → {rows: [...], summary} |
| `apply_filter(filter_spec)` | グローバルフィルタを適用 | {period: "2024Q4", account_type: "Revenue"} |
| `drill_down(element_id)` | チャート要素をドリルダウン | クリックした棒グラフの詳細データ |
| `get_kpi_values()` | 現在のKPIカード値を取得 | {total_je: 1.2M, risk_count: 342, ...} |
| `search_journals(query)` | 仕訳を検索 | 条件に合致する仕訳リスト |
| `get_risk_details(journal_id)` | 仕訳のリスク詳細を取得 | ルール違反、MLスコア等 |
| `add_note(journal_id, note)` | 仕訳にメモ追加 | レビューコメント記録 |
| `add_tag(journal_id, tag)` | 仕訳にタグ付与 | 要確認、異常等 |
| `take_screenshot(view_id)` | 現在表示の画面キャプチャ | レポート用画像 |
| `export_data(spec)` | データをエクスポート | CSV/JSON形式 |

### 10.3 各タブの可視化仕様

#### 10.3.1 サマリータブ

| チャート名 | 種類 | 表示内容 | インタラクション |
|----------|------|---------|----------------|
| KPIカード群 | スコアカード | 総仕訳件数、総金額、リスク件数 | クリックで詳細タブへ |
| リスクレベル分布 | ドーナツチャート | Critical/High/Medium/Low比率 | セグメントでフィルタ |
| 月次推移サマリー | 複合チャート | 件数(棒)+金額(線)+リスク(線) | 期間ブラシ選択 |
| 勘定科目Top10 | 横棒グラフ | 金額上位10勘定 | クリックで勘定詳細へ |
| 最新アラート一覧 | リストテーブル | 直近Critical/High 5件 | 行クリックで詳細モーダル |
| ルール違反ヒートマップ | ヒートマップ | ルールカテゴリ×月のヒット数 | セルクリックで仕訳一覧 |

#### 10.3.2 時系列分析タブ

| チャート名 | 種類 | 表示内容 | インタラクション |
|----------|------|---------|----------------|
| 日次仕訳推移 | エリアチャート | 日次金額合計の推移 | ズーム、期間選択 |
| 月次比較チャート | グループ棒グラフ | 当年/前年の月別比較 | 月クリックで日次展開 |
| 前年同月比増減 | 滝グラフ | 前年比での増減要因分解 | 棒クリックで勘定詳細 |
| 曜日×時間帯分布 | ヒートマップ | 曜日(縦)×時間帯(横)の件数 | セルクリックで該当仕訳 |
| 季節性分析 | レーダーチャート | 月別平均パターン比較 | 軸クリックで月次詳細 |

#### 10.3.3 勘定科目分析タブ

| チャート名 | 種類 | 表示内容 | インタラクション |
|----------|------|---------|----------------|
| 勘定科目ツリーマップ | ツリーマップ | 勘定階層の金額構成比（色=リスク） | クリックでドリルダウン |
| 勘定別日次推移+異常点 | 線+散布図 | 日次金額+異常スコア点 | 点クリックで仕訳詳細 |
| 勘定月次推移比較 | マルチライン | 複数勘定の月次比較 | 凡例クリックで表示切替 |
| 勘定組み合わせ | コードダイアグラム | 借方/貸方の組み合わせ頻度 | 弧クリックで該当仕訳 |
| 勘定別統計テーブル | データテーブル | 件数、金額、平均、σ、リスク数 | ソート、フィルタ、エクスポート |
| 増減ハイライト表 | 条件付書式 | 前月比±20%以上をハイライト | 行クリックで推移表示 |

#### 10.3.4 異常検知・リスクタブ

| チャート名 | 種類 | 表示内容 | インタラクション |
|----------|------|---------|----------------|
| リスクスコア分布 | ヒストグラム | 統合リスクスコアの分布 | 範囲選択でフィルタ |
| ルール違反ランキング | 横棒グラフ | ルール別ヒット件数Top20 | 棒クリックで仕訳一覧 |
| ハイリスク仕訳一覧 | データテーブル | スコア上位の仕訳詳細 | ソート、フィルタ、詳細 |
| リスク推移チャート | 積み上げ面 | リスクレベル別件数推移 | 領域クリックで仕訳 |
| MLスコア散布図 | 散布図 | X=ルール、Y=MLスコア | 範囲選択、点クリック |
| 異常パターンマップ | t-SNE/UMAP | 仕訳特徴量の2次元圧縮 | クラスタ選択 |

### 10.4 エージェント操作の可視化UI

ユーザーがエージェントの動きを見られるUI。

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 JAIA Autonomous Audit Agent                      [Stop]  │
├─────────────────────────────────────────────────────────────┤
│ 現在のフェーズ: 深掘り分析 (3/8)                              │
│ ████████████░░░░░░░░ 40%                                    │
├─────────────────────────────────────────────────────────────┤
│ 🔍 現在の操作:                                               │
│ ├─ Risk Analyzer が「勘定科目分析」タブを確認中              │
│ ├─ フィルタ適用: 期間=2024Q4, リスク=High                   │
│ └─ ドリルダウン: 売掛金勘定の詳細を調査                      │
├─────────────────────────────────────────────────────────────┤
│ 📊 発見事項 (5件):                                           │
│ ├─ ⚠️ Critical: 売掛金の異常増加（前年比+85%）              │
│ ├─ ⚠️ High: 自己承認仕訳が32件検出                          │
│ └─ 📝 Medium: 回転期間の悪化傾向                             │
├─────────────────────────────────────────────────────────────┤
│ 💬 エージェントからの質問:                                   │
│ 「売上が急増していますが、大型受注などの背景はありますか？」   │
│ [はい、説明を入力] [いいえ、調査続行] [詳細を見る]            │
└─────────────────────────────────────────────────────────────┘
```

### 10.5 操作履歴ログ

```
┌─────────────────────────────────────────────────────────────┐
│ 📋 操作履歴                                    [Export]      │
├─────────────────────────────────────────────────────────────┤
│ 10:23:45 | Explorer    | サマリータブを確認                  │
│ 10:23:52 | Explorer    | KPI: 総仕訳1.2M件, Critical 45件    │
│ 10:24:01 | Orchestrator| 優先調査: 売掛金, 売上高            │
│ 10:24:15 | RiskAnalyzer| 勘定科目タブに移動                 │
│ 10:24:22 | RiskAnalyzer| フィルタ: 売掛金                   │
│ 10:24:35 | RiskAnalyzer| 異常検出: 前年比+85%               │
│ 10:24:48 | Investigator| 仕訳JE-2024-12345をドリルダウン    │
│ 10:25:02 | Investigator| タグ付与: 要確認                   │
│ 10:25:15 | Verifier   | 発見事項を検証中...                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. 仕訳メモ・タグ機能

### 11.1 メモ機能

#### 11.1.1 メモデータ構造

| フィールド | 型 | 説明 |
|----------|---|------|
| note_id | VARCHAR(36) | メモID（UUID） |
| journal_id | VARCHAR(100) | 対象仕訳ID（JE_Number + JE_Line_Number） |
| note_text | TEXT | メモ本文（最大2000文字） |
| note_type | ENUM | 種別（Question/Comment/Issue/Resolution） |
| created_by | VARCHAR(100) | 作成者 |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |
| is_resolved | BOOLEAN | 解決済みフラグ |

### 11.2 タグ機能

#### 11.2.1 タグデータ構造

| フィールド | 型 | 説明 |
|----------|---|------|
| tag_id | VARCHAR(36) | タグID |
| tag_name | VARCHAR(50) | タグ名（例: 要確認、重要、完了） |
| tag_color | VARCHAR(7) | タグ色（#RRGGBB） |
| tag_category | ENUM | カテゴリ（Review/Risk/Status/Custom） |

#### 11.2.2 定義済みタグ

| タグ名 | 色 | 用途 |
|-------|---|------|
| 要確認 | #FFC107（黄） | 後で確認が必要な仕訳 |
| 要調査 | #FF5722（橙） | 詳細調査が必要 |
| 異常 | #F44336（赤） | 異常と判断された仕訳 |
| 確認済 | #4CAF50（緑） | 確認完了 |
| 問題なし | #2196F3（青） | 正常と判断 |
| クライアント確認 | #9C27B0（紫） | クライアントへの確認待ち |

### 11.3 レビュー管理機能

- タグ付き仕訳の一覧表示・フィルタ
- 未解決メモの一覧表示
- レビューステータスの集計ダッシュボード
- タグ/メモ付き仕訳のエクスポート
- レビュー履歴の監査証跡

---

## 12. AIエージェント・自律分析仕様

### 12.1 エージェント構成（10エージェント）

| エージェント | 役割 | 使用ツール |
|------------|------|-----------|
| **Orchestrator** | 分析計画立案、エージェント間調整、完了判定 | create_analysis_plan, dispatch_agent, decide_completion |
| **Explorer** | 全体概況把握、KPI確認、異常エリア特定 | view_summary_tab, view_kpi_cards, scan_risk_distribution |
| **TrendAnalyzer** | 趨勢分析、前年比、季節性パターン確認 | compare_periods, analyze_seasonality |
| **RiskAnalyzer** | ルール違反分析、MLスコア解釈、パターン検出 | get_rule_violations, analyze_pattern, get_ml_scores |
| **FinancialAnalyzer** | 財務指標分析、比率分析、BS/PL整合性確認 | get_kpis, analyze_ratios |
| **Investigator** | 個別仕訳の深掘り、関連取引追跡 | search_journals, get_related, add_note, add_tag |
| **Verifier** | 発見事項の妥当性検証、反証探索、誤検知除外 | check_finding_validity, search_counter_evidence |
| **Hypothesis** | 仮説生成、因果関係推論、追加調査提案 | generate_hypothesis, suggest_investigation |
| **Visualizer** | グラフ生成、可視化コード出力 | generate_chart, create_table, capture_screenshot |
| **Reporter** | PPT/PDF生成、レポート組み立て | create_ppt, create_pdf, export_report |

### 12.2 エージェントツール定義

#### 12.2.1 Orchestrator用ツール

| ツール名 | 機能説明 |
|---------|---------|
| create_analysis_plan | 分析計画を作成 |
| dispatch_agent | 専門エージェントにタスクを割り当て |
| check_progress | 分析進捗を確認 |
| resolve_conflict | エージェント間の矛盾を解消 |
| decide_completion | 分析完了を判定 |
| trigger_report_generation | レポート生成を開始 |

#### 12.2.2 データ取得系ツール

| ツール名 | 機能説明 |
|---------|---------|
| query_aggregates | 集計テーブルへのクエリ実行 |
| get_summary_stats | 指定期間・勘定のサマリー統計を取得 |
| get_high_risk_journals | リスクスコア上位N件の仕訳を取得 |
| search_journals | 条件指定による仕訳検索 |
| get_related_journals | 指定仕訳に関連する仕訳を検索 |
| get_benford_analysis | ベンフォード分析結果を取得 |
| get_rule_violations | ルール違反の分析 |
| get_ml_scores | ML異常スコアを取得 |
| get_kpis | 財務指標を取得 |

#### 12.2.3 可視化生成系ツール

| ツール名 | 機能説明 |
|---------|---------|
| generate_time_series_chart | 時系列グラフを生成 |
| generate_distribution_chart | 分布グラフを生成 |
| generate_comparison_chart | 比較グラフを生成 |
| generate_heatmap | ヒートマップを生成 |
| generate_treemap | ツリーマップを生成 |

#### 12.2.4 Verifier用ツール

| ツール名 | 機能説明 |
|---------|---------|
| check_finding_validity | 発見事項の妥当性を確認 |
| search_counter_evidence | 反証を探索 |
| compare_with_baseline | ベースラインと比較 |
| mark_false_positive | 誤検知としてマーク |

### 12.3 視覚認識機能

エージェントがグラフや数字を「見て判断する」ための機能。

```python
class ChartPerception:
    """チャートの視覚的特徴を解釈"""

    def analyze_chart(self, chart_data, chart_image):
        return {
            "chart_type": "bar_chart",
            "data_points": [...],
            "visual_patterns": {
                "trend": "increasing",
                "outliers": [{"x": "2024-03", "y": 150000, "deviation": "3.2σ"}],
                "seasonality": "quarterly_peak",
                "anomaly_regions": [{"start": "2024-01", "end": "2024-03"}]
            },
            "derived_insights": [
                "3月に急激な増加（前月比+150%）",
                "過去の季節パターンから逸脱"
            ]
        }

    def compare_charts(self, chart1, chart2):
        """2つのチャートを比較して相関・乖離を検出"""
        return {
            "correlation": 0.85,
            "divergence_points": [...],
            "interpretation": "売上と売掛金に正の相関あり、ただし3月に乖離"
        }
```

### 12.4 自律分析フロー（State Machine）

```
[Start]
    │
    ▼
[1. 初期スキャン]
    │ Explorer: ダッシュボード全体を巡回
    │ - サマリータブのKPI確認
    │ - リスク分布の把握
    │ - 主要チャートの概観
    ▼
[2. 重点領域特定]
    │ Orchestrator: 分析優先度を決定
    │ - Critical/Highリスクが多い領域
    │ - 趨勢異常が検出された勘定
    │ - 前回分析からの変化点
    ▼
[3. 深掘り分析] ←────────────────────┐
    │ 各Specialist Agent:              │
    │ - フィルタを適用して詳細確認      │
    │ - ドリルダウンで個別仕訳を調査    │
    │ - 関連データを収集               │
    ▼                                 │
[4. 発見事項の記録]                     │
    │ - 仕訳にメモ・タグを付与          │
    │ - 発見事項をナレッジベースに登録   │
    ▼                                 │
[5. 検証・反証]                         │
    │ Verifier Agent:                  │
    │ - 発見事項の妥当性をチェック      │
    │ - 誤検知でないか確認             │
    ▼                                 │
[6. 仮説生成・追加調査]                 │
    │ Hypothesis Agent:                │
    │ - 「なぜこの異常が起きたか」を推論 │
    │ - 追加で確認すべき項目を提案      │
    │                                 │
    ├── 追加調査が必要 ───────────────┘
    │
    ▼
[7. 完了判定]
    │ Orchestrator:
    │ - 十分な分析ができたか判断
    │ - 未調査の重要領域がないか確認
    ▼
[8. レポート生成]
    │ Reporter Agent:
    │ - 発見事項を優先度順に整理
    │ - 適切なグラフ・表を選定
    │ - PPT/PDFを生成
    ▼
[End]
```

### 12.5 オーケストレーション状態管理

```python
class AnalysisState:
    """分析セッションの状態を管理"""

    # 分析計画
    analysis_plan: AnalysisPlan
    current_phase: str  # "scanning", "investigating", "verifying", "reporting"

    # 発見事項
    findings: List[Finding]
    hypotheses: List[Hypothesis]

    # 調査履歴
    visited_views: List[ViewVisit]       # どのチャートを見たか
    applied_filters: List[FilterAction]  # どのフィルタを適用したか
    drill_downs: List[DrillDownAction]   # どこをドリルダウンしたか

    # タグ・メモ
    tagged_journals: List[TaggedJournal]
    notes_added: List[Note]

    # 品質管理
    verification_results: List[VerificationResult]
    false_positives: List[FalsePositive]  # 誤検知として除外したもの

    # レポート素材
    selected_charts: List[ChartForReport]
    selected_tables: List[TableForReport]
    narrative_drafts: List[str]
```

### 12.6 自律判断ルール

エージェントが「いつ深掘りするか」「いつ終了するか」を判断するルール。

#### 12.6.1 深掘り判断閾値

| 項目 | 閾値 | 説明 |
|-----|------|------|
| risk_score | 60 | スコア60以上は深掘り |
| amount_threshold | 10,000,000円 | 1000万円以上は深掘り |
| variance_rate | 30% | 変動率30%以上は深掘り |
| anomaly_count | 5件 | 異常件数5件以上は深掘り |

#### 12.6.2 完了判断基準

| 項目 | 基準 | 説明 |
|-----|------|------|
| min_findings | 3件 | 最低3件の発見事項 |
| critical_coverage | 100% | Critical全件調査 |
| high_coverage | 80% | High 80%以上調査 |
| max_iterations | 10回 | 最大反復回数 |
| time_limit | 30分 | 制限時間 |

#### 12.6.3 誤検知判断基準

| 項目 | 条件 | 説明 |
|-----|------|------|
| recurring_pattern | True | 毎月同じパターン |
| explained_by_business | True | 業務上の説明あり |
| within_tolerance | 10%以内 | 許容範囲内 |

### 12.7 レスポンス時間目標

| 処理 | 目標時間 | 最大許容 |
|-----|---------|---------|
| チャット応答（単純質問） | 2秒以下 | 5秒 |
| チャート生成 | 3秒以下 | 8秒 |
| 1回の分析サイクル | 30秒以下 | 60秒 |
| 全体分析時間 | 5-30分 | データ量による |
| レポート生成 | 10秒以下 | 30秒 |

---

## 13. 洞察生成・レポート出力機能

### 13.1 洞察生成エンジン

#### 13.1.1 洞察生成プロセス

| # | ステップ | 処理内容 | 出力 |
|---|---------|---------|------|
| 1 | データ収集 | 各分析エージェントからの発見事項を収集 | raw_findings[] |
| 2 | 重要度評価 | ビジネスインパクト、リスク度、新規性で評価 | scored_findings[] |
| 3 | クラスタリング | 関連する発見事項をテーマ別にグループ化 | insight_clusters[] |
| 4 | ストーリー構築 | 因果関係、時系列、比較の観点で物語化 | insight_narratives[] |
| 5 | 提言生成 | 発見事項に基づく具体的なアクション提案 | recommendations[] |
| 6 | 可視化選定 | 各洞察に最適なグラフ/チャートを選定 | visualization_specs[] |

#### 13.1.2 洞察カテゴリ

| カテゴリ | 内容 | 優先度判定基準 |
|---------|------|---------------|
| 異常・リスク発見 | ハイリスク仕訳、ルール違反パターン、不正の兆候 | リスクスコア、金額規模 |
| トレンド変化 | 前年比大幅増減、季節性からの逸脱、新傾向 | 変動率、影響金額 |
| 財務指標警告 | 回転期間悪化、流動性低下、収益性変動 | 基準値との乖離度 |
| プロセス課題 | 承認遅延、自己承認集中、時間外処理多発 | 件数、関与者数 |
| ポジティブ発見 | 改善傾向、効率化の兆候、ベストプラクティス | 改善度、持続性 |

#### 13.1.3 洞察データ構造

| フィールド | 型 | 説明 |
|----------|---|------|
| insight_id | VARCHAR(36) | 洞察ID（UUID） |
| category | VARCHAR(50) | 洞察カテゴリ |
| title | VARCHAR(200) | 洞察タイトル（1行サマリー） |
| executive_summary | TEXT | 経営層向け要約（50〜100字） |
| detailed_narrative | TEXT | 詳細説明（200〜500字） |
| supporting_data | JSON | 根拠データ（数値、仕訳ID等） |
| visualization_type | VARCHAR(50) | 推奨グラフ種類 |
| visualization_config | JSON | グラフ設定（軸、色、フィルタ等） |
| recommendations | JSON[] | 提言リスト |
| priority_score | INTEGER | 優先度スコア（1-100） |
| target_audience | VARCHAR(50) | 対象読者（executive/audit_director/both） |

### 13.2 レポートテンプレート

| レポート名 | 形式 | 対象読者 | 生成タイミング |
|----------|------|---------|---------------|
| エグゼクティブサマリー | PPT | 経営者、取締役会 | 月次/四半期/オンデマンド |
| 内部監査分析レポート | PDF | 内部監査室長 | 月次/オンデマンド |
| リスクアラートレポート | PDF | リスク管理部門 | 週次/アラート発生時 |
| 監査調書 | DOCX/PDF | 外部監査人 | オンデマンド |
| ダッシュボード印刷用 | PDF | 全般 | オンデマンド |

### 13.3 PPT自動生成仕様（10スライド標準）

| # | スライドタイトル | 内容 | レイアウト |
|---|----------------|------|-----------|
| 1 | 表紙 | レポートタイトル、対象期間、作成日、会社ロゴ | センタリング、ダークBG |
| 2 | エグゼクティブサマリー | 主要発見事項3点、総合リスク評価、重要KPI | 3カラムカード |
| 3 | 期間サマリー | 仕訳件数/金額推移、前期比較、主要指標 | KPIカード+折れ線グラフ |
| 4 | リスク概況 | リスクレベル分布、Critical/High件数推移 | ドーナツ+棒グラフ |
| 5 | 重要発見事項① | 最重要洞察の詳細、根拠グラフ、影響額 | 左テキスト+右グラフ |
| 6 | 重要発見事項② | 2番目の洞察、トレンド分析、比較データ | 左テキスト+右グラフ |
| 7 | 重要発見事項③ | 3番目の洞察、パターン分析、関連仕訳 | 左テキスト+右グラフ |
| 8 | 財務指標ハイライト | 回転期間推移、流動性、収益性の要注意点 | マルチKPI+スパークライン |
| 9 | 提言・アクションアイテム | 優先度付きの改善提案リスト（3-5項目） | アイコン付きリスト |
| 10 | Appendix/次のステップ | 補足データへのリンク、次回分析予定 | シンプルリスト |

### 13.4 PPTデザイン仕様

#### カラーパレット

| 用途 | カラーコード | 使用箇所 |
|-----|------------|---------|
| Primary | #1E3A5F（ネイビー） | 表紙背景、見出し、強調テキスト |
| Secondary | #2E86AB（ティール） | グラフ主要色、アクセント |
| Accent | #F18F01（オレンジ） | 警告、ハイライト、Critical表示 |
| Background | #F8F9FA（ライトグレー） | コンテンツスライド背景 |
| Risk-Critical | #DC3545（赤） | Criticalリスク表示 |
| Risk-High | #FD7E14（橙） | Highリスク表示 |
| Risk-Medium | #FFC107（黄） | Mediumリスク表示 |
| Risk-Low | #28A745（緑） | Lowリスク表示 |

#### タイポグラフィ

- タイトル: Arial Black 36pt / ネイビー
- サブタイトル: Arial 24pt / ティール
- 本文: Arial 16pt / ダークグレー
- キャプション: Arial 12pt / グレー
- 数値ハイライト: Arial Black 48-72pt / アクセントカラー

### 13.5 PDFレポート仕様（20-30ページ標準）

| ページ | セクション | 内容 |
|-------|----------|------|
| 1 | 表紙 | レポートタイトル、対象期間、作成者、機密区分 |
| 2 | 目次 | 自動生成目次（ページ番号付き） |
| 3-4 | エグゼクティブサマリー | 主要発見事項、リスク評価、推奨アクション要約 |
| 5-7 | 分析概要 | 分析対象、手法、データ範囲、前提条件 |
| 8-12 | リスク分析結果 | ルール違反詳細、ML異常検知結果、リスクスコア分布 |
| 13-16 | 財務指標分析 | 回転期間、流動性、収益性の詳細分析と推移グラフ |
| 17-20 | 発見事項詳細 | 各洞察の詳細説明、根拠データ、関連仕訳一覧 |
| 21-23 | 提言・改善計画 | 優先度付き提言、実施スケジュール案、期待効果 |
| 24- | Appendix | 詳細データテーブル、用語集、分析手法説明 |

### 13.6 レポート生成パラメータ

| パラメータ | 型 | 説明 |
|----------|---|------|
| report_type | ENUM | executive_ppt / audit_pdf / risk_alert / audit_workpaper |
| period_start | DATE | 分析対象期間（開始） |
| period_end | DATE | 分析対象期間（終了） |
| comparison_period | ENUM | 前月 / 前年同期 / カスタム |
| focus_areas | ARRAY | 重点分析領域（勘定、部門、リスクカテゴリ） |
| insight_count | INTEGER | 掲載する洞察の最大数 |
| include_appendix | BOOLEAN | 詳細Appendixを含めるか |
| language | ENUM | ja / en（将来対応） |
| branding | OBJECT | 会社ロゴ、カラースキーム、フォント設定 |

### 13.7 レスポンス時間目標

| 処理 | 目標 | 最大許容 |
|-----|------|---------|
| 洞察生成（10件） | 30秒 | 60秒 |
| PPT生成（10スライド） | 20秒 | 45秒 |
| PDF生成（30ページ） | 30秒 | 60秒 |
| グラフ生成（1枚） | 2秒 | 5秒 |

---

## 14. データモデル設計

### 14.1 主要テーブル構成

| テーブル名 | 説明 | AICPAマッピング |
|----------|------|----------------|
| journal_entries | 仕訳明細データ | GL_Detail |
| chart_of_accounts | 勘定科目マスタ | Chart_Of_Accounts |
| trial_balance | 試算表データ | Trial_Balance |
| fiscal_periods | 会計期間マスタ | （拡張） |
| users | ユーザーマスタ | User_Listing |
| segments | セグメントマスタ | Segment_Listing |
| journal_notes | 仕訳メモ・タグ | （独自拡張） |
| risk_scores | リスクスコア結果 | （独自拡張） |
| insights | 洞察テーブル | （独自拡張） |
| reports | レポート管理テーブル | （独自拡張） |
| **analysis_sessions** | **分析セッション状態** | **（独自拡張）** |

### 14.2 journal_entries（仕訳データ）

| カラム名 | 型 | NULL | 説明 |
|---------|---|------|------|
| journal_id | VARCHAR(50) | NOT NULL, PK | 仕訳ID |
| posting_date | DATE | NOT NULL | 転記日 |
| entry_datetime | TIMESTAMP | NOT NULL | 起票日時 |
| account_code | VARCHAR(20) | NOT NULL | 勘定科目コード |
| account_name | VARCHAR(100) | NOT NULL | 勘定科目名 |
| debit_amount | DECIMAL(18,2) | NULL | 借方金額 |
| credit_amount | DECIMAL(18,2) | NULL | 貸方金額 |
| description | TEXT | NULL | 摘要 |
| created_by | VARCHAR(50) | NULL | 起票者ID |
| approved_by | VARCHAR(50) | NULL | 承認者ID |
| department_code | VARCHAR(20) | NULL | 部門コード |
| source_system | VARCHAR(30) | NULL | ソースシステム |

### 14.3 analysis_sessions（分析セッション状態）

| カラム名 | 型 | 説明 |
|---------|---|------|
| session_id | VARCHAR(36) | セッションID（UUID） |
| started_at | TIMESTAMP | 開始日時 |
| completed_at | TIMESTAMP | 完了日時 |
| current_phase | VARCHAR(50) | 現在のフェーズ |
| analysis_plan | JSON | 分析計画 |
| findings | JSON | 発見事項リスト |
| visited_views | JSON | 訪問したビュー履歴 |
| applied_filters | JSON | 適用したフィルタ履歴 |
| verification_results | JSON | 検証結果 |
| false_positives | JSON | 誤検知リスト |

### 14.4 インデックス設計

- PRIMARY KEY: journal_id
- INDEX: posting_date（パーティションキー候補）
- INDEX: account_code
- INDEX: created_by
- COMPOSITE INDEX: (posting_date, account_code)

---

## 15. 非機能要件

### 15.1 性能要件

| 項目 | 要件 |
|-----|------|
| 対応データ量 | 年間仕訳件数 1,000万件 × 3期以上 |
| 同時接続数 | 10ユーザー（スタンドアロン版） |
| バッチ処理時間 | 100万件の全処理で30分以内 |
| インポート処理 | 100万件を10分以内 |
| フィルタ応答時間 | 200ms以下（事前集計活用） |
| Dashboard API応答 | 200ms以下 |
| レポート生成 | PPT 10スライド: 45秒以内、PDF 30ページ: 60秒以内 |
| ストレージ | 生データの3倍程度（集計・インデックス含む） |

### 15.2 自律分析性能要件

| 項目 | 要件 |
|-----|------|
| 1回の分析サイクル | 30秒以内（目標） |
| 全体分析時間 | 5-30分（データ量による） |
| 同時エージェント数 | 3-5（リソース考慮） |
| エージェント間通信 | 100ms以下 |

### 15.3 セキュリティ要件

- データはすべてローカル保存（クラウド送信なし）
- LLM APIへの送信データは匿名化/マスキング処理
- データベース暗号化（AES-256）
- 監査ログの記録（操作履歴、アクセス履歴）

### 15.4 監査証跡要件

- 全エージェント操作のログ記録
- 判断理由の記録
- 発見事項と根拠データの紐付け
- レポート生成プロセスの記録
- セッション履歴の長期保存

### 15.5 可用性・運用要件

- オフライン動作対応（LLM API接続時のみオンライン必要）
- 自動バックアップ機能（日次）
- ログローテーション（30日保持）

### 15.6 エラーハンドリング

- API呼び出し失敗時のリトライ（最大3回）
- エージェントのスタック検出と回復
- 無限ループ防止（最大反復回数）
- タイムアウト処理（セッション単位）

### 15.7 AICPA準拠

- GL Standard Level 1フィールド100%対応

---

## 16. 技術スタック

### 16.1 フロントエンド

| カテゴリ | 技術 | バージョン |
|---------|------|----------|
| ランタイム | Electron | 28.x |
| UIフレームワーク | React | 18.x |
| 状態管理 | Zustand | 4.x |
| チャートライブラリ | Recharts / D3.js / Nivo | 各最新版 |
| データグリッド | AG Grid | 31.x |
| スタイリング | TailwindCSS | 3.x |

### 16.2 バックエンド

| カテゴリ | 技術 | バージョン |
|---------|------|----------|
| 言語 | Python | 3.11+ |
| API | FastAPI | 0.109+ |
| データ処理 | Polars | 0.20+ |
| 機械学習 | scikit-learn / PyOD | 1.4+ / 1.1+ |
| エージェント | LangGraph | 0.0.40+ |
| LLM | マルチクラウド対応（設定で選択） | 下記参照 |

### 16.3 データベース

| 用途 | 技術 | 備考 |
|-----|------|------|
| 仕訳・集計データ | DuckDB | OLAP特化、高速集計 |
| メタデータ・ルール | SQLite | 設定、ルール定義等 |
| キャッシュ | Parquet (ファイル) | 集計結果キャッシュ |

### 16.4 レポート生成

| カテゴリ | 技術 | 用途 |
|---------|------|------|
| PPT生成 | pptxgenjs | スライド生成、グラフ埋め込み |
| PDF生成 | ReportLab | PDF作成、表・グラフ挿入 |
| テンプレートエンジン | Jinja2 | 動的コンテンツ生成 |
| グラフ画像化 | Matplotlib / Plotly | PNG/SVG出力 |
| 洞察生成LLM | マルチクラウド対応 | テキスト生成、要約（下記参照） |

### 16.5 配布形式

- Windows: インストーラー (.exe) または ポータブル版 (.zip)
- macOS: DMG パッケージ
- Python環境不要（PyInstallerでバンドル）

### 16.6 LLMプロバイダー設定（マルチクラウド対応）

設定画面からLLMプロバイダーを選択可能。企業のクラウド戦略・契約状況に応じて柔軟に切り替え可能。ローカルLLM（Ollama）による開発・テスト環境もサポート。

#### 16.6.1 対応プロバイダー一覧（8プロバイダー）

| プロバイダー | 代表モデル | SDK/API | 用途 |
| ------------ | ---------- | ------- | ---- |
| **AWS Bedrock** | Claude Opus 4.6, Nova Premier | boto3 / Bedrock Runtime | **エンタープライズ推奨** |
| **Azure AI Foundry** | GPT-5.2, Claude Opus 4.6 | azure-openai SDK | 最新GPT-5シリーズ + Claude |
| **GCP Vertex AI** | Gemini 3 Pro, Gemini 2.5 Flash Lite | google-cloud-aiplatform | **コスト重視** |
| **Anthropic Direct** | Claude Opus 4.6, Sonnet 4.5, Haiku 4.5 | anthropic SDK | 最新モデル即時利用 |
| **OpenAI Direct** | GPT-5.2, GPT-5, o3-pro, o4-mini | openai SDK | GPT-5直接利用 |
| **Google AI Studio** | Gemini 3 Flash, Gemini 2.5 Pro | google-genai SDK | 個人/PoC |
| **Azure OpenAI（レガシー）** | GPT-4o | azure-openai SDK | 既存Azure環境 |
| **Ollama（ローカル）** | Phi-4, DeepSeek R1, Llama 3.3 | REST API (httpx) | **開発・テスト用** |

#### 16.6.2 設定項目

| 設定項目 | 型 | 説明 |
|---------|---|------|
| provider | ENUM | bedrock / azure_foundry / vertex_ai / anthropic / openai / google / azure / ollama |
| model_id | STRING | 使用するモデルID（例: claude-opus-4-6, gemini-3-pro, phi4） |
| region | STRING | リージョン（例: us-east-1, global）※Gemini 3.0はglobalのみ |
| api_key / credentials | SECRET | 認証情報（環境変数または設定ファイル） |
| max_tokens | INTEGER | 最大出力トークン数（デフォルト: 4096） |
| temperature | FLOAT | 生成の多様性（デフォルト: 0.3） |
| timeout_seconds | INTEGER | タイムアウト（デフォルト: 60） |
| retry_count | INTEGER | リトライ回数（デフォルト: 3） |

#### 16.6.3 プロバイダー別設定例

**AWS Bedrock（推奨：既存AWS環境がある場合）**
```json
{
  "provider": "bedrock",
  "model_id": "us.anthropic.claude-opus-4-6-20260201-v1:0",
  "region": "us-east-1",
  "credentials": "IAM_ROLE or ACCESS_KEY"
}
```

**Azure AI Foundry（推奨：最新GPT-5を使う場合）**
```json
{
  "provider": "azure_foundry",
  "model_id": "gpt-5.2",
  "endpoint": "https://your-foundry.openai.azure.com/",
  "api_version": "2026-01-01",
  "credentials": "API_KEY"
}
```

**GCP Vertex AI（推奨：コスト重視の場合）**
```json
{
  "provider": "vertex_ai",
  "model_id": "gemini-3-flash-preview",
  "region": "global",
  "project_id": "your-project-id",
  "credentials": "SERVICE_ACCOUNT_JSON"
}
```

**Ollama（ローカル開発・テスト）**
```json
{
  "provider": "ollama",
  "model_id": "phi4",
  "base_url": "http://localhost:11434"
}
```

#### 16.6.4 フォールバック設定

プライマリプロバイダーが利用不可の場合のフォールバック先を設定可能。

| 設定項目 | 説明 |
|---------|------|
| fallback_enabled | フォールバック有効化（true/false） |
| fallback_provider | フォールバック先プロバイダー |
| fallback_threshold | フォールバック発動の失敗回数 |

#### 16.6.5 コスト・性能比較（参考・2026年2月時点）

| プロバイダー | 代表モデル | 入力(/1M tokens) | 出力(/1M tokens) | レイテンシ | 備考 |
|-------------|-----------|------------------|------------------|----------|------|
| AWS Bedrock | Claude Opus 4.6 | $15.00 | $75.00 | 低 | VPC内通信、監査ログ統合 |
| AWS Bedrock | Claude Haiku 4.5 | $0.80 | $4.00 | 非常に低 | 大量処理向け |
| Azure Foundry | GPT-5.2 | $10.00 | $30.00 | 中 | M365連携、コンプライアンス |
| Vertex AI | Gemini 2.5 Flash Lite | $0.15 | $0.60 | 非常に低 | **最低コスト** |
| Vertex AI | Gemini 3 Pro | $5.00 | $15.00 | 低 | BigQuery連携 |
| Anthropic Direct | Claude Opus 4.6 | $15.00 | $75.00 | 低 | 最新モデル即時利用 |
| OpenAI Direct | GPT-5.2 | $10.00 | $30.00 | 中 | 直接API利用 |
| Ollama | Phi-4 (ローカル) | 無料 | 無料 | ハード依存 | GPU推奨、開発用 |

※ 料金は2026年2月時点の参考値。実際の料金は各プロバイダーの最新情報を確認。

---

## 改訂履歴

| バージョン | 日付 | 変更内容 |
|----------|------|---------|
| 1.0 | 2026年2月 | 初版作成 |
| 2.0 | 2026年2月 | ルールベース75ルール、財務指標、8エージェント、11タブダッシュボード追加 |
| 3.0 | 2026年2月 | 洞察生成エンジン、PPT/PDF自動生成、9エージェント構成追加 |
| 4.0 | 2026年2月 | AICPA ADS準拠、会計期間管理、趨勢分析、メモ/タグ機能、85ルール追加 |
| **5.0** | **2026年2月** | **自律分析エージェント機能、Dashboard Interface Layer、10エージェント構成、Human-in-the-Loop、操作可視化UI、監査証跡強化** |

---

**— End of Document —**
