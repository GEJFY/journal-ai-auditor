# Changelog

All notable changes to JAIA (Journal entry AI Analyzer) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-02-23

### Added
- Column mapping UI for journal entry import with auto-suggestion based on column name similarity
- Multi-step import flow: upload → column mapping → validation → import execution
- Analytics page with 3 tabs: department analysis, vendor concentration, account flow
- Report purpose selection (auditor vs management) for PPT/PDF exports
- Frontend Dockerfile (multi-stage: Node build → Nginx serve) for web deployment
- Docker Compose frontend service for production (`docker-compose up --build`)
- Optional full-Docker development mode (`--profile full`)
- Frontend `.dockerignore` for build context optimization
- AnalyticsPage tests and extended ImportPage tests for column mapping

### Changed
- DuckDB connection lifecycle: use module-level singleton and close on shutdown
- `docker-compose.yml` frontend service now builds from Dockerfile instead of mounting pre-built dist
- `Dockerfile.dev` limits `--reload` file watching to `app/` directory to prevent memory errors

### Fixed
- DuckDB file lock conflict on uvicorn reload (close connection during lifespan shutdown)
- Docker watchfiles `Cannot allocate memory` error with `--reload-dir app`
- FastAPI `regex` → `pattern` deprecation warnings in dashboard.py

## [0.2.1] - 2026-02-15

### Added
- SECURITY.md with vulnerability reporting guidelines and security checklist
- CHANGELOG.md following Keep a Changelog format
- Vite environment variable support for frontend API URL (`VITE_API_BASE`)
- Electron main process TypeScript compilation (`tsconfig.electron.json`)
- Startup settings validation with production warnings
- CORS origins configurable via environment variable (`CORS_ALLOWED_ORIGINS`)
- Frontend production environment configuration (`.env.production`)

### Changed
- Migrated from Azure OpenAI SDK to Azure AI Foundry SDK (`azure-ai-inference`)
- Unified port numbers: Backend 8090, Frontend 5290
- Enhanced nginx.conf with complete security headers (HSTS, CSP, Referrer-Policy, Permissions-Policy)
- CORS origins now loaded from environment variable instead of hardcoded values
- Updated all documentation with correct port references

### Fixed
- Removed hardcoded API keys from `test_azure_connection.py`
- Fixed TypeScript `ImportMeta.env` type definition for CI
- Fixed test coverage threshold for new UI components
- Fixed port assertion in `test_models.py`

### Security
- Added Strict-Transport-Security header to nginx
- Added Content-Security-Policy header to nginx
- Added Referrer-Policy and Permissions-Policy headers to nginx
- API documentation endpoints disabled in production mode
- Request size limit (100MB) added to nginx

## [0.2.0] - 2026-02-09

### Added
- Enterprise test coverage and comprehensive documentation
- Multi-cloud LLM support (8 providers: Anthropic, OpenAI, Google, Bedrock, Azure AI Foundry, Vertex AI, Azure OpenAI, Ollama)
- Cloud deployment guides (AWS, Azure, GCP)
- Terraform infrastructure-as-code for all cloud providers
- Docker containerization with docker-compose
- CI/CD pipeline with GitHub Actions
- Security middleware (rate limiting, IP blocking, suspicious pattern detection)
- CONTRIBUTING.md with development guidelines

### Changed
- Expanded LLM model catalog to latest 2026 models
- Improved error handling with structured JAIA exceptions

## [0.1.0] - 2026-02-02

### Added
- Initial release
- 58 audit rules across 6 categories (Amount, Time, Account, Approval, ML, Benford)
- 5 ML anomaly detection methods (Isolation Forest, LOF, One-Class SVM, Autoencoder, Ensemble)
- Benford's Law analysis (first/second digit, MAD conformity test)
- Risk scoring (0-100 integrated score)
- Report generation (PPT/PDF format)
- Electron + React frontend with dashboard
- FastAPI backend with DuckDB + SQLite
- LangGraph-based multi-agent system
- AICPA Audit Data Standards (GL_Detail) compliance
