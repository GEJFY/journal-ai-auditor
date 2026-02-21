# E2Eテスト拡充・パフォーマンス最適化・実データ検証プラン

## 概要
3つのPRに分けて実施する。

| PR | テーマ | サイズ |
|----|--------|--------|
| **#22** | パフォーマンス最適化 | M |
| **#23** | 実データ検証スクリプト | M |
| **#24** | E2Eテスト拡充（Playwright） | L |

依存関係: #22 → #23（最適化後に実データ検証） → #24（検証済みデータでE2E）

---

## PR #22: パフォーマンス最適化

### 22-1: SQLiteインデックス追加
- **ファイル**: `backend/app/db/sqlite.py` の `initialize_schema()`
- DuckDB側は `schema.py` に11個のインデックスが既に定義済み
- SQLiteの `audit_trail`, `llm_usage_log` にインデックスが欠落:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trail(timestamp DESC);
  CREATE INDEX IF NOT EXISTS idx_audit_trail_event_type ON audit_trail(event_type);
  CREATE INDEX IF NOT EXISTS idx_llm_usage_timestamp ON llm_usage_log(timestamp DESC);
  CREATE INDEX IF NOT EXISTS idx_llm_usage_provider ON llm_usage_log(provider);
  ```

### 22-2: ダッシュボードAPIクエリキャッシュ
- **ファイル**: `backend/app/api/endpoints/dashboard.py`
- `config.py` に `cache_ttl_seconds = 300` が定義済みだが未使用
- TTLCacheを dashboard にも適用:
  - `/summary`, `/kpi`, `/benford` のレスポンスをキャッシュ
  - キャッシュキー = `f"{endpoint}:{fiscal_year}:{period_from}:{period_to}"`
  - TTL = 300秒（config.cache_ttl_seconds）
  - `/api/v1/cache/invalidate` でキャッシュクリアAPI追加

### 22-3: `/risk` エンドポイント最適化
- **ファイル**: `backend/app/api/endpoints/dashboard.py`
- 現状: `get_risk_items()` が3回 + distribution で計4クエリ
- 改善: 1クエリに統合（UNION ALL + risk_level CASE）
  ```sql
  SELECT journal_id, gl_detail_id, risk_score, ...,
      CASE WHEN risk_score >= 60 THEN 'high'
           WHEN risk_score >= 40 THEN 'medium'
           ELSE 'low' END as risk_level
  FROM journal_entries
  WHERE fiscal_year = ? AND risk_score >= 20
  ORDER BY risk_score DESC
  LIMIT ?
  ```
  + 別クエリで distribution（集計のみなので軽量）

### 22-4: DuckDB接続プール化
- **ファイル**: `backend/app/db/duckdb.py`
- 現状: 毎回 `duckdb.connect()` → `close()` で接続コストが発生
- 改善: 永続接続 + 読み取り専用カーソル方式
  ```python
  class DuckDBManager:
      def __init__(self):
          self._conn = None   # 遅延初期化

      def _get_connection(self):
          if self._conn is None:
              self._conn = duckdb.connect(str(self.db_path))
              self._conn.execute("SET threads TO 4")
          return self._conn

      @contextmanager
      def connect(self):
          conn = self._get_connection()
          cursor = conn.cursor()
          try:
              yield cursor
          finally:
              cursor.close()
  ```
  - 書き込み操作（insert_df, initialize_schema）は既存の接続上で実行
  - テスト用にclose()メソッドも提供

### 22-5: パフォーマンステスト追加
- **ファイル**: `backend/tests/test_performance.py`（新規）
- ベンチマーク:
  - `/health` < 50ms
  - `/dashboard/summary` < 200ms（空DB）
  - `/dashboard/risk` < 500ms（空DB）
  - DuckDB接続プール再利用確認
  - キャッシュヒット/ミス確認

### テスト
- 既存テスト全パス確認
- 新規パフォーマンステスト追加

---

## PR #23: 実データ検証スクリプト

### 23-1: データインポートスクリプト
- **ファイル**: `scripts/import_sample_data.py`（新規）
- `sample_data/` の CSV を DuckDB にインポート:
  1. `01_chart_of_accounts.csv` → `chart_of_accounts`
  2. `02_department_master.csv` → `departments`
  3. `03_vendor_master.csv` → `vendors`
  4. `04_user_master.csv` → `users`
  5. `10_journal_entries.csv` → `journal_entries` (784,824行)
- Polarsで読み込み → DuckDBに挿入
- 進捗表示、エラーハンドリング
- 冪等性（DROP TABLE IF EXISTS → CREATE → INSERT）

### 23-2: データ検証テスト
- **ファイル**: `backend/tests/test_data_verification.py`（新規）
- `@pytest.mark.skipif(not HAS_SAMPLE_DATA)` で sample_data 未インポート時はスキップ
- 検証項目:
  1. **行数**: journal_entries が 784,824行
  2. **借方貸方バランス**: 各journal_id内で D合計 = C合計
  3. **勘定科目マスタ整合性**: journal_entries の gl_account_number が全て chart_of_accounts に存在
  4. **期間分布**: fiscal_year=2024 の全12期間にデータ存在
  5. **ダッシュボードAPI検証**: `/summary` の total_entries が実データと一致
  6. **リスク分析検証**: risk_score 分布が high/medium/low/minimal に分散
  7. **ベンフォード分布**: 第一桁分布がベンフォードの法則に近似（MAD < 0.02）
  8. **期間比較**: MoM/YoY で正しい勘定科目変動額を返す

### 23-3: 検証レポート出力
- テスト結果をJSON/テキストで出力
- CI連携: `pytest backend/tests/test_data_verification.py -v --tb=short`

---

## PR #24: E2Eテスト拡充（Playwright）

### 24-1: Playwright設定
- **ファイル**: `frontend/playwright.config.ts`（新規）
- テスト対象: `http://localhost:5290`（開発サーバー）
- バックエンドAPI: `http://localhost:8090`
- ブラウザ: Chromium のみ（Electron互換のため）
- スクリーンショット: テスト失敗時のみ

