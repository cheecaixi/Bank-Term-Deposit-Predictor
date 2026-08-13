"""
Bank Marketing Dashboard Service
=================================
Student C's microservice. Talks ONLY to the API Gateway (Member B) --
never directly to Inference, Database, or Monitoring.

MOCK vs LIVE MODE
------------------
Toggle it from the sidebar in the app itself (no code edit needed).
- Mock mode: uses fake local prediction logic. Works with zero other
  services running -- good for building/demoing before teammates finish.
- Live mode: calls the real Gateway at GATEWAY_URL.

GATEWAY CONTRACT (matches Member B's actual FastAPI code)
-----------------------------------------------------------
  POST {GATEWAY_URL}/api/predict   -> single customer -> {"prediction":.., "probability":..}
  GET  {GATEWAY_URL}/api/results   -> list of all past logged predictions (raw, not aggregated)
  GET  {GATEWAY_URL}/api/logs      -> monitoring/system logs

NOTE: there is no batch endpoint on the Gateway yet. Until Member B adds
one (e.g. POST /api/predict/batch), live batch mode falls back to calling
/api/predict once per row. This is slower and is clearly labelled in the UI.
"""

import os
import time
import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------
DEFAULT_GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")

FEATURE_FIELDS = [
    "age", "job", "marital", "education", "default",
    "balance", "housing", "loan", "contact", "day",
    "month", "campaign", "pdays", "previous", "poutcome",
]
ID_FIELDS = ["customer_id", "phone_number"]  # passed through, never sent to the model

JOB_OPTIONS = ["management", "technician", "entrepreneur", "blue-collar", "unknown",
               "retired", "admin.", "services", "self-employed", "unemployed",
               "housemaid", "student"]
MARITAL_OPTIONS = ["married", "single", "divorced"]
EDUCATION_OPTIONS = ["unknown", "secondary", "primary", "tertiary"]
YES_NO_OPTIONS = ["yes", "no"]
CONTACT_OPTIONS = ["unknown", "telephone", "cellular"]
MONTH_OPTIONS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
POUTCOME_OPTIONS = ["unknown", "other", "failure", "success"]

st.set_page_config(page_title="Bank Marketing Dashboard", layout="wide", page_icon="🏦")

# ---------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []  # list of dicts, for this session's single predictions
if "gateway_url" not in st.session_state:
    st.session_state.gateway_url = DEFAULT_GATEWAY_URL
if "use_mock" not in st.session_state:
    st.session_state.use_mock = True


# ---------------------------------------------------------------
# MOCK PREDICTOR (stand-in for the real Inference service)
# ---------------------------------------------------------------
def mock_predict(record: dict) -> dict:
    score = 0.1
    if record.get("balance", 0) > 1000:
        score += 0.2
    if record.get("poutcome") == "success":
        score += 0.4
    if record.get("housing") == "no":
        score += 0.1
    if record.get("previous", 0) > 0:
        score += 0.05
    score = min(score, 0.95)
    return {"probability": round(score, 3), "prediction": "yes" if score > 0.5 else "no"}


# ---------------------------------------------------------------
# REAL API CALLS -- matches Member B's FastAPI gateway exactly
# ---------------------------------------------------------------
def call_predict_api(record: dict) -> dict:
    url = f"{st.session_state.gateway_url}/api/predict"
    resp = requests.post(url, json=record, timeout=10)
    resp.raise_for_status()
    return resp.json()


def call_results_api() -> list:
    """Raw historical predictions from the Gateway -- we aggregate them
    ourselves client-side since the Gateway doesn't expose a summary
    endpoint yet."""
    url = f"{st.session_state.gateway_url}/api/results"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def predict_one(record: dict):
    if st.session_state.use_mock:
        time.sleep(0.3)  # tiny delay so the spinner feels real in demos
        return mock_predict(record)
    try:
        return call_predict_api(record)
    except Exception as e:
        st.error(f"Could not reach the Gateway at {st.session_state.gateway_url}: {e}")
        return None


