def validate_sql(sql: str):
    banned = ["delete", "update", "insert", "drop", "alter"]
    for word in banned:
        if word in sql.lower():
            raise ValueError("SQL không hợp lệ")