### 24-2: テストユーティリティ
- **ファイル**: `frontend/e2e/fixtures.ts`（新規）
- ページオブジェクトパターン:
  - `DashboardPage` — KPIカード、チャート確認
  - `ImportPage` — ファイルアップロード操作
  - `SettingsPage` — 設定変更操作
- モックAPI サーバー（`page.route()` でAPIレスポンスをインターセプト）

### 24-3: E2Eテストケース
- **ファイル**: `frontend/e2e/` ディレクトリ

| テストファイル | 内容 |
|----------------|------|
| `dashboard.spec.ts` | ダッシュボード表示、KPI確認、チャートレンダリング |
| `navigation.spec.ts` | サイドバーナビゲーション、全ページ遷移 |
| `import.spec.ts` | CSVファイルアップロードフロー（モックAPI） |
| `analysis.spec.ts` | AI分析チャット送信、SSEストリーミング表示 |
| `settings.spec.ts` | 設定保存、ルールトグル |
| `responsive.spec.ts` | モバイルビューポートでのレイアウト確認 |

### 24-4: CI統合
- `.github/workflows/ci.yml` に `e2e-test` ジョブ追加
- ステップ: vite build → preview → playwright test
- アーティファクト: スクリーンショット、トレース

---

## 検証（各PR共通）
1. Backend: `ruff check . && ruff format --check .`
2. Backend tests: `pytest tests/ -x`
3. Frontend: `eslint && prettier --check && tsc --noEmit && vitest run`
4. CI全チェックパス

## 見積もりサイズ
- PR #22: 5ファイル変更、パフォーマンステスト1本追加
- PR #23: スクリプト1本、検証テスト1本追加
- PR #24: Playwright設定 + E2Eテスト6本 + CI修正
