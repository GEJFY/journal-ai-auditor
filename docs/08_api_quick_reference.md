# JAIA API クイックリファレンス

本ドキュメントは、JAIAのAPIを素早く利用するためのリファレンスガイドです。
詳細な仕様は [04_api_design.md](04_api_design.md) を参照してください。

---

## 基本情報

| 項目 | 値 |
|------|-----|
| ベースURL | `http://localhost:8090/api/v1` |
| 認証 | 不要（ローカル実行） |
| Content-Type | `application/json` |
| 文字コード | UTF-8 |

---

## エンドポイント一覧

### システム

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/api/v1/health` | API健全性確認 |

### データインポート

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/import/upload` | ファイルアップロード |
| GET | `/api/v1/import/status/{import_id}` | インポート状況確認 |

### ダッシュボード

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/dashboard/summary` | サマリー情報 |
| GET | `/api/v1/dashboard/kpi` | KPI指標 |
| GET | `/api/v1/dashboard/benford` | Benford分析結果 |
| GET | `/api/v1/dashboard/timeseries` | 時系列データ |
| GET | `/api/v1/dashboard/risk-distribution` | リスク分布 |

### バッチ処理

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/batch/execute` | バッチ処理実行 |
| GET | `/api/v1/batch/rules` | ルール一覧 |
| GET | `/api/v1/batch/status/{batch_id}` | バッチ状況確認 |

### 分析

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/analysis/violations` | 違反仕訳一覧 |
| GET | `/api/v1/analysis/ml-anomalies` | ML異常検知結果 |
| GET | `/api/v1/analysis/benford-detail` | Benford詳細分析 |
| GET | `/api/v1/analysis/risk-details` | リスク詳細 |

### AIエージェント

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/v1/agents/analyze` | AI分析実行 |
| GET | `/api/v1/agents/sessions/{session_id}` | セッション状況 |
| POST | `/api/v1/agents/chat` | チャット送信 |

### レポート

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/v1/reports/templates` | テンプレート一覧 |
| POST | `/api/v1/reports/generate` | レポート生成 |
| POST | `/api/v1/reports/export/ppt` | PPTエクスポート |
| POST | `/api/v1/reports/export/pdf` | PDFエクスポート |

---

## 共通クエリパラメータ

| パラメータ | 型 | 説明 | 例 |
|-----------|---|------|-----|
| `fiscal_year` | integer | 会計年度 | `2024` |
| `period_start` | date | 期間開始日 | `2024-04-01` |
| `period_end` | date | 期間終了日 | `2025-03-31` |
| `risk_level` | string | リスクレベル | `Critical,High` |
| `limit` | integer | 取得件数上限 | `100` |
| `offset` | integer | オフセット | `0` |

---

## リクエスト例

### ヘルスチェック

```bash
curl http://localhost:8090/health
```

レスポンス:
```json
{
  "status": "healthy",
  "app": "JAIA",
  "version": "1.0.0"
}
```

### ダッシュボードサマリー取得

```bash
curl "http://localhost:8090/api/v1/dashboard/summary?fiscal_year=2024"
```

レスポンス:
```json
{
  "success": true,
  "data": {
    "total_entries": 150000,
    "total_amount": 5000000000,
    "risk_distribution": {
      "Critical": 45,
      "High": 342,
      "Medium": 2100,
      "Low": 147513
    }
  }
}
```

### KPI取得

```bash
curl "http://localhost:8090/api/v1/dashboard/kpi?fiscal_year=2024"
```

レスポンス:
```json
{
  "success": true,
  "data": {
    "total_entries": 150000,
    "total_amount": 5000000000,
    "critical_count": 45,
    "high_count": 342,
    "medium_count": 2100,
    "low_count": 147513
  }
}
```

### Benford分析取得

```bash
curl "http://localhost:8090/api/v1/dashboard/benford?fiscal_year=2024"
```

レスポンス:
```json
{
  "success": true,
  "data": {
    "first_digit": {
      "observed": [0.301, 0.176, 0.125, ...],
      "expected": [0.301, 0.176, 0.125, ...],
      "mad": 0.008,
      "conformity": "Close Conformity"
    }
  }
}
```

### 違反仕訳一覧取得

```bash
curl "http://localhost:8090/api/v1/analysis/violations?fiscal_year=2024&risk_level=Critical,High&limit=50"
```

### バッチ処理実行

```bash
curl -X POST "http://localhost:8090/api/v1/batch/execute" \
  -H "Content-Type: application/json" \
  -d '{"fiscal_year": 2024, "run_rules": true, "run_ml": true}'
