# JAIA クラウドリソース利用料見積もり

## 1. 概要

本ドキュメントは、JAIA（Journal entry AI Analyzer）システムのクラウドリソース利用料を3大クラウドプロバイダー（AWS、Azure、GCP）別に見積もるものである。

### 対象範囲

- **対象クラウド**: AWS (Bedrock)、Azure (AI Foundry)、GCP (Vertex AI)
- **環境区分**: Development（開発）、Staging（検証）、Production（本番）
- **想定ワークロード**:
  - 年間仕訳データ処理量: 100,000件/年
  - AI分析実行回数: 50回/月
  - 同時接続ユーザー数: 開発 1-2名、本番 5-10名

### 前提条件

- 料金は2026年2月時点の公開価格に基づく
- 為替レートは含まない（USD表記）
- サポートプラン・税金は含まない
- リザーブドインスタンス等の割引は適用前の価格

---

## 2. LLMプロバイダー別コスト比較

### 2.1 モデル別料金一覧

| プロバイダー | モデル | Input (per 1M tokens) | Output (per 1M tokens) | ティア |
|---|---|---|---|---|
| Anthropic | Claude Opus 4.6 | $15.00 | $75.00 | Premium |
| Anthropic | Claude Sonnet 4.5 | $3.00 | $15.00 | Balanced |
| Anthropic | Claude Haiku 4.5 | $0.80 | $4.00 | Fast |
| OpenAI | GPT-5.2 | $15.00 | $60.00 | Premium |
| OpenAI | GPT-5 | $5.00 | $30.00 | Premium |
| OpenAI | GPT-5 Mini | $1.50 | $6.00 | Balanced |
| OpenAI | GPT-5 Nano | $0.05 | $0.20 | Fast |
| OpenAI | o3-pro | $20.00 | $80.00 | Reasoning |
| OpenAI | o3 | $10.00 | $40.00 | Reasoning |
| OpenAI | o4-mini | $1.10 | $4.40 | Reasoning |
| Google | Gemini 3 Pro | $3.50 | $10.50 | Premium |
| Google | Gemini 3 Flash Preview | $0.50 | $1.50 | Fast |
| Google | Gemini 2.5 Pro | $2.50 | $10.00 | Balanced |
| Google | Gemini 2.5 Flash-Lite | $0.075 | $0.30 | Fast |
| AWS Bedrock | Claude Opus 4.6 | $15.00 | $75.00 | Premium |
| AWS Bedrock | Amazon Nova Premier | $2.50 | $10.00 | Premium |
| AWS Bedrock | Amazon Nova Pro | $0.80 | $3.20 | Balanced |
| AWS Bedrock | Amazon Nova Lite | $0.06 | $0.24 | Fast |
| AWS Bedrock | Amazon Nova Micro | $0.035 | $0.14 | Fast |
| Ollama (Local) | All Models | $0 (Free) | $0 (Free) | Free |

### 2.2 月次LLMコスト試算

JAIA における典型的な監査分析のトークン消費量:

- **1回の分析あたり**: 入力 ~10,000トークン、出力 ~5,000トークン
- **月間分析回数**: 50回
- **月間トークン合計**: 入力 500,000トークン、出力 250,000トークン

#### ティア別月次コスト

| ティア | 代表モデル | 入力コスト | 出力コスト | **月額合計** |
|---|---|---|---|---|
| **Premium** | Claude Opus 4.6 | $7.50 | $18.75 | **$26.25** |
| **Premium** | GPT-5.2 | $7.50 | $15.00 | **$22.50** |
| **Premium** | Gemini 3 Pro | $1.75 | $2.63 | **$4.38** |
| **Reasoning** | o3-pro | $10.00 | $20.00 | **$30.00** |
| **Reasoning** | o3 | $5.00 | $10.00 | **$15.00** |
| **Reasoning** | o4-mini | $0.55 | $1.10 | **$1.65** |
| **Balanced** | Claude Sonnet 4.5 | $1.50 | $3.75 | **$5.25** |
| **Balanced** | GPT-5 Mini | $0.75 | $1.50 | **$2.25** |
| **Balanced** | Gemini 2.5 Pro | $1.25 | $2.50 | **$3.75** |
| **Balanced** | Amazon Nova Pro | $0.40 | $0.80 | **$1.20** |
| **Fast** | Claude Haiku 4.5 | $0.40 | $1.00 | **$1.40** |
| **Fast** | GPT-5 Nano | $0.025 | $0.05 | **$0.075** |
| **Fast** | Gemini 3 Flash Preview | $0.25 | $0.38 | **$0.63** |
| **Fast** | Gemini 2.5 Flash-Lite | $0.038 | $0.075 | **$0.11** |
| **Fast** | Amazon Nova Lite | $0.03 | $0.06 | **$0.09** |
| **Fast** | Amazon Nova Micro | $0.018 | $0.035 | **$0.053** |
| **Free** | Ollama (Local) | $0 | $0 | **$0** |

