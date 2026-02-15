# JAIA API設計書

## 1. API概要

### 1.1 基本仕様

| 項目 | 仕様 |
|------|------|
| ベースURL | `http://localhost:8090/api/v1` |
| 認証 | ローカル実行のため不要（将来：JWT） |
| Content-Type | `application/json` |
| 文字コード | UTF-8 |
| タイムゾーン | UTC (レスポンスでは`+00:00`表記) |

### 1.2 レスポンス形式

```typescript
// 成功時
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2026-02-01T12:00:00Z",
    "request_id": "uuid",
    "processing_time_ms": 150
  }
}

// エラー時
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "期間の指定が不正です",
    "details": { ... }
  },
  "meta": { ... }
}
```

### 1.3 共通クエリパラメータ

| パラメータ | 型 | 説明 |
|-----------|---|------|
| `period_start` | date | 期間開始日 (YYYY-MM-DD) |
| `period_end` | date | 期間終了日 (YYYY-MM-DD) |
| `fiscal_year` | string | 会計年度 (YYYY) |
| `accounting_period` | int | 会計期間 (1-14) |
| `accounts` | string[] | 勘定科目コードリスト |
| `fs_captions` | string[] | 表示科目リスト |
| `risk_levels` | string[] | リスクレベルリスト |
| `limit` | int | 取得件数上限 (default: 100) |
| `offset` | int | オフセット (default: 0) |

---

## 2. データインポートAPI

### 2.1 ファイル検証

```
POST /api/v1/import/validate
```

**リクエスト**
```json
{
  "file_path": "/path/to/file.csv",
  "file_type": "csv",
  "data_type": "gl_detail",
  "encoding": "utf-8",
  "options": {
    "date_format": "%Y-%m-%d",
    "decimal_separator": "."
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "is_valid": false,
    "total_rows": 150000,
    "valid_rows": 149500,
    "error_count": 300,
    "warning_count": 200,
    "validation_results": [
      {
        "check_id": "VAL_001",
        "check_name": "必須フィールド確認",
        "status": "passed",
        "affected_rows": 0
      },
      {
        "check_id": "VAL_004",
        "check_name": "借方/貸方バランス",
        "status": "failed",
        "affected_rows": 300,
        "sample_errors": [
          {"row": 1234, "je_number": "JE-2024-001", "message": "借方貸方不一致: 差額 1,000円"}
        ]
      }
    ],
    "column_mapping": {
      "detected": ["JE_Number", "Amount", "Effective_Date", ...],
      "required": ["JE_Number", "JE_Line_Number", "Fiscal_Year", ...],
      "missing": ["Currency_Code"],
      "suggestions": [
        {"source": "仕訳番号", "target": "JE_Number", "confidence": 0.95}
      ]
    },
    "preview_rows": [
      {"JE_Number": "JE-2024-001", "Amount": 100000, ...}
    ]
  }
}
```

### 2.2 インポート実行

```
POST /api/v1/import/execute
```

**リクエスト**
```json
{
  "file_path": "/path/to/file.csv",
  "file_type": "csv",
  "data_type": "gl_detail",
  "column_mapping": {
    "仕訳番号": "JE_Number",
    "金額": "Amount"
  },
  "options": {
    "skip_errors": false,
    "run_aggregation": true,
    "run_scoring": true
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "import_id": "imp_abc123",
    "status": "completed",
    "records_imported": 149500,
    "records_skipped": 500,
    "processing_time_seconds": 45,
    "aggregation_status": "completed",
    "scoring_status": "completed"
  }
}
```

### 2.3 インポート状況確認

```
GET /api/v1/import/{import_id}/status
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "import_id": "imp_abc123",
    "status": "processing",
    "progress": 65,
    "current_step": "aggregation",
    "steps": [
      {"step": "validation", "status": "completed", "duration_ms": 5000},
      {"step": "import", "status": "completed", "duration_ms": 30000},
      {"step": "aggregation", "status": "in_progress", "progress": 50},
      {"step": "scoring", "status": "pending"}
    ]
  }
}
```

---

## 3. Dashboard Interface API

### 3.1 サマリータブ

```
GET /api/v1/dashboard/summary
```

**クエリパラメータ**
- `period_start`, `period_end`, `fiscal_year`, `accounts`, `risk_levels`

