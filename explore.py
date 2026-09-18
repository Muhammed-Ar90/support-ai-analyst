import pandas as pd 

df=pd.read_csv('data/support_tickets.csv')
print(df.head())
print(df.columns.tolist())
print()
print(df.dtypes)
print(df.isna().sum())

df["created_at"] = pd.to_datetime(df["created_at"])
print(df["created_at"].dtype)
print(df["created_at"].min(), "to", df["created_at"].max())

df["response_time_hrs"] = pd.to_numeric(df["response_time_hrs"], errors="coerce")
df["resolution_time_hrs"] = pd.to_numeric(df["resolution_time_hrs"], errors="coerce")
df["customer_rating"] = pd.to_numeric(df["customer_rating"], errors="coerce")
print(df.dtypes)

dataset_now = df["created_at"].max()
print("dataset_now:", dataset_now)


#SQL

import sqlite3

conn = sqlite3.connect(":memory:")

df_for_sql = df.copy()
df_for_sql["created_at"] = df_for_sql["created_at"].astype(str)

df_for_sql.to_sql("tickets", conn, index=False, if_exists="replace")

result = pd.read_sql_query("SELECT COUNT(*) FROM tickets", conn)
print(result)