> **注記**: 上記はAPI直接利用の場合の試算。実際にはリトライ、プロンプト調整、テスト実行等で1.5〜2倍のトークンを消費する可能性がある。

### 2.3 コストパフォーマンス分析

| 用途 | 推奨モデル | 理由 |
|---|---|---|
| 複雑な不正検知分析 | Claude Opus 4.6 / GPT-5.2 | 高精度な推論能力が必要 |
| 日常的な仕訳分析 | Claude Sonnet 4.5 / Gemini 2.5 Pro | コストと品質のバランス |
| バッチ処理・前処理 | Gemini 2.5 Flash-Lite / Nova Micro | 大量処理に最適 |
| 推論チェーン分析 | o3 / o4-mini | 多段階推論タスク向け |
| ローカル開発・テスト | Ollama (Phi-4 等) | コストゼロ |

---

## 3. AWS (Bedrock) 構成コスト

### 3.1 インフラストラクチャ構成

```
┌─────────────────────────────────────────────┐
│  AWS Cloud                                  │
│  ┌──────────┐  ┌──────────────────────────┐ │
│  │ Route 53 │→ │ ALB (Application LB)     │ │
│  └──────────┘  └──────────┬───────────────┘ │
│                           ↓                 │
│  ┌────────────────────────────────────────┐ │
│  │ ECS Fargate (Private Subnet)           │ │
│  │  ┌────────────┐  ┌────────────┐       │ │
│  │  │ Task 1     │  │ Task 2     │       │ │
│  │  │ 2vCPU/4GB  │  │ 2vCPU/4GB  │       │ │
│  │  └────────────┘  └────────────┘       │ │
│  └────────────────────────────────────────┘ │
│       ↓              ↓            ↓         │
│  ┌────────┐  ┌────────────┐  ┌──────────┐  │
│  │Bedrock │  │ S3 (10GB)  │  │Secrets   │  │
│  │ API    │  │ Reports    │  │Manager   │  │
│  └────────┘  └────────────┘  └──────────┘  │
│       ↓                                     │
│  ┌──────────────┐  ┌─────────────────────┐  │
│  │ CloudWatch   │  │ NAT Gateway         │  │
│  │ Logs/Metrics │  │ (Private→Internet)  │  │
│  └──────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 3.2 リソース別月額コスト

| リソース | 仕様 | 月額 (USD) | 備考 |
|---|---|---|---|
| **ECS Fargate** | 2 vCPU, 4GB RAM × 2タスク | ~$140 | 本番: 24/7稼働 |
| **ALB** | Application Load Balancer | ~$22 | 固定費 + LCU課金 |
| **ECR** | コンテナレジストリ | ~$1 | 500MB未満のイメージ |
| **S3** | Standard, 10GB | ~$2 | レポート保存用 |
| **Secrets Manager** | 5シークレット | ~$1 | API キー管理 |
| **CloudWatch** | Logs + Metrics + Alarms | ~$10 | 5GB ログ/月 |
| **NAT Gateway** | 1 AZ | ~$45 | データ処理 10GB/月 |
| **Route 53** | ホストゾーン 1個 | ~$1 | DNS管理 |
| **VPC** | VPC + サブネット | $0 | VPC自体は無料 |

### 3.3 環境別コスト

| 項目 | Development | Staging | Production |
|---|---|---|---|
| **Compute (ECS)** | $35 | $70 | $140+ |
| **Load Balancer** | $22 | $22 | $22 |
| **Storage (S3/ECR)** | $3 | $3 | $5 |
| **Networking (NAT)** | $0 | $45 | $45 |
| **Monitoring** | $5 | $10 | $20 |
| **Infrastructure 小計** | **$65** | **$150** | **$232+** |
| **LLM (Balanced層)** | $10 | $20 | $50 |
| **合計** | **$75** | **$170** | **$282+** |

#### 環境別構成の詳細

**Development（開発環境）**
- ECS Fargate: 1タスク（1 vCPU, 2GB）、業務時間のみ稼働（~12h/日）
- NAT Gateway なし（パブリックサブネット使用）
- CloudWatch: 基本ログのみ
- LLM: Amazon Nova Pro (Balanced) を主に使用

**Staging（検証環境）**
- ECS Fargate: 1タスク（2 vCPU, 4GB）、24/7稼働
- NAT Gateway: 1 AZ
- CloudWatch: ログ + 基本メトリクス
- LLM: 本番同等モデルで検証

**Production（本番環境）**
- ECS Fargate: 2タスク（2 vCPU, 4GB）、24/7稼働、Auto Scaling有効
- NAT Gateway: 1 AZ（マルチAZの場合は ×2 = $90）
- CloudWatch: フルモニタリング + アラーム
- LLM: Claude Sonnet 4.5 / Claude Opus 4.6（重要分析）

### 3.4 AWS コスト最適化オプション

| 最適化手法 | 削減効果 | 適用環境 |
|---|---|---|
| Fargate Spot | 最大70%削減 (Compute) | Development |
| スケジュールスケーリング | 約50%削減 (Compute) | Development/Staging |
| S3 Intelligent-Tiering | ~20%削減 (Storage) | Production |
| RI/Savings Plans | 最大30%削減 | Production (年契約) |
| CloudWatch ログ保持期間短縮 | ~30%削減 (Monitoring) | 全環境 |

---

## 4. Azure (AI Foundry) 構成コスト

### 4.1 インフラストラクチャ構成

```
┌─────────────────────────────────────────────┐
│  Azure Cloud                                │
│  ┌──────────┐  ┌──────────────────────────┐ │
│  │Azure DNS │→ │ Container Apps Ingress   │ │
│  └──────────┘  └──────────┬───────────────┘ │
│                           ↓                 │
│  ┌────────────────────────────────────────┐ │
│  │ Azure Container Apps                   │ │
│  │  ┌────────────┐  ┌────────────┐       │ │
│  │  │ Replica 1  │  │ Replica 2  │       │ │
│  │  │ 1vCPU/2GB  │  │ 1vCPU/2GB  │       │ │
│  │  └────────────┘  └────────────┘       │ │
│  └────────────────────────────────────────┘ │
│       ↓              ↓            ↓         │
│  ┌─────────────┐ ┌──────────┐ ┌──────────┐ │
│  │Azure OpenAI │ │ Storage  │ │Key Vault │ │
│  │AI Foundry   │ │ Account  │ │          │ │
│  │ (S0 Tier)   │ │ (LRS)    │ │          │ │
│  └─────────────┘ └──────────┘ └──────────┘ │
│       ↓                                     │
│  ┌──────────────┐  ┌─────────────────────┐  │
│  │Log Analytics │  │ Virtual Network     │  │
│  │ Workspace    │  │                     │  │
│  └──────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────┘
```

### 4.2 リソース別月額コスト

| リソース | 仕様 | 月額 (USD) | 備考 |
|---|---|---|---|
| **Container Apps** | 1 vCPU, 2GB RAM × 2レプリカ | ~$120 | 本番: 常時稼働 |
| **Azure OpenAI (S0)** | Standard デプロイ | ~$0 | 従量課金（トークン単位） |
| **Container Registry (Basic)** | Basic SKU | ~$5 | イメージ保存 |
| **Key Vault** | Standard | ~$1 | $0.03/10,000操作 |
| **Storage Account (LRS)** | LRS, 10GB | ~$2 | Blob Storage |
| **Log Analytics** | 5GB インジェスト/月 | ~$5 | ログ収集・分析 |
| **Virtual Network** | VNet + サブネット | ~$5 | VNet統合 |
| **Azure DNS** | ゾーン 1個 | ~$1 | DNS管理 |

### 4.3 環境別コスト

| 項目 | Development | Staging | Production |
|---|---|---|---|
| **Compute (Container Apps)** | $20 | $60 | $120+ |
| **Networking (VNet)** | $0 | $5 | $5 |
| **Storage** | $3 | $5 | $8 |
| **Monitoring** | $3 | $5 | $10 |
| **Security (Key Vault)** | $1 | $1 | $1 |
| **Infrastructure 小計** | **$27** | **$76** | **$144+** |
| **LLM (Balanced層)** | $10 | $20 | $50 |
| **合計** | **$37** | **$96** | **$194+** |

#### 環境別構成の詳細

**Development（開発環境）**
- Container Apps: 0-1レプリカ（Scale to Zero 対応）
- VNet統合なし（パブリックアクセス）
- Log Analytics: 最小構成
- LLM: GPT-5 Mini (Balanced) を主に使用

**Staging（検証環境）**
- Container Apps: 1レプリカ常時稼働
- VNet統合あり
- Log Analytics: 標準構成
- LLM: 本番同等モデルで検証

**Production（本番環境）**
- Container Apps: 2レプリカ常時稼働、Auto Scale有効（最大5）
- VNet統合 + プライベートエンドポイント
- Log Analytics: フル監視 + アラート
- LLM: GPT-5.2 / Claude Sonnet 4.5

### 4.4 Azure コスト最適化オプション

| 最適化手法 | 削減効果 | 適用環境 |
|---|---|---|
| Scale to Zero | 最大80%削減 (Compute) | Development |
| Azure Reservations | 最大30%削減 | Production (1年/3年) |
| Log Analytics コミットメント | ~15%削減 | Production (100GB/日以上) |
| Storage 階層管理 (Cool/Archive) | ~50%削減 (Storage) | Production |

---

## 5. GCP (Vertex AI) 構成コスト

### 5.1 インフラストラクチャ構成

```
┌─────────────────────────────────────────────┐
│  Google Cloud                               │
│  ┌──────────┐  ┌──────────────────────────┐ │
│  │Cloud DNS │→ │ Cloud Load Balancing     │ │
│  └──────────┘  └──────────┬───────────────┘ │
│                           ↓                 │
│  ┌────────────────────────────────────────┐ │
│  │ Cloud Run                              │ │
│  │  ┌────────────┐  ┌────────────┐       │ │
│  │  │ Instance 1 │  │ Instance 2 │       │ │
│  │  │ 2vCPU/2GB  │  │ 2vCPU/2GB  │       │ │
│  │  └────────────┘  └────────────┘       │ │
│  └────────────────────────────────────────┘ │
│       ↓              ↓            ↓         │
│  ┌──────────┐ ┌────────────┐ ┌───────────┐ │
│  │Vertex AI │ │ Cloud      │ │ Secret    │ │
│  │Gemini API│ │ Storage    │ │ Manager   │ │
│  └──────────┘ └────────────┘ └───────────┘ │
│       ↓                                     │
│  ┌──────────────┐  ┌─────────────────────┐  │
│  │Cloud Logging │  │ Serverless VPC      │  │
│  │& Monitoring  │  │ Access Connector    │  │
│  └──────────────┘  └─────────────────────┘  │
│                    ┌─────────────────────┐   │
│                    │ Cloud Armor (Prod)  │   │
│                    └─────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 5.2 リソース別月額コスト

