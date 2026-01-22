import requests

HRM_API_URL = "https://hrm.icss.com.vn/ICSS/api/execute-sql"

def execute_sql(sql: str):
    payload = {"command": sql}
    headers = {"Content-Type": "application/json"}

    res = requests.post(HRM_API_URL, json=payload, headers=headers, timeout=10)
    
    if res.status_code != 200:
        raise Exception("HRM API error")

    return res.json()
