import pandas as pd 
df=pd.read_csv('data/support_tickets.csv') 
df["created_at"] = pd.to_datetime(df["created_at"])

dataset_now = df["created_at"].max()
print("dataset_now:", dataset_now)
print("total tickets:", len(df))


unresolved_urgent = df[
    (df["status"].isin(["Open", "Escalated"])) &
    (df["priority"].isin(["High", "Critical"]))
]

print(len(unresolved_urgent))
print(unresolved_urgent[["ticket_id", "priority", "status", "created_at"]].head())


unresolved_urgent = unresolved_urgent.copy()

unresolved_urgent["age_hours"] = (
    (dataset_now - unresolved_urgent["created_at"]).dt.total_seconds() / 3600
).round(1)

print(unresolved_urgent[["ticket_id", "priority", "status", "age_hours"]].sort_values("age_hours", ascending=False).head(10))

p75 = unresolved_urgent["age_hours"].quantile(0.75)
print("75th percentile age (hours):", round(p75, 1))

stale = unresolved_urgent[unresolved_urgent["age_hours"] >= p75].copy()
print(len(stale))


p90 = unresolved_urgent["age_hours"].quantile(0.90)
print("90th percentile age (hours):", round(p90, 1))

stale["severity"] = stale["age_hours"].apply(
    lambda h: "critical" if h >= p90 else "warning"
)
print(stale["severity"].value_counts())

#anomaly 2

resolved = df[df["resolution_time_hrs"].notna()].copy()
print(len(resolved))

def find_outliers_per_priority(resolved_df):
    flagged_parts = []
    for priority, group in resolved_df.groupby("priority"):
        q1 = group["resolution_time_hrs"].quantile(0.25)
        q3 = group["resolution_time_hrs"].quantile(0.75)
        iqr = q3 - q1
        upper = q3 + 1.5 * iqr
        flagged_parts.append(group[group["resolution_time_hrs"] > upper])
    return pd.concat(flagged_parts)

long_resolution = find_outliers_per_priority(resolved)
print(len(long_resolution))
print(long_resolution["priority"].value_counts())


