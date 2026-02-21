import duckdb
from app.db import DuckDBManager

def verify_risk_data():
    db = DuckDBManager()
    
    print("--- Journal Entries Count ---")
    count = db.execute("SELECT COUNT(*) FROM journal_entries")[0][0]
    print(f"Total entries: {count}")
    
    print("\n--- Risk Score Distribution ---")
    dist = db.execute("""
        SELECT 
            CASE 
                WHEN risk_score >= 60 THEN 'High (>=60)'
                WHEN risk_score >= 40 THEN 'Medium (>=40)'
                WHEN risk_score >= 20 THEN 'Low (>=20)'
                ELSE 'Minimal (<20)'
            END as level,
            COUNT(*) as count
        FROM journal_entries
        GROUP BY 1
        ORDER BY 2 DESC
    """)
    for row in dist:
        print(f"{row[0]}: {row[1]}")
        
    print("\n--- Sample Risk Items (>=20) ---")
    items = db.execute("""
        SELECT journal_id, risk_score, amount, effective_date 
        FROM journal_entries 
        WHERE risk_score >= 20 
        LIMIT 5
    """)
    for row in items:
        print(row)

if __name__ == "__main__":
    verify_risk_data()