| リソース | 仕様 | 月額 (USD) | 備考 |
|---|---|---|---|
| **Cloud Run** | 2 vCPU, 2GB RAM × min 2インスタンス | ~$100 | 本番: 最小2インスタンス |
| **Artifact Registry** | コンテナイメージ保存 | ~$1 | 500MB未満 |
| **Cloud Storage** | Standard, 10GB | ~$2 | レポート保存 |
| **Secret Manager** | 5シークレット | ~$1 | APIキー管理 |
| **VPC Connector** | Serverless VPC Access | ~$15 | f1-micro × 2 |
| **Cloud Armor** | Standard Tier | ~$5 | WAF (本番のみ) |
| **Cloud Logging** | 5GB/月 | ~$5 | $0.50/GiB |
| **Cloud Monitoring** | 基本メトリクス | $0 | 無料枠内 |

### 5.3 環境別コスト

| 項目 | Development | Staging | Production |
|---|---|---|---|
| **Compute (Cloud Run)** | $15 | $50 | $100+ |
| **Networking (VPC/Armor)** | $0 | $15 | $20 |
| **Storage** | $3 | $3 | $5 |
| **Monitoring** | $2 | $5 | $10 |
| **Security** | $0 | $1 | $6 |
| **Infrastructure 小計** | **$20** | **$74** | **$141+** |
| **LLM (Balanced層)** | $5 | $15 | $40 |
| **合計** | **$25** | **$89** | **$181+** |

