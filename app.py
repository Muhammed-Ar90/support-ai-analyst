
import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Support AI Analyst",
    page_icon="🤖"
)

st.title("🤖 Support Ticket AI Analyst")

# --------------------------------------------------
# QUESTION
# --------------------------------------------------

st.subheader("Ask Your Data")

question = st.text_input(
    "Enter your question",
    placeholder="Example: How many tickets are currently open?"
)

if st.button("🔎 Ask Question"):

    if not question.strip():
        st.warning("Please enter a question.")

    else:
        try:
            with st.spinner("Processing..."):

                response = requests.post(
                    f"{API_URL}/query",
                    json={"question": question},
                    timeout=120
                )

            if response.status_code == 200:

                result = response.json()

                st.subheader("Answer")

                st.write(
                    result.get(
                        "answer",
                        "No answer returned."
                    )
                )

                rows = result.get("rows")

                if rows:
                    st.subheader("Results")
                    st.dataframe(rows)

                sql = result.get("sql")

                if sql:
                    with st.expander("View SQL"):
                        st.code(
                            sql,
                            language="sql"
                        )

            else:
                try:
                    error = response.json()
                except Exception:
                    error = response.text

                st.error(
                    f"API Error ({response.status_code}): {error}"
                )

        except requests.exceptions.ConnectionError:
            st.error(
                "Cannot connect to FastAPI. "
                "Make sure the backend is running."
            )

        except requests.exceptions.Timeout:
            st.error(
                "Request timed out."
            )

        except Exception as e:
            st.error(
                f"Unexpected error: {e}"
            )


st.divider()


# --------------------------------------------------
# STATS
# --------------------------------------------------

st.subheader("Dataset Statistics")

if st.button("📊 View Stats"):

    try:
        with st.spinner("Loading statistics..."):

            response = requests.get(
                f"{API_URL}/stats",
                timeout=30
            )

        if response.status_code == 200:

            stats = response.json()

            st.subheader("Statistics")

            # Basic statistics
            st.write(
                f"**Total Tickets:** "
                f"{stats.get('total_tickets', 'N/A')}"
            )

            st.write(
                f"**Average Customer Rating:** "
                f"{stats.get('avg_customer_rating', 'N/A')}"
            )

            st.write(
                f"**Average Response Time:** "
                f"{stats.get('avg_response_time_hrs', 'N/A')} hrs"
            )

            st.write(
                f"**Average Resolution Time:** "
                f"{stats.get('avg_resolution_time_hrs', 'N/A')} hrs"
            )

            # Status
            st.write("### Tickets by Status")

            by_status = stats.get("by_status", {})

            if by_status:
                st.dataframe(
                    [
                        {
                            "Status": status,
                            "Tickets": count
                        }
                        for status, count in by_status.items()
                    ],
                    hide_index=True
                )

            # Priority
            st.write("### Tickets by Priority")

            by_priority = stats.get("by_priority", {})

            if by_priority:
                st.dataframe(
                    [
                        {
                            "Priority": priority,
                            "Tickets": count
                        }
                        for priority, count in by_priority.items()
                    ],
                    hide_index=True
                )

            # Category
            st.write("### Tickets by Category")

            by_category = stats.get("by_category", {})

            if by_category:
                st.dataframe(
                    [
                        {
                            "Category": category,
                            "Tickets": count
                        }
                        for category, count in by_category.items()
                    ],
                    hide_index=True
                )

        else:

            st.error(
                f"Stats API Error: {response.status_code}"
            )

    except requests.exceptions.ConnectionError:

        st.error(
            "Cannot connect to FastAPI. "
            "Make sure the backend is running."
        )

    except Exception as e:

        st.error(
            f"Error loading statistics: {e}"
        )


st.divider()


# --------------------------------------------------
# ANOMALIES
# --------------------------------------------------

st.subheader("🚨 Anomaly Detection")

if st.button("🚨 Check Anomalies"):

    try:

        with st.spinner("Detecting anomalies..."):

            response = requests.get(
                f"{API_URL}/anomalies",
                timeout=60
            )

        if response.status_code == 200:

            anomalies = response.json()

            # ==================================================
            # 1. STALE URGENT TICKETS
            # ==================================================

            stale = anomalies.get(
                "stale_urgent_tickets",
                {}
            )

            stale_count = stale.get("count", 0)
            warning_count = stale.get("warning_count", 0)
            critical_count = stale.get("critical_count", 0)

            st.markdown("### 🕐 Stale Urgent Tickets")

            # Summary
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Total",
                    stale_count
                )

            with col2:
                st.metric(
                    "⚠️ Warning",
                    warning_count
                )

            with col3:
                st.metric(
                    "🔴 Critical",
                    critical_count
                )

            # Tickets
            stale_tickets = stale.get(
                "tickets",
                []
            )

            if stale_tickets:

                st.write("#### Tickets")

                st.dataframe(
                    stale_tickets,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.success(
                    "No stale urgent tickets detected."
                )


            # ==================================================
            # 2. LONG RESOLUTION OUTLIERS
            # ==================================================

            st.divider()

            outliers = anomalies.get(
                "long_resolution_outliers",
                {}
            )

            outlier_count = outliers.get(
                "count",
                0
            )

            outlier_tickets = outliers.get(
                "tickets",
                []
            )

            st.markdown(
                "### ⏱️ Long Resolution Outliers"
            )

            st.metric(
                "Total Outliers",
                outlier_count
            )

            if outlier_tickets:

                st.write("#### Tickets")

                st.dataframe(
                    outlier_tickets,
                    use_container_width=True,
                    hide_index=True
                )

            else:

                st.success(
                    "No long-resolution outliers detected."
                )

        else:

            st.error(
                f"Anomaly API Error: "
                f"{response.status_code}"
            )

    except requests.exceptions.ConnectionError:

        st.error(
            "Cannot connect to FastAPI. "
            "Make sure the backend is running."
        )

    except requests.exceptions.Timeout:

        st.error(
            "Anomaly detection timed out."
        )

    except Exception as e:

        st.error(
            f"Error detecting anomalies: {e}"
        )

