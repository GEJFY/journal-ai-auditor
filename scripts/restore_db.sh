#!/usr/bin/env bash
# JAIA Database Restore Script
# バックアップから DuckDB / SQLite をリストア
#
# 使用方法:
#   ./scripts/restore_db.sh --list                              # バックアップ一覧表示
#   ./scripts/restore_db.sh --timestamp 20260216_020000         # 指定タイムスタンプでリストア
#   ./scripts/restore_db.sh --latest                            # 最新バックアップでリストア
#   ./scripts/restore_db.sh --latest --docker                   # Docker volume にリストア
#   ./scripts/restore_db.sh --latest --target duckdb            # DuckDB のみリストア
#   ./scripts/restore_db.sh --latest --target sqlite            # SQLite のみリストア

set -euo pipefail

# デフォルト設定
DATA_DIR="${DATA_DIR:-./data}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DOCKER_MODE=false
CONTAINER_NAME="jaia-backend"
LIST_MODE=false
USE_LATEST=false
TIMESTAMP=""
TARGET="both"  # duckdb, sqlite, both

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
        --list)        LIST_MODE=true; shift ;;
        --latest)      USE_LATEST=true; shift ;;
        --timestamp)   TIMESTAMP="$2"; shift 2 ;;
        --docker)      DOCKER_MODE=true; shift ;;
        --target)      TARGET="$2"; shift 2 ;;
        --backup-dir)  BACKUP_DIR="$2"; shift 2 ;;
        --data-dir)    DATA_DIR="$2"; shift 2 ;;
        --container)   CONTAINER_NAME="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --list              バックアップ一覧を表示"
            echo "  --latest            最新バックアップからリストア"
            echo "  --timestamp TS      指定タイムスタンプからリストア (例: 20260216_020000)"
            echo "  --docker            Docker volume にリストア"
            echo "  --target TYPE       リストア対象: duckdb, sqlite, both (デフォルト: both)"
            echo "  --backup-dir DIR    バックアップディレクトリ"
            echo "  --data-dir DIR      データディレクトリ (デフォルト: ./data)"
            echo "  --container NAME    Docker コンテナ名 (デフォルト: jaia-backend)"
            echo "  -h, --help          ヘルプを表示"
            exit 0
            ;;
        *) log_error "Unknown option: $1"; exit 1 ;;
    esac
done

# バックアップ一覧表示
if [ "$LIST_MODE" = true ]; then
    echo "=== Available Backups ==="
    echo ""
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "Backup directory not found: $BACKUP_DIR"
        exit 0
    fi

    # タイムスタンプ抽出・ソート
    echo "Timestamp            DuckDB                          SQLite"
    echo "-------------------  ------------------------------  ------------------------------"
    for f in $(ls "$BACKUP_DIR"/jaia_*.duckdb* 2>/dev/null | sort -r); do
        ts=$(basename "$f" | sed -E 's/jaia_([0-9]{8}_[0-9]{6}).*/\1/')
        duckdb_file=$(basename "$f")
        duckdb_size=$(du -h "$f" | cut -f1)
        sqlite_file=""
        sqlite_size=""
        for sf in "${BACKUP_DIR}/jaia_meta_${ts}".*; do
            if [ -f "$sf" ] && [[ "$(basename "$sf")" == jaia_meta_${ts}.db* ]] && [[ ! "$(basename "$sf")" == *-wal ]] && [[ ! "$(basename "$sf")" == *-shm ]]; then
                sqlite_file=$(basename "$sf")
                sqlite_size=$(du -h "$sf" | cut -f1)
                break
            fi
        done
        printf "%-20s %-30s %-30s\n" "$ts" "${duckdb_file} (${duckdb_size})" "${sqlite_file:-N/A} ${sqlite_size:+(${sqlite_size})}"
    done
    exit 0
fi

# リストア対象のタイムスタンプを決定
if [ "$USE_LATEST" = true ]; then
    LATEST_DUCKDB=$(ls -t "$BACKUP_DIR"/jaia_*.duckdb* 2>/dev/null | head -1)
    if [ -z "$LATEST_DUCKDB" ]; then
        log_error "No DuckDB backups found in $BACKUP_DIR"
        exit 1
    fi
    TIMESTAMP=$(basename "$LATEST_DUCKDB" | sed -E 's/jaia_([0-9]{8}_[0-9]{6}).*/\1/')
    log_info "Using latest backup: $TIMESTAMP"
elif [ -z "$TIMESTAMP" ]; then
    log_error "Specify --latest or --timestamp <TS>. Use --list to see available backups."
    exit 1
fi

log_info "=== JAIA Database Restore ==="
log_info "Timestamp: $TIMESTAMP"
log_info "Target: $TARGET"