#### 環境別構成の詳細

**Development（開発環境）**
- Cloud Run: 0-1インスタンス（Scale to Zero 活用）
- VPC Connector なし
- Cloud Armor なし
- LLM: Gemini 2.5 Flash-Lite (Fast) を主に使用 → 極めて低コスト

**Staging（検証環境）**
- Cloud Run: 1インスタンス（最小1）
- VPC Connector あり
- Cloud Armor なし
- LLM: 本番同等モデルで検証

**Production（本番環境）**
- Cloud Run: 2インスタンス（最小2、最大10）
- VPC Connector あり
- Cloud Armor 有効（WAF）
- LLM: Gemini 3 Pro / Gemini 2.5 Pro

### 5.4 GCP コスト最適化オプション

| 最適化手法 | 削減効果 | 適用環境 |
|---|---|---|
| Scale to Zero | 最大90%削減 (Compute) | Development |
| Cloud Run 最小インスタンス0 | 未使用時 $0 | Development/Staging |
| Committed Use Discounts | 最大30%削減 | Production (1年/3年) |
| Cloud Storage Nearline | ~50%削減 (Storage) | アーカイブ用 |
| 無料枠の活用 | Cloud Run 月200万リクエスト無料 | Development |

---

## 6. 3クラウド比較サマリー

