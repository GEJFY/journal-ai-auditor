#!/usr/bin/env bash
# JAIA Database Backup Script
# DuckDB (jaia.duckdb) + SQLite (jaia_meta.db) のバックアップを実行
#
# 使用方法:
#   ./scripts/backup_db.sh                    # ローカルバックアップ
#   ./scripts/backup_db.sh --docker           # Docker volume からバックアップ
#   ./scripts/backup_db.sh --compress         # gzip 圧縮付き
#   ./scripts/backup_db.sh --retain 14        # 14日分保持（デフォルト: 30日）
#   ./scripts/backup_db.sh --backup-dir /path # バックアップ先指定

set -euo pipefail

# デフォルト設定
DATA_DIR="${DATA_DIR:-./data}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETAIN_DAYS="${RETAIN_DAYS:-30}"
COMPRESS=false
DOCKER_MODE=false
CONTAINER_NAME="jaia-backend"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)      DOCKER_MODE=true; shift ;;
        --compress)    COMPRESS=true; shift ;;
        --retain)      RETAIN_DAYS="$2"; shift 2 ;;
        --backup-dir)  BACKUP_DIR="$2"; shift 2 ;;
        --data-dir)    DATA_DIR="$2"; shift 2 ;;
        --container)   CONTAINER_NAME="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --docker          Docker volume からバックアップ"
            echo "  --compress        gzip 圧縮を有効化"
            echo "  --retain DAYS     バックアップ保持日数 (デフォルト: 30)"
            echo "  --backup-dir DIR  バックアップ先ディレクトリ"
            echo "  --data-dir DIR    データディレクトリ (デフォルト: ./data)"
            echo "  --container NAME  Docker コンテナ名 (デフォルト: jaia-backend)"
            echo "  -h, --help        ヘルプを表示"
            exit 0
            ;;
        *) log_error "Unknown option: $1"; exit 1 ;;
    esac
done

# バックアップディレクトリ作成
mkdir -p "$BACKUP_DIR"

log_info "=== JAIA Database Backup ==="
log_info "Timestamp: $TIMESTAMP"
log_info "Backup dir: $BACKUP_DIR"
log_info "Retain: $RETAIN_DAYS days"

# Docker モードの場合、コンテナからファイルをコピー
if [ "$DOCKER_MODE" = true ]; then
    log_info "Mode: Docker (container: $CONTAINER_NAME)"

    # コンテナが稼働中か確認
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Container '$CONTAINER_NAME' is not running"
        exit 1
    fi

    # DuckDB バックアップ
    log_info "Backing up DuckDB from Docker volume..."
    docker cp "${CONTAINER_NAME}:/app/data/jaia.duckdb" \
        "${BACKUP_DIR}/jaia_${TIMESTAMP}.duckdb"

    # SQLite バックアップ (WAL ファイル含む)
    log_info "Backing up SQLite from Docker volume..."
    docker cp "${CONTAINER_NAME}:/app/data/jaia_meta.db" \
        "${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db"
    docker cp "${CONTAINER_NAME}:/app/data/jaia_meta.db-wal" \
        "${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db-wal" 2>/dev/null || true
    docker cp "${CONTAINER_NAME}:/app/data/jaia_meta.db-shm" \
        "${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db-shm" 2>/dev/null || true

else
    log_info "Mode: Local (data dir: $DATA_DIR)"

    # ローカルファイル存在確認
    if [ ! -f "${DATA_DIR}/jaia.duckdb" ]; then
        log_warn "DuckDB file not found: ${DATA_DIR}/jaia.duckdb (skipping)"
    else
        log_info "Backing up DuckDB..."
        cp "${DATA_DIR}/jaia.duckdb" "${BACKUP_DIR}/jaia_${TIMESTAMP}.duckdb"
    fi

    if [ ! -f "${DATA_DIR}/jaia_meta.db" ]; then
        log_warn "SQLite file not found: ${DATA_DIR}/jaia_meta.db (skipping)"
    else
        log_info "Backing up SQLite..."
        # sqlite3 .backup が利用可能ならオンラインバックアップ（推奨）
        if command -v sqlite3 &>/dev/null; then
            sqlite3 "${DATA_DIR}/jaia_meta.db" \
                ".backup '${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db'"
        else
            cp "${DATA_DIR}/jaia_meta.db" "${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db"
            cp "${DATA_DIR}/jaia_meta.db-wal" \
                "${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db-wal" 2>/dev/null || true
            cp "${DATA_DIR}/jaia_meta.db-shm" \
                "${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db-shm" 2>/dev/null || true
        fi
    fi
fi

# gzip 圧縮
if [ "$COMPRESS" = true ]; then
    log_info "Compressing backup files..."
    for f in "${BACKUP_DIR}/jaia_${TIMESTAMP}"* "${BACKUP_DIR}/jaia_meta_${TIMESTAMP}"*; do
        if [ -f "$f" ] && [[ ! "$f" == *.gz ]]; then
            gzip "$f"
            log_info "  Compressed: $(basename "$f").gz"
        fi
    done
fi

# バックアップサイズ表示
log_info "Backup files:"
for f in "${BACKUP_DIR}/"*"${TIMESTAMP}"*; do
    if [ -f "$f" ]; then
        size=$(du -h "$f" | cut -f1)
        log_info "  $(basename "$f") ($size)"
    fi
done

# 古いバックアップの削除
OLD_COUNT=$(find "$BACKUP_DIR" -name "jaia_*.duckdb*" -o -name "jaia_meta_*.db*" \
    | xargs -I{} find {} -mtime "+${RETAIN_DAYS}" 2>/dev/null | wc -l)

if [ "$OLD_COUNT" -gt 0 ]; then
    log_info "Cleaning up backups older than $RETAIN_DAYS days ($OLD_COUNT files)..."
    find "$BACKUP_DIR" -name "jaia_*.duckdb*" -mtime "+${RETAIN_DAYS}" -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "jaia_meta_*.db*" -mtime "+${RETAIN_DAYS}" -delete 2>/dev/null || true
else
    log_info "No old backups to clean up"
fi

log_info "=== Backup completed successfully ==="