**レスポンス**
```json
{
  "success": true,
  "data": {
    "kpi": {
      "total_journals": 1200000,
      "total_amount": 5000000000,
      "critical_count": 45,
      "high_count": 342,
      "medium_count": 2100,
      "low_count": 1197513
    },
    "risk_distribution": [
      {"level": "Critical", "count": 45, "percentage": 0.004},
      {"level": "High", "count": 342, "percentage": 0.029},
      {"level": "Medium", "count": 2100, "percentage": 0.175},
      {"level": "Low", "count": 1197513, "percentage": 99.79}
    ],
    "monthly_trend": [
      {
        "month": "2024-01",
        "journal_count": 95000,
        "total_amount": 400000000,
        "risk_count": 180
      }
    ],
    "top_accounts": [
      {
        "gl_account_number": "1101",
        "gl_account_name": "売掛金",
        "total_amount": 850000000,
        "journal_count": 45000
      }
    ],
    "recent_alerts": [
      {
        "journal_id": "JE-2024-12345_1",
        "risk_level": "Critical",
        "risk_score": 92,
        "top_factor": "自己承認 + 重要性基準超過",
        "amount": 150000000,
        "effective_date": "2024-01-15"
      }
    ],
    "rule_heatmap": {
      "categories": ["金額", "時間", "勘定", "承認", "摘要", "パターン", "趨勢"],
      "months": ["2024-01", "2024-02", "2024-03"],
      "data": [
        [15, 20, 12],
        [8, 5, 10]
      ]
    }
  }
}
```

### 3.2 時系列分析タブ

```
GET /api/v1/dashboard/timeseries
```

**クエリパラメータ**
- 共通パラメータ + `granularity` (daily|monthly)

**レスポンス**
```json
{
  "success": true,
  "data": {
    "daily_trend": [
      {
        "date": "2024-01-01",
        "total_amount": 15000000,
        "journal_count": 3500
      }
    ],
    "monthly_comparison": [
      {
        "month": 1,
        "current_year": 400000000,
        "prior_year": 350000000,
        "variance_rate": 0.143
      }
    ],
    "yoy_waterfall": {
      "start_value": 350000000,
      "end_value": 400000000,
      "changes": [
        {"category": "売上増加", "value": 60000000},
        {"category": "費用増加", "value": -10000000}
      ]
    },
    "weekday_hour_heatmap": {
      "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
      "hours": [0, 1, 2, ..., 23],
      "data": [[10, 5, 2, ...], ...]
    },
    "seasonality_radar": {
      "months": ["Jan", "Feb", ..., "Dec"],
      "current_year": [100, 95, 105, ...],
      "prior_year": [90, 88, 98, ...],
      "average": [95, 92, 102, ...]
    }
  }
}
```

### 3.3 勘定科目分析タブ

```
GET /api/v1/dashboard/accounts
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "treemap": {
      "name": "root",
      "children": [
        {
          "name": "Asset",
          "children": [
            {
              "name": "売掛金",
              "gl_account_number": "1101",
              "value": 850000000,
              "risk_score": 45
            }
          ]
        }
      ]
    },
    "account_daily": {
      "account": "1101",
      "data": [
        {
          "date": "2024-01-01",
          "amount": 15000000,
          "anomaly_score": 0.2
        }
      ],
      "anomaly_points": [
        {"date": "2024-01-15", "amount": 50000000, "anomaly_score": 0.85}
      ]
    },
    "account_flow_chord": {
      "nodes": ["売掛金", "売上高", "現金", "仕入高"],
      "links": [
        {"source": 0, "target": 1, "value": 500000000},
        {"source": 2, "target": 0, "value": 450000000}
      ]
    },
    "account_stats": [
      {
        "gl_account_number": "1101",
        "gl_account_name": "売掛金",
        "journal_count": 45000,
        "sum_amount": 850000000,
        "avg_amount": 18888,
        "std_amount": 5000,
        "risk_count": 150,
        "variance_mom": 0.15,
        "variance_yoy": 0.25
      }
    ]
  }
}
```

### 3.4 異常検知・リスクタブ

```
GET /api/v1/dashboard/risk
```

**クエリパラメータ**
- 共通パラメータ + `rule_categories`, `min_score`, `max_score`