### 6.1 環境別総コスト比較

| 環境 | AWS (Bedrock) | Azure (AI Foundry) | GCP (Vertex AI) |
|---|---|---|---|
| **Development** | $75 | $60 | $55 |
| **Staging** | $170 | $140 | $130 |
| **Production** | $282+ | $240+ | $220+ |
| **全環境合計** | **$527+** | **$440+** | **$405+** |

### 6.2 インフラのみ比較（LLM費用除く）

| 環境 | AWS | Azure | GCP |
|---|---|---|---|
| Development | $65 | $27 | $20 |
| Staging | $150 | $76 | $74 |
| Production | $232+ | $144+ | $141+ |

> **注記**: GCP Cloud Run は Scale to Zero に対応しており、開発環境のコストが最も低くなる。AWS は NAT Gateway の固定費が高い点に注意。

### 6.3 機能比較

| 特性 | AWS (Bedrock) | Azure (AI Foundry) | GCP (Vertex AI) |
|---|---|---|---|
| **対応LLMモデル** | Claude, Nova, Llama | GPT, Claude, Llama | Gemini, Claude, Llama |
| **Scale to Zero** | 非対応 (ECS) | 対応 (Container Apps) | 対応 (Cloud Run) |
| **マネージドLB** | ALB (有料) | 組み込み (無料) | 組み込み (無料) |
| **NAT費用** | 高い ($45/AZ) | VNet統合 ($5) | VPC Connector ($15) |
| **SLA (Compute)** | 99.99% | 99.95% | 99.95% |
| **日本リージョン** | 東京 (ap-northeast-1) | 東日本 (japaneast) | 東京 (asia-northeast1) |
| **Enterprise機能** | 最も充実 | AD連携に強い | データ分析に強い |

### 6.4 推奨構成

#### コスト最適構成
- **GCP (Cloud Run) + Gemini 3 Flash Preview**
- 月額: Development $25 / Production $181+
- 特徴: Scale to Zero で開発コスト最小、Gemini Flash の高コスパ
- 適用: スタートアップ、PoC、小規模チーム