def predict_many(df: pd.DataFrame, progress_callback=None):
    """Returns a results DataFrame with probability/prediction columns added."""
    feature_df = df[FEATURE_FIELDS]
    results = []
    for i, row in feature_df.iterrows():
        record = row.to_dict()
        if st.session_state.use_mock:
            result = mock_predict(record)
        else:
            try:
                result = call_predict_api(record)
            except Exception as e:
                st.error(f"Batch stopped -- Gateway error on row {i}: {e}")
                return None
        results.append(result)
        if progress_callback:
            progress_callback((i + 1) / len(feature_df))
    out = df.copy()
    out["probability"] = [r["probability"] for r in results]
    out["prediction"] = [r["prediction"] for r in results]
    return out


# ---------------------------------------------------------------
# SIDEBAR -- connection settings, visible and interactive
# ---------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    st.session_state.use_mock = st.toggle(
        "Mock mode",
        value=st.session_state.use_mock,
        help="ON = fake predictions, works with no backend running. OFF = calls the real API Gateway.",
    )
    if not st.session_state.use_mock:
        st.session_state.gateway_url = st.text_input("Gateway URL", value=st.session_state.gateway_url)
        if st.button("🔌 Test connection"):
            try:
                r = requests.get(f"{st.session_state.gateway_url}/docs", timeout=3)
                st.success(f"Reached gateway (status {r.status_code})")
            except Exception as e:
                st.error(f"Unreachable: {e}")
    else:
        st.caption("Using local fake predictor -- no backend needed.")

    st.divider()
    st.caption(f"Mode: {'🧪 MOCK' if st.session_state.use_mock else '🟢 LIVE'}")
    st.caption(f"Predictions this session: {len(st.session_state.history)}")


# ---------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------
st.title("🏦 Bank Marketing AI Dashboard")
mode_badge = "🧪 Mock mode -- no backend needed" if st.session_state.use_mock else f"🟢 Live -- {st.session_state.gateway_url}"
st.caption(mode_badge)

tab1, tab2, tab3 = st.tabs(["🧑 Single Prediction", "📁 Batch Prediction", "📈 Analyst View"])

