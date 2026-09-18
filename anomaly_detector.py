import pandas as pd
import math


def find_stale_urgent_tickets(df, dataset_now):
    unresolved_urgent = df[
        (df["status"].isin(["Open", "Escalated"])) &
        (df["priority"].isin(["High", "Critical"]))
    ].copy()

    unresolved_urgent["age_hours"] = (
        (dataset_now - unresolved_urgent["created_at"]).dt.total_seconds() / 3600
    ).round(1)

    p75 = unresolved_urgent["age_hours"].quantile(0.75)
    p90 = unresolved_urgent["age_hours"].quantile(0.90)

    stale = unresolved_urgent[unresolved_urgent["age_hours"] >= p75].copy()
    stale["severity"] = stale["age_hours"].apply(
        lambda h: "critical" if h >= p90 else "warning"
    )

    return stale.sort_values("age_hours", ascending=False)



def find_long_resolution_outliers(df):
    resolved = df[df["resolution_time_hrs"].notna()].copy()

    flagged_parts = []
    for priority, group in resolved.groupby("priority"):
        q1 = group["resolution_time_hrs"].quantile(0.25)
        q3 = group["resolution_time_hrs"].quantile(0.75)
        iqr = q3 - q1
        upper = q3 + 1.5 * iqr
        flagged_parts.append(group[group["resolution_time_hrs"] > upper])

    return pd.concat(flagged_parts).sort_values("resolution_time_hrs", ascending=False)




def clean_for_json(records):
    cleaned = []
    for row in records:
        cleaned_row = {}
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                cleaned_row[key] = None
            else:
                cleaned_row[key] = value
        cleaned.append(cleaned_row)
    return cleaned




def detect_anomalies(df, dataset_now):
    stale = find_stale_urgent_tickets(df, dataset_now)
    long_resolution = find_long_resolution_outliers(df)

    return {
        "stale_urgent_tickets": {
            "count": len(stale),
            "warning_count": int((stale["severity"] == "warning").sum()),
            "critical_count": int((stale["severity"] == "critical").sum()),
            "tickets": clean_for_json(stale.to_dict(orient="records")),
        },
        "long_resolution_outliers": {
            "count": len(long_resolution),
            "tickets": clean_for_json(long_resolution.to_dict(orient="records")),
        },
    }


if __name__ == "__main__":
    df = pd.read_csv("data/support_tickets.csv")
    df["created_at"] = pd.to_datetime(df["created_at"])
    dataset_now = df["created_at"].max()

    stale = find_stale_urgent_tickets(df, dataset_now)
    print("stale urgent tickets:", len(stale))
    print(stale["severity"].value_counts())

    long_resolution = find_long_resolution_outliers(df)
    print()
    print("long resolution outliers:", len(long_resolution))
    print(long_resolution["priority"].value_counts())

    result = detect_anomalies(df, dataset_now)
    print(result["stale_urgent_tickets"]["count"])
    print(result["long_resolution_outliers"]["count"])