#### バランス構成（推奨）
- **AWS (Bedrock) + Claude Sonnet 4.5**
- 月額: Development $75 / Production $282+
- 特徴: Enterprise 向けの堅牢なインフラ、Claude の高品質分析
- 適用: 中〜大規模企業、監査法人、本格運用

#### 最高精度構成
- **Azure (AI Foundry) + GPT-5.2**
- 月額: Development $60 / Production $240+
- 特徴: GPT-5.2 の最高精度、Azure AD との統合
- 適用: 大企業、厳格なコンプライアンス要件、Microsoft 365 環境

#### ハイブリッド構成（上級者向け）
- **GCP (Cloud Run) + 複数LLM切替**
  - バッチ処理: Gemini 2.5 Flash-Lite → $0.11/月
  - 日常分析: Claude Sonnet 4.5 → $5.25/月
  - 重要分析: Claude Opus 4.6 → $26.25/月（必要時のみ）
- 月額: LLM コスト $10〜$30（使い分けにより大幅削減）

---

## 7. 年間コスト見積もり

### 7.1 年間コスト予測（成長係数込み）

ワークロードの成長を年間20%と仮定した場合:

| 年度 | 成長係数 | AWS 年間 | Azure 年間 | GCP 年間 |
|---|---|---|---|---|
| **1年目** | 1.0x | $6,324 | $5,280 | $4,860 |
| **2年目** | 1.2x | $7,589 | $6,336 | $5,832 |
| **3年目** | 1.4x | $8,854 | $7,392 | $6,804 |

> **算出根拠**: 全環境合計の月額 × 12ヶ月 × 成長係数。Production 環境のスケールアップが主な増加要因。

### 7.2 環境別年間コスト

| 環境 | AWS 年間 | Azure 年間 | GCP 年間 |
|---|---|---|---|
| Development | $900 | $720 | $660 |
| Staging | $2,040 | $1,680 | $1,560 |
| Production | $3,384+ | $2,880+ | $2,640+ |
| **合計** | **$6,324+** | **$5,280+** | **$4,860+** |

### 7.3 LLMモデル選択による年間コスト変動

Production 環境のLLMコストのみ（50分析/月、年間600分析）:

| モデル戦略 | 月額LLM | 年間LLM | 備考 |
|---|---|---|---|
| Claude Opus 4.6 全件 | $26.25 | $315 | 最高精度だがコスト高 |
| Claude Sonnet 4.5 全件 | $5.25 | $63 | コスパ良好 |
| Gemini 2.5 Flash-Lite 全件 | $0.11 | $1.35 | 最安だが精度検証必要 |
| ハイブリッド（推奨） | ~$8 | ~$96 | 用途別に最適モデル選択 |

---

## 8. コスト最適化の推奨事項

### 8.1 コンピューティング最適化

| # | 推奨事項 | 削減効果 | 優先度 |
|---|---|---|---|
| 1 | **開発環境で Spot/Preemptible インスタンスを使用** | 最大70%削減 | 高 |
| 2 | **開発環境で Scale to Zero を活用**（GCP Cloud Run / Azure Container Apps） | 最大90%削減 | 高 |
| 3 | **業務時間外のスケジュールスケーリング** | 約50%削減 | 中 |
| 4 | **本番環境で RI / Committed Use Discounts を検討** | 最大30%削減 | 中（年契約） |

### 8.2 LLMコスト最適化

| # | 推奨事項 | 削減効果 | 優先度 |
|---|---|---|---|
| 1 | **バッチ処理には Gemini Flash / Nova Micro を使用** | 90%以上削減 | 高 |
| 2 | **複雑な分析のみ Opus / GPT-5.2 を使用** | 50〜70%削減 | 高 |
| 3 | **LLMレスポンスのキャッシュ機構を実装** | 30〜50%削減 | 高 |
| 4 | **分析あたりのトークンバジェットを設定** | 過剰消費防止 | 中 |
| 5 | **プロンプトの最適化（簡潔化）** | 20〜30%削減 | 中 |
| 6 | **Anthropic Prompt Caching の活用** | 最大90%削減（キャッシュヒット時） | 高 |

### 8.3 ストレージ・ネットワーク最適化

