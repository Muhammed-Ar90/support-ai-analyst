from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import sqlite3

from llm_engine import answer_question
from anomaly_detector import detect_anomalies

app = FastAPI()

df = pd.read_csv("data/support_tickets.csv")
df["created_at"] = pd.to_datetime(df["created_at"])
dataset_now = df["created_at"].max()

conn = sqlite3.connect(":memory:", check_same_thread=False)
df_for_sql = df.copy()
df_for_sql["created_at"] = df_for_sql["created_at"].astype(str)
df_for_sql.to_sql("tickets", conn, index=False, if_exists="replace")


class QuestionRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok", "tickets_loaded": len(df)}


@app.post("/query")
def query(request: QuestionRequest):
    try:
        return answer_question(request.question, df, conn, dataset_now)
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/anomalies")
def anomalies():
    return detect_anomalies(df, dataset_now)


@app.get("/stats")
def stats():
    return {
        "total_tickets": len(df),
        "by_status": df["status"].value_counts().to_dict(),
        "by_priority": df["priority"].value_counts().to_dict(),
        "by_category": df["category"].value_counts().to_dict(),
        "avg_customer_rating": round(float(df["customer_rating"].mean(skipna=True)), 2),
        "avg_response_time_hrs": round(float(df["response_time_hrs"].mean(skipna=True)), 2),
        "avg_resolution_time_hrs": round(float(df["resolution_time_hrs"].mean(skipna=True)), 2),
        "date_range": {
            "start": df["created_at"].min().strftime("%Y-%m-%d %H:%M:%S"),
            "end": df["created_at"].max().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }