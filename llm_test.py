import os

key = os.environ.get("GROQ_API_KEY")
print("Key loaded:", key is not None)

import requests
import re
import sqlite3
import pandas as pd

def ask_llm(question):
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "user", "content": question}
            ]
        }
    )
    data = response.json()
    return data["choices"][0]["message"]["content"]

def is_safe_sql(sql):
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        return False
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "ATTACH", "PRAGMA", "CREATE"]
    for word in forbidden:
        if re.search(r"\b" + word + r"\b", sql_upper):
            return False
    return True

def synthesize_answer(question, sql, result_df):
    rows = result_df.to_dict(orient="records")

    prompt = f"""You are a support-operations analyst. Answer the user's question
using ONLY the data below. Be concise and specific with numbers.

Question: {question}
SQL used: {sql}
Result data: {rows}

Answer:"""

    return ask_llm(prompt)


df = pd.read_csv("data/support_tickets.csv")
df["created_at"] = pd.to_datetime(df["created_at"]) 
dataset_now = df["created_at"].max() 
df["created_at"] = df["created_at"].astype(str)

schema = """
Table: tickets
Columns:
  - ticket_id (TEXT)
  - created_at (TEXT, 'YYYY-MM-DD HH:MM:SS')
  - category (TEXT): one of 'General', 'Billing', 'Technical'
  - priority (TEXT): one of 'Low', 'Medium', 'High', 'Critical'
  - status (TEXT): one of 'Open', 'Escalated', 'Resolved'
  - response_time_hrs (REAL)
  - resolution_time_hrs (REAL): NULL if not yet Resolved
  - agent_id (TEXT)
  - customer_rating (REAL, 1-5): NULL if not yet Resolved
  - issue_summary (TEXT)
"""

question = "Show me all Critical tickets not resolved within 12 hours."

prompt = f"""You translate questions into a single SQLite SELECT query.

{schema}

Important: This is a historical dataset. Treat {dataset_now} as the current
date/time — NOT the real-world today. For relative dates like "this month"
or "this week", calculate relative to {dataset_now}, not SQLite's built-in
'now'.

Rules:
- Output ONLY the raw SQL. No explanation, no markdown formatting.
- Only ever write a SELECT statement.

Question: {question}
"""

sql = ask_llm(prompt)
print(sql)

print(is_safe_sql(sql))



conn = sqlite3.connect(":memory:")
df.to_sql("tickets", conn, index=False, if_exists="replace")

if is_safe_sql(sql):
    result = pd.read_sql_query(sql, conn)
    print(result)

    answer = synthesize_answer(question, sql, result)   # <-- NEW, goes here
    print(answer)
else:
    print("Blocked: generated SQL failed the safety check.")
    print("SQL was:", sql)