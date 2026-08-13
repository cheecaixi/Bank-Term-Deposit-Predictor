"""
Bank Marketing Dashboard Service
=================================
This is Student C's microservice. It has 3 tabs:
  1. Single Prediction  -> agent types in one customer's details
  2. Batch Prediction    -> agent uploads a CSV of many customers
  3. Analyst View        -> charts/KPIs for managers

HOW IT TALKS TO THE REST OF THE SYSTEM
---------------------------------------
Right now, USE_MOCK = True, so this file predicts using a fake function
(mock_predict / mock_predict_batch) instead of calling a real API.
This lets you build and test the whole UI WITHOUT waiting for the
Inference/Gateway services to be ready.

Once your teammates have a working API Gateway, you just:
  1. Set USE_MOCK = False
  2. Set GATEWAY_URL to the real gateway address (e.g. via env var)
The call_predict_api() and call_batch_api() functions below are where
the real HTTP requests happen -- everything else in the app doesn't
need to change.
"""

import os
import io
import requests
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------
USE_MOCK = True  # flip to False once the real Gateway is ready
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

# The exact fields your form collects. Agree these names with
# Member A (Inference) so your JSON matches what their model expects.
FEATURE_FIELDS = [
    "age", "job", "marital", "education", "default",
    "balance", "housing", "loan", "contact", "day",
    "month", "campaign", "pdays", "previous", "poutcome",
]

JOB_OPTIONS = [
    "management", "technician", "entrepreneur", "blue-collar", "unknown",
    "retired", "admin.", "services", "self-employed", "unemployed",
    "housemaid", "student",
]
MARITAL_OPTIONS = ["married", "single", "divorced"]
EDUCATION_OPTIONS = ["unknown", "secondary", "primary", "tertiary"]
YES_NO_OPTIONS = ["yes", "no"]
CONTACT_OPTIONS = ["unknown", "telephone", "cellular"]
MONTH_OPTIONS = ["jan", "feb", "mar", "apr", "may", "jun",
                  "jul", "aug", "sep", "oct", "nov", "dec"]
POUTCOME_OPTIONS = ["unknown", "other", "failure", "success"]


# ---------------------------------------------------------------
# MOCK PREDICTOR (stand-in for the real Inference service)
# ---------------------------------------------------------------
def mock_predict(record: dict) -> dict:
    """Pretends to call the ML model for ONE customer.
    Replace this logic later with a real API call (see call_predict_api).
    """
    # very rough fake logic: higher balance + previous success -> higher prob
    score = 0.1
    if record.get("balance", 0) > 1000:
        score += 0.2
    if record.get("poutcome") == "success":
        score += 0.4
    if record.get("housing") == "no":
        score += 0.1
    score = min(score, 0.95)
    return {"probability": round(score, 3), "prediction": "yes" if score > 0.5 else "no"}


def mock_predict_batch(df: pd.DataFrame) -> pd.DataFrame:
    """Pretends to call the ML model for MANY customers at once."""
    results = df.apply(lambda row: mock_predict(row.to_dict()), axis=1)
    df = df.copy()
    df["probability"] = results.apply(lambda r: r["probability"])
    df["prediction"] = results.apply(lambda r: r["prediction"])
    return df


# ---------------------------------------------------------------
# REAL API CALLS (used once USE_MOCK = False)
# ---------------------------------------------------------------
def call_predict_api(record: dict) -> dict:
    """Calls the real Gateway's /predict endpoint for one customer."""
    resp = requests.post(f"{GATEWAY_URL}/predict", json=record, timeout=10)
    resp.raise_for_status()
    return resp.json()  # expected: {"probability": 0.73, "prediction": "yes"}


def call_batch_api(df: pd.DataFrame) -> pd.DataFrame:
    """Calls the real Gateway's /predict/batch endpoint for many customers."""
    records = df.to_dict(orient="records")
    resp = requests.post(f"{GATEWAY_URL}/predict/batch", json={"records": records}, timeout=60)
    resp.raise_for_status()
    results = resp.json()["results"]  # expected: list of {"probability":..,"prediction":..}
    out = df.copy()
    out["probability"] = [r["probability"] for r in results]
    out["prediction"] = [r["prediction"] for r in results]
    return out


def predict_one(record: dict) -> dict:
    if USE_MOCK:
        return mock_predict(record)
    try:
        return call_predict_api(record)
    except Exception as e:
        st.error(f"Could not reach Inference service: {e}")
        return None


def predict_many(df: pd.DataFrame):
    if USE_MOCK:
        return mock_predict_batch(df)
    try:
        return call_batch_api(df)
    except Exception as e:
        st.error(f"Could not reach Inference service: {e}")
        return None