**レスポンス**
```json
{
  "success": true,
  "data": {
    "score_histogram": {
      "bins": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
      "counts": [500000, 300000, 200000, 100000, 50000, 30000, 15000, 3000, 1500, 500]
    },
    "rule_ranking": [
      {
        "rule_id": "APR_001",
        "rule_name": "自己承認",
        "category": "承認",
        "hit_count": 342,
        "total_amount": 5000000000
      }
    ],
    "high_risk_journals": [
      {
        "journal_id": "JE-2024-12345_1",
        "je_number": "JE-2024-12345",
        "effective_date": "2024-01-15",
        "gl_account_number": "1101",
        "gl_account_name": "売掛金",
        "amount": 150000000,
        "description": "決算調整",
        "entered_by": "user001",
        "approved_by": "user001",
        "integrated_risk_score": 92,
        "risk_level": "Critical",
        "rule_violations": ["APR_001", "AMT_001", "DSC_002"],
        "top_risk_factors": ["自己承認", "重要性基準超過", "調整仕訳"]
      }
    ],
    "risk_trend": [
      {
        "month": "2024-01",
        "critical": 5,
        "high": 30,
        "medium": 180,
        "low": 94785
      }
    ],
    "ml_scatter": {
      "points": [
        {
          "journal_id": "JE-2024-12345_1",
          "rule_score": 65,
          "ml_score": 0.85,
          "risk_level": "Critical"
        }
      ]
    }
  }
}
```

### 3.5 ドリルダウン

```
GET /api/v1/dashboard/drilldown/{element_type}/{element_id}
```

**パラメータ**
- `element_type`: account | month | rule | risk_level
- `element_id`: 勘定コード | 月 | ルールID | リスクレベル

**レスポンス**
```json
{
  "success": true,
  "data": {
    "element_info": {
      "type": "account",
      "id": "1101",
      "name": "売掛金"
    },
    "summary": {
      "journal_count": 45000,
      "total_amount": 850000000,
      "risk_breakdown": {
        "critical": 3,
        "high": 25,
        "medium": 122,
        "low": 44850
      }
    },
    "journals": [
      {
        "journal_id": "JE-2024-12345_1",
        "je_number": "JE-2024-12345",
        "effective_date": "2024-01-15",
        "amount": 150000000,
        "description": "...",
        "risk_score": 92
      }
    ],
    "related_charts": [
      {
        "chart_type": "line",
        "title": "売掛金月次推移",
        "data": [...]
      }
    ]
  }
}
```

### 3.6 仕訳検索

```
POST /api/v1/dashboard/search/journals
```

**リクエスト**
```json
{
  "filters": {
    "period": {"start": "2024-01-01", "end": "2024-03-31"},
    "accounts": ["1101", "1102"],
    "amount_range": {"min": 1000000, "max": null},
    "risk_levels": ["Critical", "High"],
    "entered_by": ["user001"],
    "description_keyword": "調整",
    "rule_violations": ["APR_001"]
  },
  "sort": {"field": "integrated_risk_score", "order": "desc"},
  "pagination": {"limit": 50, "offset": 0}
}
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "total_count": 342,
    "journals": [
      {
        "journal_id": "JE-2024-12345_1",
        "je_number": "JE-2024-12345",
        "je_line_number": 1,
        "fiscal_year": "2024",
        "accounting_period": 1,
        "effective_date": "2024-01-15",
        "entry_date": "2024-01-15",
        "gl_account_number": "1101",
        "gl_account_name": "売掛金",
        "amount": 150000000,
        "debit_amount": 150000000,
        "credit_amount": 0,
        "je_line_description": "決算調整",
        "entered_by": "user001",
        "approved_by": "user001",
        "source": "MANUAL",
        "integrated_risk_score": 92,
        "risk_level": "Critical",
        "rule_violations": [
          {"rule_id": "APR_001", "score": 40, "description": "自己承認"}
        ],
        "tags": ["要確認"],
        "notes_count": 2
      }
    ]
  }
}
```

### 3.7 仕訳詳細