# ---------------------------------------------------------------
# TAB 1: SINGLE PREDICTION
# ---------------------------------------------------------------
with tab1:
    st.subheader("Predict for one customer")
    st.write("Use this mid-call, or to spot-check a customer already looked up.")

    with st.form("single_predict_form"):
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

        submitted = st.form_submit_button("🔮 Predict", type="primary", use_container_width=True)

    if submitted:
        record = {
            "age": age, "job": job, "marital": marital, "education": education,
            "default": default, "balance": balance, "housing": housing, "loan": loan,
            "contact": contact, "day": day, "month": month, "campaign": campaign,
            "pdays": pdays, "previous": previous, "poutcome": poutcome,
        }
        with st.spinner("Scoring customer..."):
            result = predict_one(record)

        if result:
            prob = result["probability"]
            label = result["prediction"]

            res_col1, res_col2 = st.columns([1, 2])
            with res_col1:
                st.metric("Subscription probability", f"{prob*100:.1f}%")
            with res_col2:
                st.progress(prob)

            if label == "yes":
                st.success("✅ Likely to SUBSCRIBE — good candidate to prioritize on this call.")
            else:
                st.warning("❌ Unlikely to subscribe based on current profile.")

            st.session_state.history.insert(0, {
                "time": time.strftime("%H:%M:%S"), "job": job, "age": age,
                "probability": prob, "prediction": label,
            })

    if st.session_state.history:
        st.divider()
        st.write("#### Recent predictions this session")
        hist_df = pd.DataFrame(st.session_state.history[:10])
        st.dataframe(hist_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------
# TAB 2: BATCH PREDICTION
# ---------------------------------------------------------------
with tab2:
    st.subheader("Predict for a whole list of customers")
    st.write(
        "Upload a CSV exported from the bank's system. Required columns: "
        + ", ".join(FEATURE_FIELDS)
        + ". Optional: `customer_id`, `phone_number` (carried through to results, never sent to the model)."
    )

    if not st.session_state.use_mock:
        st.info("Live mode has no batch endpoint yet -- rows are scored one at a time via /api/predict. This will be slower for large files.")

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Could not read that file as CSV: {e}")
            df = None

        if df is not None:
            missing_cols = [c for c in FEATURE_FIELDS if c not in df.columns]
            if missing_cols:
                st.error("Missing required columns: " + ", ".join(missing_cols))
            else:
                id_cols_present = [c for c in ID_FIELDS if c in df.columns]
                if not id_cols_present:
                    st.warning("No customer_id or phone_number column found -- results won't be traceable back to a specific customer.")

                st.success(f"Loaded {len(df)} rows.")
                with st.expander("Preview uploaded data", expanded=True):
                    st.dataframe(df.head(10), use_container_width=True)

                if st.button("🔮 Run batch prediction", type="primary"):
                    progress_bar = st.progress(0.0, text="Scoring customers...")

                    def update_progress(frac):
                        progress_bar.progress(frac, text=f"Scoring customers... {int(frac*100)}%")

                    results_df = predict_many(df, progress_callback=update_progress)
                    progress_bar.empty()

                    if results_df is not None:
                        st.session_state.last_batch_results = results_df
                        st.success("Done!")

    if "last_batch_results" in st.session_state:
        results_df = st.session_state.last_batch_results

        st.divider()
        st.write("#### Results")

        k1, k2, k3 = st.columns(3)
        subscribe_rate = (results_df["prediction"] == "yes").mean()
        k1.metric("Customers scored", len(results_df))
        k2.metric("Predicted subscription rate", f"{subscribe_rate*100:.1f}%")
        k3.metric("High-confidence leads (>70%)", int((results_df["probability"] > 0.7).sum()))

        sort_choice = st.radio("Sort by", ["Highest probability first", "Original order"], horizontal=True)
        display_df = results_df.copy()
        if sort_choice == "Highest probability first":
            display_df = display_df.sort_values("probability", ascending=False)

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        csv_bytes = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download results as CSV",
            data=csv_bytes,
            file_name="predictions_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

# ---------------------------------------------------------------
# TAB 3: ANALYST VIEW
# ---------------------------------------------------------------
with tab3:
    st.subheader("Campaign performance overview")

    if st.session_state.use_mock:
        st.caption("Mock mode -- showing sample data, not real logged predictions.")
        sample = pd.DataFrame({
            "job": ["management", "technician", "blue-collar", "admin.", "retired"],
            "conversion_rate": [0.14, 0.11, 0.08, 0.13, 0.22],
        })
        total_predictions = 1204
        subscribe_rate = 0.123
        by_job = sample
    else:
        try:
            with st.spinner("Fetching results from the Gateway..."):
                raw_results = call_results_api()
            records_df = pd.DataFrame(raw_results)
            total_predictions = len(records_df)
            subscribe_rate = (records_df["prediction"] == "yes").mean() if len(records_df) else 0
            by_job = (
                records_df.assign(subscribed=records_df["prediction"] == "yes")
                .groupby("job")["subscribed"].mean()
                .reset_index()
                .rename(columns={"subscribed": "conversion_rate"})
            ) if "job" in records_df.columns else pd.DataFrame()
        except Exception as e:
            st.error(f"Could not load analytics from the Gateway: {e}")
            total_predictions, subscribe_rate, by_job = 0, 0, pd.DataFrame()

    kpi1, kpi2 = st.columns(2)
    kpi1.metric("Total predictions logged", f"{total_predictions:,}")
    kpi2.metric("Overall subscription rate", f"{subscribe_rate*100:.1f}%")

    if not by_job.empty:
        st.write("#### Conversion rate by job type")
        st.bar_chart(by_job.set_index("job"))
    else:
        st.info("No data to chart yet.")