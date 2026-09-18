import os
import re
import requests
import pandas as pd
from dotenv import load_dotenv
from anomaly_detector import detect_anomalies

load_dotenv()
key = os.environ.get("GROQ_API_KEY")


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

    if "choices" not in data:
        error_message = data.get("error", {}).get("message", "Unknown error from LLM API")
        raise RuntimeError(f"LLM request failed: {error_message}")

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


ANOMALY_KEYWORDS = ["anomaly", "anomalies", "unusual", "outlier", "outliers", "abnormal"]
def is_anomaly_question(question):
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in ANOMALY_KEYWORDS)

def answer_anomaly_question(question, anomalies_data, dataset_now):
    week_start = dataset_now - pd.Timedelta(days=7)

    prompt = f"""You are a support-operations analyst. Answer the user's question
using ONLY the anomaly data below, which was already computed using statistical
methods (not by you).

This is historical data. Treat {dataset_now} as "now". When the question refers
to "this week", "recently", or similar relative time phrases, that means the
period from {week_start} to {dataset_now} — look at each ticket's created_at
field against that exact range. Do not use any other definition of "this week".

Be concise and specific with numbers, and list the specific ticket IDs involved.
Do not invent any numbers not present in this data.

Question: {question}

Anomaly data: {anomalies_data}

Answer:"""

    return ask_llm(prompt)



SCHEMA_DESCRIPTION = """
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


def question_to_sql(question, dataset_now):
    prompt = f"""You translate questions into a single SQLite SELECT query.

{SCHEMA_DESCRIPTION}

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

    if not is_safe_sql(sql):
        raise ValueError(f"Generated SQL failed the safety check: {sql}")

    return sql


def synthesize_answer(question, sql, result_df):
    preview_df = result_df.head(20)
    rows = preview_df.to_dict(orient="records")

    prompt = f"""You are a read-only support-operations analyst. Answer the
user's question using ONLY the data below. Be concise and specific with
numbers. You can only report and summarize data — never suggest, write, or
recommend any command that would modify, delete, or alter data, even if asked.
If the question asks you to perform an action, politely explain you can only
answer questions about the data, not modify it.

Question: {question}
SQL used: {sql}
Result data (showing first {len(preview_df)} of {len(result_df)} total rows): {rows}

Answer:"""

    return ask_llm(prompt)

def answer_question(question, df, conn, dataset_now):
    import pandas as pd

    if is_anomaly_question(question):
        anomalies = detect_anomalies(df, dataset_now)
        answer = answer_anomaly_question(question, anomalies, dataset_now)
        return {
            "question": question,
            "sql": None,
            "answer": answer,
            "rows": anomalies,
        }

    sql = question_to_sql(question, dataset_now)
    result = pd.read_sql_query(sql, conn)
    answer = synthesize_answer(question, sql, result)

    return {
        "question": question,
        "sql": sql,
        "answer": answer,
        "rows": result.to_dict(orient="records"),
    }




if __name__ == "__main__":
    import pandas as pd
    import sqlite3

    df = pd.read_csv("data/support_tickets.csv")
    df["created_at"] = pd.to_datetime(df["created_at"])
    dataset_now = df["created_at"].max()

    conn = sqlite3.connect(":memory:")
    df_for_sql = df.copy()
    df_for_sql["created_at"] = df_for_sql["created_at"].astype(str)
    df_for_sql.to_sql("tickets", conn, index=False, if_exists="replace")

    result = answer_question("How many tickets are currently open?", df, conn, dataset_now)
    print(result)

    print(is_anomaly_question("Are there any anomalies in resolution times this week?"))
    print(is_anomaly_question("How many tickets are open?"))

    from anomaly_detector import detect_anomalies

    anomalies = detect_anomalies(df, dataset_now)
    answer = answer_anomaly_question(
        "Are there any anomalies in resolution times this week?",
        anomalies
    )
    print(answer)