# リストア対象ファイルの確認
DUCKDB_BACKUP=""
SQLITE_BACKUP=""

if [ "$TARGET" = "both" ] || [ "$TARGET" = "duckdb" ]; then
    DUCKDB_BACKUP=$(ls "${BACKUP_DIR}/jaia_${TIMESTAMP}.duckdb"* 2>/dev/null | head -1)
    if [ -z "$DUCKDB_BACKUP" ]; then
        log_error "DuckDB backup not found for timestamp: $TIMESTAMP"
        [ "$TARGET" = "duckdb" ] && exit 1
    fi
fi

if [ "$TARGET" = "both" ] || [ "$TARGET" = "sqlite" ]; then
    SQLITE_BACKUP=$(ls "${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db"* 2>/dev/null | grep -v '\-wal$' | grep -v '\-shm$' | head -1)
    if [ -z "$SQLITE_BACKUP" ]; then
        log_error "SQLite backup not found for timestamp: $TIMESTAMP"
        [ "$TARGET" = "sqlite" ] && exit 1
    fi
fi

# 確認プロンプト
echo ""
log_warn "This will overwrite current database files!"
if [ -n "$DUCKDB_BACKUP" ]; then
    echo "  DuckDB: $(basename "$DUCKDB_BACKUP")"
fi
if [ -n "$SQLITE_BACKUP" ]; then
    echo "  SQLite: $(basename "$SQLITE_BACKUP")"
fi
echo ""
read -p "Continue? (y/N): " confirm
if [[ ! "$confirm" =~ ^[yY]$ ]]; then
    log_info "Restore cancelled"
    exit 0
fi

# Docker モードの場合、コンテナを停止
if [ "$DOCKER_MODE" = true ]; then
    log_info "Stopping container: $CONTAINER_NAME"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
fi

# DuckDB リストア
if [ -n "$DUCKDB_BACKUP" ]; then
    log_info "Restoring DuckDB..."

    # gzip 圧縮の場合は解凍
    if [[ "$DUCKDB_BACKUP" == *.gz ]]; then
        TMP_FILE="/tmp/jaia_restore_${TIMESTAMP}.duckdb"
        gunzip -c "$DUCKDB_BACKUP" > "$TMP_FILE"
        DUCKDB_BACKUP="$TMP_FILE"
    fi

    if [ "$DOCKER_MODE" = true ]; then
        docker cp "$DUCKDB_BACKUP" "${CONTAINER_NAME}:/app/data/jaia.duckdb"
    else
        mkdir -p "$DATA_DIR"
        cp "$DUCKDB_BACKUP" "${DATA_DIR}/jaia.duckdb"
    fi
    log_info "  DuckDB restored"
fi

# SQLite リストア
if [ -n "$SQLITE_BACKUP" ]; then
    log_info "Restoring SQLite..."

    # gzip 圧縮の場合は解凍
    if [[ "$SQLITE_BACKUP" == *.gz ]]; then
        TMP_FILE="/tmp/jaia_meta_restore_${TIMESTAMP}.db"
        gunzip -c "$SQLITE_BACKUP" > "$TMP_FILE"
        SQLITE_BACKUP="$TMP_FILE"
    fi

    if [ "$DOCKER_MODE" = true ]; then
        docker cp "$SQLITE_BACKUP" "${CONTAINER_NAME}:/app/data/jaia_meta.db"
    else
        mkdir -p "$DATA_DIR"
        cp "$SQLITE_BACKUP" "${DATA_DIR}/jaia_meta.db"
        # WAL/SHM ファイルがあればリストア
        WAL_FILE="${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db-wal"
        SHM_FILE="${BACKUP_DIR}/jaia_meta_${TIMESTAMP}.db-shm"
        if [ -f "$WAL_FILE" ]; then
            cp "$WAL_FILE" "${DATA_DIR}/jaia_meta.db-wal"
        else
            rm -f "${DATA_DIR}/jaia_meta.db-wal"
        fi
        if [ -f "$SHM_FILE" ]; then
            cp "$SHM_FILE" "${DATA_DIR}/jaia_meta.db-shm"
        else
            rm -f "${DATA_DIR}/jaia_meta.db-shm"
        fi
    fi
    log_info "  SQLite restored"
fi

# Docker モードの場合、コンテナを再起動
if [ "$DOCKER_MODE" = true ]; then
    log_info "Starting container: $CONTAINER_NAME"
    docker start "$CONTAINER_NAME"
fi

# 一時ファイルのクリーンアップ
rm -f /tmp/jaia_restore_*.duckdb /tmp/jaia_meta_restore_*.db

log_info "=== Restore completed successfully ==="
log_info "Verify with: curl -s http://localhost:8090/api/v1/status | jq ."