```

### PPTレポートエクスポート

```bash
curl -X POST "http://localhost:8090/api/v1/reports/export/ppt" \
  -H "Content-Type: application/json" \
  -d '{
    "fiscal_year": 2024,
    "period_start": "2024-04-01",
    "period_end": "2024-06-30",
    "company_name": "株式会社サンプル"
  }' \
  --output report.pptx
```

### PDFレポートエクスポート

```bash
curl -X POST "http://localhost:8090/api/v1/reports/export/pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "fiscal_year": 2024,
    "period_start": "2024-04-01",
    "period_end": "2024-06-30"
  }' \
  --output report.pdf
```

---

## レスポンス形式

### 成功時

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "abc123",
    "timestamp": "2024-01-15T10:00:00Z",
    "processing_time_ms": 150
  }
}
```

### エラー時

```json
{
  "success": false,
  "error": {
    "error_code": "VALIDATION_ERROR",
    "message": "パラメータが不正です",
    "detail": { ... }
  },
  "meta": {
    "request_id": "abc123",
    "timestamp": "2024-01-15T10:00:00Z"
  }
}
```

---

## エラーコード

| コード | HTTPステータス | 説明 |
|--------|---------------|------|
| `VALIDATION_ERROR` | 400 | リクエスト検証エラー |
| `NOT_FOUND` | 404 | リソースが見つからない |
| `CONFLICT` | 409 | リソース競合 |
| `IMPORT_ERROR` | 422 | インポート処理失敗 |
| `ANALYSIS_ERROR` | 500 | 分析処理失敗 |
| `LLM_PROVIDER_ERROR` | 503 | LLMプロバイダーエラー |
| `INTERNAL_ERROR` | 500 | 内部エラー |

---

## リスクレベル定義

| レベル | スコア範囲 | 説明 |
|--------|----------|------|
| Critical | 80-100 | 即時対応が必要 |
| High | 60-79 | 優先的な確認が必要 |
| Medium | 40-59 | 通常の確認対象 |
| Low | 0-39 | 低リスク |

---

## 監査ルールカテゴリ

| カテゴリ | コード | ルール数 | 説明 |
|---------|--------|---------|------|
| 金額 | AMT | 12 | 金額に関する異常検出 |
| 時間 | TIM | 10 | 時間・日付に関する異常検出 |
| 勘定科目 | ACC | 10 | 勘定科目に関する異常検出 |
| 承認 | APR | 10 | 承認フローに関する異常検出 |
| ML異常 | ML | 6 | 機械学習による異常検出 |
| Benford | BEN | 10 | Benfordの法則による分析 |

---

## Swagger UI

開発環境では Swagger UI が利用可能です:

- Swagger UI: `http://localhost:8090/docs`
- ReDoc: `http://localhost:8090/redoc`
- OpenAPI JSON: `http://localhost:8090/openapi.json`

※ 本番環境（`debug=false`）ではセキュリティ上の理由で無効化されます。

---

## Python クライアント例

```python
import httpx

BASE_URL = "http://localhost:8090/api/v1"

async def get_dashboard_summary(fiscal_year: int):
    """ダッシュボードサマリーを取得"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/dashboard/summary",
            params={"fiscal_year": fiscal_year}
        )
        return response.json()

async def get_violations(fiscal_year: int, risk_level: str = "Critical,High"):
    """違反仕訳を取得"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/analysis/violations",
            params={
                "fiscal_year": fiscal_year,
                "risk_level": risk_level
            }
        )
        return response.json()

async def export_ppt_report(fiscal_year: int, output_path: str):
    """PPTレポートをエクスポート"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/reports/export/ppt",
            json={"fiscal_year": fiscal_year}
        )
        with open(output_path, "wb") as f:
            f.write(response.content)
```

---

## TypeScript クライアント例

```typescript
const BASE_URL = "http://localhost:8090/api/v1";

interface DashboardSummary {
  total_entries: number;
  total_amount: number;
  risk_distribution: Record<string, number>;
}

async function getDashboardSummary(fiscalYear: number): Promise<DashboardSummary> {
  const response = await fetch(
    `${BASE_URL}/dashboard/summary?fiscal_year=${fiscalYear}`
  );
  const data = await response.json();
  return data.data;
}

async function getViolations(
  fiscalYear: number,
  riskLevel: string = "Critical,High"
): Promise<Violation[]> {
  const response = await fetch(
    `${BASE_URL}/analysis/violations?fiscal_year=${fiscalYear}&risk_level=${riskLevel}`
  );
  const data = await response.json();
  return data.data.violations;
}
```