```
GET /api/v1/dashboard/journals/{journal_id}
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "journal": {
      "journal_id": "JE-2024-12345_1",
      "je_number": "JE-2024-12345",
      "je_line_number": 1,
      "fiscal_year": "2024",
      "accounting_period": 1,
      "effective_date": "2024-01-15",
      "entry_date": "2024-01-15",
      "gl_account_number": "1101",
      "gl_account_name": "売掛金",
      "fs_caption": "売掛金",
      "account_type": "Asset",
      "amount": 150000000,
      "debit_amount": 150000000,
      "credit_amount": 0,
      "je_line_description": "決算調整",
      "je_header_description": "月次決算調整仕訳",
      "entered_by": "user001",
      "entered_by_name": "山田太郎",
      "approved_by": "user001",
      "approved_by_name": "山田太郎",
      "approved_date": "2024-01-15",
      "source": "MANUAL",
      "business_unit": "本社",
      "document_number": "DOC-2024-001"
    },
    "risk_detail": {
      "integrated_risk_score": 92,
      "risk_level": "Critical",
      "rule_risk_score": 85,
      "ml_risk_score": 0.78,
      "rule_violations": [
        {
          "rule_id": "APR_001",
          "rule_name": "自己承認",
          "category": "承認",
          "severity": "Critical",
          "score": 40,
          "description": "起票者と承認者が同一",
          "details": {"entered_by": "user001", "approved_by": "user001"}
        },
        {
          "rule_id": "AMT_001",
          "rule_name": "重要性基準超過",
          "category": "金額",
          "severity": "Critical",
          "score": 40,
          "description": "金額が重要性基準値(1億円)を超過",
          "details": {"amount": 150000000, "threshold": 100000000}
        }
      ],
      "ml_scores": {
        "isolation_forest": 0.82,
        "lof": 0.75,
        "one_class_svm": 0.79,
        "autoencoder": 0.78,
        "benford": 0.65
      }
    },
    "related_journals": [
      {
        "journal_id": "JE-2024-12345_2",
        "relationship": "same_je",
        "amount": -150000000,
        "gl_account_name": "売上高"
      }
    ],
    "notes": [
      {
        "note_id": "note_001",
        "note_text": "確認が必要",
        "note_type": "Question",
        "created_by": "auditor001",
        "created_at": "2024-01-20T10:00:00Z"
      }
    ],
    "tags": ["要確認", "重要"]
  }
}
```

---

## 4. 分析API

### 4.1 自律分析開始

```
POST /api/v1/analysis/start
```

**リクエスト**
```json
{
  "period": {"start": "2024-01-01", "end": "2024-03-31"},
  "focus_areas": ["risk", "trend", "financial"],
  "options": {
    "deep_investigation": true,
    "generate_report": true,
    "report_types": ["ppt", "pdf"]
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_abc123",
    "status": "started",
    "stream_url": "/api/v1/analysis/sess_abc123/stream"
  }
}
```

### 4.2 分析進捗ストリーム (SSE)

```
GET /api/v1/analysis/{session_id}/stream
```

**SSEイベント**
```
event: phase_change
data: {"phase": "exploring", "progress": 10}

event: operation
data: {"agent": "Explorer", "action": "view_summary_tab", "details": {...}}

event: finding
data: {"finding_id": "f001", "severity": "Critical", "title": "売掛金異常増加", "summary": "..."}

event: human_input_required
data: {"question_id": "q001", "question": "売上急増の背景をご存知ですか？", "options": [...]}

event: progress
data: {"phase": "investigating", "progress": 45, "findings_count": 5}

event: complete
data: {"status": "completed", "total_findings": 12, "report_ready": true}
```

### 4.3 Human-in-the-Loop応答

```
POST /api/v1/analysis/{session_id}/respond
```

**リクエスト**
```json
{
  "question_id": "q001",
  "response": "大型案件の受注がありました",
  "additional_context": "2024年1月にA社との契約が成立"
}
```

### 4.4 分析停止

```
POST /api/v1/analysis/{session_id}/stop
```

### 4.5 分析結果取得

```
GET /api/v1/analysis/{session_id}/results
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "session_id": "sess_abc123",
    "status": "completed",
    "duration_seconds": 1200,
    "summary": {
      "total_findings": 12,
      "critical_findings": 2,
      "high_findings": 5,
      "medium_findings": 5,
      "charts_viewed": 45,
      "filters_applied": 23,
      "journals_tagged": 15
    },
    "findings": [
      {
        "finding_id": "f001",
        "category": "異常・リスク発見",
        "severity": "Critical",
        "title": "売掛金の異常増加",
        "summary": "売掛金が前年同期比+85%増加。回転期間も45日→68日に悪化。",
        "details": "...",
        "supporting_data": {...},
        "recommendations": ["..."],
        "related_journals": ["JE-2024-12345_1", "JE-2024-12346_1"]
      }
    ],
    "operation_log": [
      {
        "timestamp": "2024-01-20T10:23:45Z",
        "agent": "Explorer",
        "action": "view_summary_tab",
        "details": "サマリータブを確認"
      }
    ]
  }
}
```