# ---------------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------------
st.set_page_config(page_title="Bank Marketing Dashboard", layout="wide")
st.title("📊 Bank Marketing AI Dashboard")
if USE_MOCK:
    st.caption("⚠️ Running in MOCK mode — predictions are fake placeholder logic, not the real model.")

tab1, tab2, tab3 = st.tabs(["🧑 Single Prediction", "📁 Batch Prediction", "📈 Analyst View"])

# ---------------------------------------------------------------
# TAB 1: SINGLE PREDICTION
# ---------------------------------------------------------------
with tab1:
    st.subheader("Predict for one customer")
    st.write("Fill in the customer's details, then click Predict.")

    col1, col2, col3 = st.columns(3)
    with col1:
        age = st.number_input("Age", min_value=18, max_value=100, value=35)
        job = st.selectbox("Job", JOB_OPTIONS)
        marital = st.selectbox("Marital status", MARITAL_OPTIONS)
        education = st.selectbox("Education", EDUCATION_OPTIONS)
        default = st.selectbox("Has credit in default?", YES_NO_OPTIONS)
    with col2:
        balance = st.number_input("Account balance (€)", value=1000, step=100)
        housing = st.selectbox("Has housing loan?", YES_NO_OPTIONS)
        loan = st.selectbox("Has personal loan?", YES_NO_OPTIONS)
        contact = st.selectbox("Contact method", CONTACT_OPTIONS)
        day = st.number_input("Last contact day of month", min_value=1, max_value=31, value=15)
    with col3:
        month = st.selectbox("Last contact month", MONTH_OPTIONS)
        campaign = st.number_input("Contacts this campaign", min_value=1, value=1)
        pdays = st.number_input("Days since last contact (-1 = never)", value=-1)
        previous = st.number_input("Contacts before this campaign", min_value=0, value=0)
        poutcome = st.selectbox("Previous campaign outcome", POUTCOME_OPTIONS)

    if st.button("🔮 Predict", type="primary"):
        record = {
            "age": age, "job": job, "marital": marital, "education": education,
            "default": default, "balance": balance, "housing": housing, "loan": loan,
            "contact": contact, "day": day, "month": month, "campaign": campaign,
            "pdays": pdays, "previous": previous, "poutcome": poutcome,
        }
        result = predict_one(record)
        if result:
            prob = result["probability"]
            label = result["prediction"]
            st.metric("Subscription probability", f"{prob*100:.1f}%")
            if label == "yes":
                st.success("✅ Likely to SUBSCRIBE — good candidate to prioritize on the call.")
            else:
                st.warning("❌ Unlikely to subscribe based on current profile.")

# ---------------------------------------------------------------
# TAB 2: BATCH PREDICTION
# ---------------------------------------------------------------
with tab2:
    st.subheader("Predict for a whole list of customers")
    st.write(
        "Upload a CSV with columns: "
        + ", ".join(FEATURE_FIELDS)
    )

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not read that file as CSV: {e}")
            df = None

        if df is not None:
            # Validate columns before doing anything else
            missing_cols = [c for c in FEATURE_FIELDS if c not in df.columns]
            if missing_cols:
                st.error(
                    "This file is missing required columns: "
                    + ", ".join(missing_cols)
                    + ". Please check the column names and re-upload."
                )
            else:
                st.success(f"Loaded {len(df)} rows. Preview below:")
                st.dataframe(df.head(10))

                if st.button("🔮 Run batch prediction", type="primary"):
                    with st.spinner(f"Scoring {len(df)} customers..."):
                        results_df = predict_many(df)

                    if results_df is not None:
                        st.success("Done!")
                        st.dataframe(results_df.head(50))

                        csv_bytes = results_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Download full results as CSV",
                            data=csv_bytes,
                            file_name="predictions_results.csv",
                            mime="text/csv",
                        )

                        subscribe_rate = (results_df["prediction"] == "yes").mean()
                        st.metric("Predicted subscription rate", f"{subscribe_rate*100:.1f}%")

# ---------------------------------------------------------------
# TAB 3: ANALYST VIEW
# ---------------------------------------------------------------
with tab3:
    st.subheader("Campaign performance overview")
    st.caption("Currently showing sample data. Swap this for real calls to the Database/Monitoring service later.")

    # Sample data just so the charts have something to show today.
    # Later: replace this block with a real API call, e.g.
    #   sample = requests.get(f"{GATEWAY_URL}/analytics/summary").json()
    sample = pd.DataFrame({
        "job": ["management", "technician", "blue-collar", "admin.", "retired"],
        "conversion_rate": [0.14, 0.11, 0.08, 0.13, 0.22],
    })

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total predictions made", "1,204")
    kpi2.metric("Overall subscription rate", "12.3%")
    kpi3.metric("Model accuracy (last eval)", "89.1%")

    st.write("### Conversion rate by job type")
    st.bar_chart(sample.set_index("job"))