| # | 推奨事項 | 削減効果 | 優先度 |
|---|---|---|---|
| 1 | **AWS: 開発環境で NAT Gateway を除外** | $45/月削減 | 高 |
| 2 | **古いレポートをアーカイブ階層に移行** | 50〜80%削減 | 低 |
| 3 | **ログ保持期間を環境別に設定**（開発: 7日、本番: 90日） | 30%削減 | 中 |
| 4 | **コンテナイメージのサイズ最適化** | ECR/ACR コスト削減 | 低 |

### 8.4 モニタリング・アラート

コスト管理のために以下のアラートを設定すること:

- **月額予算アラート**: 予算の50%、80%、100%で通知
- **LLMトークン使用量アラート**: 日次上限の80%で通知
- **異常検知**: 前月比150%以上のコスト増加で通知
- **各クラウドのコスト管理ツール**:
  - AWS: Cost Explorer + Budgets
  - Azure: Cost Management + Advisor
  - GCP: Cloud Billing + Budgets & Alerts

---

## 9. ローカル開発コスト

### 9.1 Ollama によるローカルLLM実行

| 項目 | コスト | 備考 |
|---|---|---|
| **Ollama ソフトウェア** | $0（無料） | オープンソース |
| **LLMモデル利用** | $0（無料） | Phi-4, Llama, Mistral 等 |
| **API費用** | $0 | ローカル実行のため不要 |
| **クラウド依存** | なし | オフライン実行可能 |

### 9.2 推奨ハードウェア構成

| 構成 | GPU | VRAM | 対応モデル | 備考 |
|---|---|---|---|---|
| **最小構成** | CPU のみ | - | Phi-4 Mini (3.8B) | 低速だが動作可能 |
| **推奨構成** | NVIDIA RTX 4060 | 8GB | Phi-4 (14B) | 快適に動作 |
| **高性能構成** | NVIDIA RTX 4070 Ti | 12GB | Llama 3.3 (70B Q4) | 高精度モデル対応 |
| **プロ構成** | NVIDIA RTX 4090 | 24GB | Mixtral 8x22B | 最大級モデル対応 |

### 9.3 ローカル開発のメリット

- **コスト**: API費用ゼロ → 開発・テスト時のコスト完全排除
- **プライバシー**: データがローカルに留まる → 機密仕訳データの漏洩リスクなし
- **速度**: ネットワーク遅延なし → レスポンスが安定
- **制限なし**: レートリミット・トークン制限なし → 自由にテスト可能
- **オフライン**: インターネット接続不要 → 出張先・セキュアエリアでも利用可能

### 9.4 ローカル vs クラウドの使い分け

| 用途 | 推奨環境 | 理由 |
|---|---|---|
| プロンプト開発・調整 | ローカル (Ollama) | 試行回数が多く、コスト回避 |
| 単体テスト実行 | ローカル (Ollama) | CI/CD パイプラインの高速化 |
| 結合テスト | Staging (Cloud) | 本番同等環境での検証 |
| デモ・PoC | ローカル (Ollama) | セットアップが簡単 |
| 本番分析 | Production (Cloud) | 高精度モデルが必要 |

---

## 10. 注意事項

### 免責事項

- 本ドキュメントの価格は **2026年2月時点** の各クラウドプロバイダー公開価格に基づく
- 実際のコストは利用状況（リクエスト数、データ量、稼働時間等）により変動する
- **LLMの価格は急速に変化する傾向がある**（年間20〜50%の値下げが一般的）
- 各クラウドの無料枠・クレジットは考慮していない
- 消費税・サポートプラン費用は含まない
- 為替変動によるJPY換算額の変動は考慮していない

### 価格更新履歴

| 日付 | 更新内容 |
|---|---|
| 2026-02-14 | 初版作成。3クラウド + LLM 8プロバイダーの見積もり |

### 参考リンク

- [AWS Pricing Calculator](https://calculator.aws/)
- [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [Anthropic API Pricing](https://www.anthropic.com/pricing)
- [OpenAI API Pricing](https://openai.com/pricing)
- [Google AI Pricing](https://ai.google.dev/pricing)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Ollama](https://ollama.com/)