---

## 5. レポートAPI

### 5.1 レポート生成

```
POST /api/v1/reports/generate
```

**リクエスト**
```json
{
  "session_id": "sess_abc123",
  "report_type": "executive_ppt",
  "options": {
    "period": {"start": "2024-01-01", "end": "2024-03-31"},
    "insight_count": 5,
    "include_appendix": true,
    "branding": {
      "company_name": "株式会社サンプル",
      "logo_path": "/path/to/logo.png"
    }
  }
}
```

**レスポンス**
```json
{
  "success": true,
  "data": {
    "report_id": "rpt_xyz789",
    "status": "generating",
    "estimated_time_seconds": 30
  }
}
```

### 5.2 レポート状況確認

```
GET /api/v1/reports/{report_id}/status
```

### 5.3 レポートダウンロード

```
GET /api/v1/reports/{report_id}/download
```

**レスポンス**: バイナリ (application/vnd.openxmlformats-officedocument.presentationml.presentation または application/pdf)

---

## 6. 仕訳メモ・タグAPI

### 6.1 メモ追加

```
POST /api/v1/journals/{journal_id}/notes
```

**リクエスト**
```json
{
  "note_text": "確認が必要",
  "note_type": "Question"
}
```

### 6.2 メモ一覧

```
GET /api/v1/journals/{journal_id}/notes
```

### 6.3 メモ解決

```
PATCH /api/v1/journals/notes/{note_id}
```

**リクエスト**
```json
{
  "is_resolved": true
}
```

### 6.4 タグ付与

```
POST /api/v1/journals/{journal_id}/tags
```

**リクエスト**
```json
{
  "tag_id": "tag_confirm"
}
```

### 6.5 タグ削除

```
DELETE /api/v1/journals/{journal_id}/tags/{tag_id}
```

### 6.6 タグ一覧

```
GET /api/v1/tags
```

---

## 7. 設定API

### 7.1 LLMプロバイダー設定

```
GET /api/v1/settings/llm
PUT /api/v1/settings/llm
```

**PUT リクエスト**
```json
{
  "provider": "aws_bedrock",
  "model_id": "anthropic.claude-v4-sonnet",
  "region": "us-east-1",
  "max_tokens": 4096,
  "temperature": 0.3,
  "fallback_enabled": true,
  "fallback_provider": "anthropic_direct"
}
```

### 7.2 ルール閾値設定

```
GET /api/v1/settings/rules
PUT /api/v1/settings/rules/{rule_id}
```

**PUT リクエスト**
```json
{
  "is_enabled": true,
  "parameters": {
    "threshold": 100000000
  }
}
```

### 7.3 フィルタプリセット

```
GET /api/v1/settings/filter-presets
POST /api/v1/settings/filter-presets
DELETE /api/v1/settings/filter-presets/{preset_id}
```

---

## 8. マスタAPI

### 8.1 会計期間

```
GET /api/v1/master/periods
POST /api/v1/master/periods
PUT /api/v1/master/periods/{period_id}
```

### 8.2 勘定科目

```
GET /api/v1/master/accounts
GET /api/v1/master/accounts/{account_code}
GET /api/v1/master/accounts/tree  # 階層構造
```

### 8.3 ユーザー

```
GET /api/v1/master/users
```

---

## 9. エラーコード一覧

| コード | HTTPステータス | 説明 |
|--------|---------------|------|
| `VALIDATION_ERROR` | 400 | リクエスト検証エラー |
| `NOT_FOUND` | 404 | リソースが見つからない |
| `CONFLICT` | 409 | リソース競合 |
| `IMPORT_FAILED` | 422 | インポート処理失敗 |
| `ANALYSIS_FAILED` | 500 | 分析処理失敗 |
| `LLM_ERROR` | 503 | LLMプロバイダーエラー |
| `INTERNAL_ERROR` | 500 | 内部エラー |

---

## 10. レート制限

| エンドポイント | 制限 |
|---------------|------|
| `/api/v1/import/*` | 10 req/min |
| `/api/v1/analysis/*` | 5 req/min |
| `/api/v1/reports/*` | 10 req/min |
| `/api/v1/dashboard/*` | 100 req/min |
| その他 | 200 req/min |

---

**次のステップ**: [05_development_plan.md](05_development_plan.md) で開発計画を策定します。
