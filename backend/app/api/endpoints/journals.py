"""
Journal entry search and detail endpoints.

仕訳データの検索・詳細参照APIエンドポイント。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.db import DuckDBManager

router = APIRouter()


def get_db() -> DuckDBManager:
    """Get DB instance."""
    return DuckDBManager()


@router.get("/search")
async def search_journals(
    fiscal_year: int = Query(...),
    keyword: str | None = Query(None, description="仕訳ID, 摘要, 科目コードで検索"),
    account: str | None = Query(None, description="勘定科目コード"),
    date_from: str | None = Query(None, description="開始日 (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="終了日 (YYYY-MM-DD)"),
    min_amount: float | None = Query(None, ge=0),
    max_amount: float | None = Query(None, ge=0),
    prepared_by: str | None = Query(None),
    risk_score_min: float | None = Query(None, ge=0, le=100),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Search journal entries with flexible filters.

    Args:
        fiscal_year: 会計年度
        keyword: フリーワード検索（仕訳ID, 摘要, 科目コード）
        account: 勘定科目コードで絞り込み
        date_from: 日付の開始範囲
        date_to: 日付の終了範囲
        min_amount: 最小金額
        max_amount: 最大金額
        prepared_by: 起票者
        risk_score_min: リスクスコアの最小値
        limit: 取得件数上限
        offset: オフセット

    Returns:
        検索結果（entries, total_count, page, page_size）
    """
    db = get_db()

    conditions = ["fiscal_year = ?"]
    params: list[Any] = [fiscal_year]

    if keyword:
        conditions.append(
            "(journal_id ILIKE ? OR description ILIKE ? OR gl_account_number ILIKE ?)"
        )
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])

    if account:
        conditions.append("gl_account_number = ?")
        params.append(account)

    if date_from:
        conditions.append("effective_date >= ?")
        params.append(date_from)

    if date_to:
        conditions.append("effective_date <= ?")
        params.append(date_to)

    if min_amount is not None:
        conditions.append("amount >= ?")
        params.append(min_amount)

    if max_amount is not None:
        conditions.append("amount <= ?")
        params.append(max_amount)

    if prepared_by:
        conditions.append("prepared_by ILIKE ?")
        params.append(f"%{prepared_by}%")

    if risk_score_min is not None:
        conditions.append("COALESCE(risk_score, 0) >= ?")
        params.append(risk_score_min)

    where = " AND ".join(conditions)

    # Count total
    count_query = f"SELECT COUNT(*) FROM journal_entries WHERE {where}"
    count_result = db.execute(count_query, params)
    total_count = count_result[0][0] if count_result else 0

    # Fetch entries with LEFT JOIN to chart_of_accounts
    data_query = f"""
        SELECT
            je.gl_detail_id,
            je.journal_id,
            je.effective_date,
            je.gl_account_number,
            COALESCE(coa.account_name, je.gl_account_number) as account_name,
            je.amount,
            je.debit_credit_indicator,
            je.description,
            je.prepared_by,
            je.approved_by,
            COALESCE(je.risk_score, 0) as risk_score
        FROM journal_entries je
        LEFT JOIN chart_of_accounts coa
            ON je.gl_account_number = coa.account_code
        WHERE {
        where.replace("fiscal_year", "je.fiscal_year")
        .replace("journal_id", "je.journal_id")
        .replace("description", "je.description")
        .replace("gl_account_number", "je.gl_account_number")
        .replace("effective_date", "je.effective_date")
        .replace("amount", "je.amount")
        .replace("prepared_by", "je.prepared_by")
        .replace("risk_score", "je.risk_score")
    }
        ORDER BY je.effective_date DESC, je.journal_id, je.journal_id_line_number
        LIMIT {limit} OFFSET {offset}
    """

    rows = db.execute(data_query, params)

    entries = [
        {
            "gl_detail_id": row[0] or "",
            "journal_id": row[1] or "",
            "effective_date": str(row[2]) if row[2] else "",
            "gl_account_number": row[3] or "",
            "account_name": row[4] or "",
            "amount": float(row[5] or 0),
            "debit_credit_indicator": row[6] or "",
            "description": row[7] or "",
            "prepared_by": row[8] or "",
            "approved_by": row[9] or "",
            "risk_score": float(row[10] or 0),
        }
        for row in rows
    ]

    return {
        "entries": entries,
        "total_count": total_count,
        "page": offset // limit if limit else 0,
        "page_size": limit,
    }
