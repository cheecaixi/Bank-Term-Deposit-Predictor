"""
Bank Marketing Dashboard Service
=================================
Student C's microservice. Talks ONLY to the API Gateway (Member B) --
never directly to Inference, Database, or Monitoring.

GATEWAY CONTRACT (matches Member B's actual FastAPI code)
-----------------------------------------------------------
  POST {GATEWAY_URL}/api/predict   -> single customer -> {"prediction":.., "probability":..}
  GET  {GATEWAY_URL}/api/results   -> list of all past logged predictions (raw, not aggregated)
  GET  {GATEWAY_URL}/api/logs      -> monitoring/system logs
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

st.set_page_config(page_title="Bank Marketing Dashboard", layout="wide", page_icon="💰")

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
# REAL API CALLS -- matches Member B's FastAPI gateway 
# ---------------------------------------------------------------
def call_predict_api(record: dict) -> dict:
    """
    Send a customer prediction request to Member B API Gateway.
    Member B forwards the 15 model features to Member A and
    saves the customer, campaign history and prediction to Member D.
    """
    url = f"{st.session_state.gateway_url}/api/predict"
    response = requests.post(url, json=record, timeout=10)
    response.raise_for_status()
    return response.json()

def search_customer_by_phone(phone_number: str):
    """
    Search Member D for an existing customer using their phone number.
    The request is routed through Member B.
    """
    url = (
        f"{st.session_state.gateway_url}"
        f"/api/customers/phone/{phone_number}"
    )
    response = requests.get(url,timeout=10)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()

def get_option_index(options, value):
    try:
        return options.index(value)
    except ValueError:
        return 0

def update_customer(customer_id: int, customer_data: dict):
    """
    Update an existing customer through Member B.
    """
    url = (
        f"{st.session_state.gateway_url}"
        f"/api/customers/{customer_id}"
    )
    response = requests.put(url, json=customer_data, timeout=10)
    response.raise_for_status()
    return response.json()

def call_results_api() -> list:
    """
    Retrieve historical prediction records through Member B.
    """
    url = f"{st.session_state.gateway_url}/api/results"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

# ---------------------------------------------------------------
# SINGLE CUSTOMER PREDICTION
# ---------------------------------------------------------------
def predict_one(record: dict):
    """
    Send one customer record to the API Gateway for prediction.
    """
    try:
        return call_predict_api(record)

    except Exception as e:
        st.error(
            f"Could not reach the API Gateway at "
            f"{st.session_state.gateway_url}: {e}"
        )

        return None

# ---------------------------------------------------------------
# BATCH CUSTOMER PREDICTION
# ---------------------------------------------------------------

def create_batch_upload(file_name: str, total_records: int) -> dict:
    """
    Create a batch record through the API Gateway.

    The API Gateway forwards this request to the Database Service
    and returns the newly created batch_id.
    """

    url = (
        f"{st.session_state.gateway_url}"
        f"/api/batch-uploads"
    )

    response = requests.post(
        url,
        json={
            "file_name": file_name,
            "total_records": total_records
        },
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def predict_many(
    df: pd.DataFrame,
    batch_id: int,
    progress_callback=None
):
    """
    Generate predictions for multiple customers through
    the API Gateway.

    Every customer is linked to the batch using batch_id.
    """

    results = []

    total_records = len(df)

    for index, row in df.iterrows():

        # ---------------------------------------------------------
        # Build request for API Gateway
        # ---------------------------------------------------------

        record = {

            # Customer identification
            "phone_number": str(
                row["phone_number"]
            ).strip(),

            # IMPORTANT:
            # Link this customer to the uploaded batch
            "batch_id": batch_id,

            # Customer features
            "age": int(row["age"]),
            "job": str(row["job"]),
            "marital": str(row["marital"]),
            "education": str(row["education"]),
            "default": str(row["default"]),
            "balance": float(row["balance"]),
            "housing": str(row["housing"]),
            "loan": str(row["loan"]),

            # Campaign features
            "contact": str(row["contact"]),
            "day": int(row["day"]),
            "month": str(row["month"]),
            "campaign": int(row["campaign"]),
            "pdays": int(row["pdays"]),
            "previous": int(row["previous"]),
            "poutcome": str(row["poutcome"])
        }

        try:

            result = call_predict_api(
                record
            )

        except requests.exceptions.HTTPError as e:

            if e.response is not None:

                st.error(
                    f"❌ Batch prediction failed at row "
                    f"{index + 1}.\n\n"
                    f"Status code: "
                    f"{e.response.status_code}\n\n"
                    f"API response:\n"
                    f"{e.response.text}"
                )

            else:

                st.error(
                    f"❌ Batch prediction failed at row "
                    f"{index + 1}: {e}"
                )

            return None

        except Exception as e:

            st.error(
                f"❌ Batch prediction stopped at row "
                f"{index + 1}: {e}"
            )

            return None

        results.append(
            result
        )

        # ---------------------------------------------------------
        # Update progress bar
        # ---------------------------------------------------------

        if progress_callback:

            progress_callback(
                len(results) / total_records
            )

    # ---------------------------------------------------------
    # Add prediction results to original dataframe
    # ---------------------------------------------------------

    out = df.copy()

    out["batch_id"] = batch_id

    out["probability"] = [
        result["probability"]
        for result in results
    ]

    out["prediction"] = [
        result["subscription"]
        for result in results
    ]

    return out


def get_batch_results(batch_id: int):
    """
    Retrieve customer prediction results for a specific batch
    through the API Gateway.
    """

    url = (
        f"{st.session_state.gateway_url}"
        f"/api/batch-uploads/{batch_id}/results"
    )

    response = requests.get(
        url,
        timeout=10
    )

    response.raise_for_status()

    return response.json()

# ---------------------------------------------------------------
# SIDEBAR -- API Gateway connection settings
# ---------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ System Settings")
    st.caption("For authorised system administrators")
    st.session_state.gateway_url = st.text_input(
        "Gateway URL",
        value=st.session_state.gateway_url,
        help=(
            "Internal address of the API Gateway.")
    )

    if st.button(
        "🔌 Test Connection",
        use_container_width=True
    ):
        try:
            response = requests.get(
                f"{st.session_state.gateway_url}/health",
                timeout=3
            )

            if response.status_code == 200:
                st.success("✅ API Gateway is connected.")
            else:
                st.warning(
                    f"⚠️ Gateway responded with "
                    f"status {response.status_code}."
                )

        except requests.exceptions.ConnectionError:
            st.error(
                "❌ Unable to connect to the API Gateway. "
                "Check that the Gateway service is running."
            )
        except requests.exceptions.Timeout:
            st.error(
                "❌ Connection timed out. "
                "Please check the Gateway address."
            )
        except Exception as error:
            st.error(
                f"❌ Connection test failed: {error}"
            )
    st.divider()

# ---------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------
st.title("💰 Bank Marketing AI Dashboard")
st.caption(f"🟢 System operational ")
st.write(
    "AI-assisted customer prioritisation for term deposit campaigns."
)
tab1, tab2, tab3 = st.tabs(["👨‍💼 Customer Prediction", "📂 Batch Prediction", "📊 Campaign Analytics"])

# ---------------------------------------------------------------
# TAB 1: SINGLE CUSTOMER PREDICTION
# ---------------------------------------------------------------
with tab1:

    st.subheader("👨‍💼 Customer Subscription Prediction")

    st.write(
        "Assess a customer's likelihood of subscribing to a term deposit."
    )

    st.info(
        "💡 Search the customer database before entering or reviewing customer details."
    )

    # =============================================================
    # 1. CUSTOMER SEARCH
    # =============================================================

    st.markdown("### 🔎 Find Customer")

    search_col1, search_col2 = st.columns([3, 1])

    with search_col1:

        phone_number = st.text_input(
            "Phone Number",
            placeholder="e.g. 91234567",
            help=(
                "Used to identify an existing customer. It is not used by the prediction model."
            )
        )

    with search_col2:

        st.write("")
        st.write("")

        search_clicked = st.button(
            "🔍 Search Customer",
            use_container_width=True
        )

    # =============================================================
    # SEARCH CUSTOMER
    # =============================================================

    if search_clicked:

        if not phone_number.strip():

            st.warning(
                "Please enter a phone number before searching."
            )

        else:

            with st.spinner("Searching customer records..."):

                try:

                    customer = search_customer_by_phone(
                        phone_number.strip()
                    )

                    if customer is None:

                        # Clear previous customer
                        st.session_state.found_customer = None
                        st.session_state.customer_id = None

                        st.info(
                            "ℹ️ No existing customer was found. " \
                            "You can enter the customer information manually below."
                        )

                    else:

                        st.session_state.found_customer = customer
                        st.session_state.customer_id = (
                            customer["customer_id"]
                        )

                        st.success(
                            f"✅ Existing customer found — "
                            f"Customer ID: "
                            f"{customer['customer_id']}"
                        )

                except Exception as e:

                    st.error(
                        f"❌ Unable to search customer: {e}"
                    )

    # =============================================================
    # EXISTING CUSTOMER STATUS
    # =============================================================

    existing_customer = st.session_state.get(
        "found_customer"
    )

    if existing_customer:

        st.caption(
            "Customer information has been loaded from the database. "
            "You can review and edit the information before generating "
            "a new prediction."
        )

    else:

        st.caption(
            "No customer record is currently loaded. "
            "Enter the customer information manually."
        )

    st.divider()

    # =============================================================
    # LOAD CUSTOMER DEFAULT VALUES
    # =============================================================

    if existing_customer:

        default_age = existing_customer.get(
            "age",
            35
        )

        default_job = existing_customer.get(
            "job",
            JOB_OPTIONS[0]
        )

        default_marital = existing_customer.get(
            "marital",
            MARITAL_OPTIONS[0]
        )

        default_education = existing_customer.get(
            "education",
            EDUCATION_OPTIONS[0]
        )

        default_default = existing_customer.get(
            "default",
            YES_NO_OPTIONS[0]
        )

        default_balance = existing_customer.get(
            "balance",
            1000.0
        )

        default_housing = existing_customer.get(
            "housing",
            YES_NO_OPTIONS[0]
        )

        default_loan = existing_customer.get(
            "loan",
            YES_NO_OPTIONS[0]
        )

    else:

        default_age = 35
        default_job = JOB_OPTIONS[0]
        default_marital = MARITAL_OPTIONS[0]
        default_education = EDUCATION_OPTIONS[0]
        default_default = YES_NO_OPTIONS[0]
        default_balance = 1000.0
        default_housing = YES_NO_OPTIONS[0]
        default_loan = YES_NO_OPTIONS[0]

    # =============================================================
    # CUSTOMER INFORMATION FORM
    # =============================================================

    with st.form("single_predict_form"):

        # =========================================================
        # CUSTOMER INFORMATION
        # =========================================================

        st.markdown("### 👤 Customer Information")

        st.caption(
            "Basic demographic and financial information."
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            age = st.number_input(
                "Age",
                min_value=18,
                max_value=100,
                value=int(default_age),
                help="Customer's age in years."
            )

        with col2:

            job = st.selectbox(
                "Job",
                JOB_OPTIONS,
                index=get_option_index(
                    JOB_OPTIONS,
                    default_job
                ),
                help="Customer's occupation."
            )

        with col3:

            marital = st.selectbox(
                "Marital Status",
                MARITAL_OPTIONS,
                index=get_option_index(
                    MARITAL_OPTIONS,
                    default_marital
                ),
                help="Customer's current marital status."
            )

        col1, col2, col3 = st.columns(3)

        with col1:

            education = st.selectbox(
                "Education",
                EDUCATION_OPTIONS,
                index=get_option_index(
                    EDUCATION_OPTIONS,
                    default_education
                ),
                help="Customer's highest level of education."
            )

        with col2:

            default = st.selectbox(
                "Credit Default",
                YES_NO_OPTIONS,
                index=get_option_index(
                    YES_NO_OPTIONS,
                    default_default
                ),
                help=(
                    "Whether the customer has credit "
                    "in default."
                )
            )

        st.divider()

        # =========================================================
        # FINANCIAL & LOAN INFORMATION
        # =========================================================

        st.markdown("### 💰 Financial & Loan Information")

        st.caption(
            "Information about the customer's account balance "
            "and existing loans."
        )

        col1, col2, col3 = st.columns(3)

        EUR_TO_SGD = 1.48

        with col1:

            balance = st.number_input(
                "Account Balance (€)",
                min_value=0.0,
                value=float(default_balance),
                step=100.0,
                help=(
                    "Customer's account balance in euros. "
                    "The EUR value is sent to the AI model."
                )
            )

            balance_sgd = balance * EUR_TO_SGD

            st.caption(
                f"≈ SGD ${balance_sgd:,.2f}"
            )

        with col2:

            housing = st.selectbox(
                "Housing Loan",
                YES_NO_OPTIONS,
                index=get_option_index(
                    YES_NO_OPTIONS,
                    default_housing
                ),
                help=(
                    "Whether the customer has "
                    "a housing loan."
                )
            )

        with col3:

            loan = st.selectbox(
                "Personal Loan",
                YES_NO_OPTIONS,
                index=get_option_index(
                    YES_NO_OPTIONS,
                    default_loan
                ),
                help=(
                    "Whether the customer has "
                    "a personal loan."
                )
            )

        st.divider()

        # =========================================================
        # CURRENT CAMPAIGN INFORMATION
        # =========================================================

        st.markdown("### 📞 Current Campaign Information")

        st.caption(
            "Information about the customer's contact history "
            "during the current and previous marketing campaigns."
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            contact = st.selectbox(
                "Contact Method",
                CONTACT_OPTIONS,
                help=(
                    "Communication method used to "
                    "contact the customer."
                )
            )

        with col2:

            day = st.number_input(
                "Last Contact Day of Month",
                min_value=1,
                max_value=31,
                value=15,
                help=(
                    "Day of the month when the customer "
                    "was last contacted."
                )
            )

        with col3:

            month = st.selectbox(
                "Last Contact Month",
                MONTH_OPTIONS,
                help=(
                    "Month when the customer "
                    "was last contacted."
                )
            )

        col1, col2, col3 = st.columns(3)

        with col1:

            campaign = st.number_input(
                "Contacts in Current Campaign",
                min_value=1,
                value=1,
                help=(
                    "Number of contacts made to this customer "
                    "during the current campaign, including "
                    "the latest contact."
                )
            )

        with col2:

            pdays = st.number_input(
                "Days Since Previous Contact",
                min_value=-1,
                value=-1,
                step=1,
                help=(
                    "-1 means the customer was not contacted "
                    "in a previous campaign. Values 0 or greater "
                    "represent the number of days since the previous "
                    "contact."
                )
            )

        with col3:

            previous = st.number_input(
                "Previous Campaign Contacts",
                min_value=0,
                value=0,
                help=(
                    "Number of contacts made to this customer "
                    "before the current campaign."
                )
            )

        col1, col2, col3 = st.columns(3)

        with col1:

            poutcome = st.selectbox(
                "Previous Campaign Outcome",
                POUTCOME_OPTIONS,
                help=(
                    "Outcome of the customer's "
                    "previous marketing campaign."
                )
            )

        st.divider()

        # =========================================================
        # PREDICTION BUTTON
        # =========================================================

        submitted = st.form_submit_button(
            "🔮 Generate Subscription Prediction",
            type="primary",
            use_container_width=True
        )

    # =============================================================
    # GENERATE PREDICTION
    # =============================================================

    if submitted:

        # ---------------------------------------------------------
        # Validate phone number
        # ---------------------------------------------------------

        if not phone_number.strip():

            st.error(
                "❌ Please enter a phone number before "
                "generating a prediction."
            )

        else:

            # -----------------------------------------------------
            # Create complete request
            # -----------------------------------------------------

            record = {

                # Customer identification
                "phone_number": phone_number.strip(),

                # Customer features
                "age": age,
                "job": job,
                "marital": marital,
                "education": education,
                "default": default,
                "balance": balance,
                "housing": housing,
                "loan": loan,

                # Campaign features
                "contact": contact,
                "day": day,
                "month": month,
                "campaign": campaign,
                "pdays": pdays,
                "previous": previous,
                "poutcome": poutcome
            }

            # -----------------------------------------------------
            # Call Member B
            # -----------------------------------------------------

            with st.spinner(
                "Sending customer information to the AI system..."
            ):

                result = predict_one(record)

            # -----------------------------------------------------
            # Display result
            # -----------------------------------------------------

            if result:

                probability = result["probability"]

                subscription = result["subscription"]

                processing_time = result.get(
                    "processing_time_seconds"
                )

                returned_customer_id = result.get(
                    "customer_id"
                )

                st.divider()

                st.markdown("### 📊 Prediction Result")

                # -------------------------------------------------
                # Customer identification
                # -------------------------------------------------

                if returned_customer_id is not None:

                    st.caption(
                        f"Customer ID: {returned_customer_id} "
                        f"• Phone: {phone_number}"
                    )

                # -------------------------------------------------
                # Result metrics
                # -------------------------------------------------

                result_col1, result_col2 = st.columns([1, 2])

                with result_col1:

                    st.metric(
                        "Subscription Probability",
                        f"{probability * 100:.1f}%"
                    )

                with result_col2:

                    st.write(
                        "**Predicted Likelihood**"
                    )

                    st.progress(
                        probability
                    )

                    if subscription == "Yes":

                        st.success(
                            "✅ Likely to Subscribe"
                        )

                    else:

                        st.warning(
                            "❌ Unlikely to Subscribe"
                        )

                # -------------------------------------------------
                # Interpretation
                # -------------------------------------------------

                if subscription == "Yes":

                    st.write(
                        "The AI model predicts a higher likelihood "
                        "that this customer will subscribe to the "
                        "term deposit. The customer may therefore "
                        "be considered a higher-priority prospect "
                        "for the marketing campaign."
                    )

                else:

                    st.write(
                        "The AI model predicts a lower likelihood "
                        "that this customer will subscribe to the "
                        "term deposit. The result can be considered "
                        "when deciding how to allocate campaign "
                        "calling resources."
                    )

                # -------------------------------------------------
                # Processing time
                # -------------------------------------------------

                if processing_time is not None:

                    st.caption(
                        f"Model processing time: "
                        f"{processing_time:.4f} seconds"
                    )

                # -------------------------------------------------
                # Save session history
                # -------------------------------------------------

                st.session_state.history.insert(
                    0,
                    {
                        "time": time.strftime(
                            "%H:%M:%S"
                        ),
                        "phone_number": phone_number,
                        "job": job,
                        "age": age,
                        "probability": probability,
                        "prediction": subscription
                    }
                )

    # =============================================================
    # RECENT PREDICTIONS
    # =============================================================

    if st.session_state.history:

        st.divider()

        st.markdown(
            "### 🕘 Recent Predictions"
        )

        st.caption(
            "Predictions generated during the current "
            "dashboard session."
        )

        hist_df = pd.DataFrame(
            st.session_state.history[:10]
        )

        st.dataframe(
            hist_df,
            use_container_width=True,
            hide_index=True
        )
        
# ---------------------------------------------------------------
# TAB 2: BATCH CUSTOMER PREDICTION
# ---------------------------------------------------------------
with tab2:

    st.subheader("📁 Batch Customer Prediction")

    st.write(
        "Upload a CSV containing multiple customer records to generate "
        "subscription predictions in bulk."
    )

    st.info(
        "💡 The uploaded file is registered as a batch through the API "
        "Gateway. Each customer is then processed with the Batch ID so "
        "the predictions can be linked to the uploaded batch."
    )

    # =============================================================
    # 1. UPLOAD CUSTOMER CSV
    # =============================================================

    st.markdown("### 📤 Upload Customer Data")

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help=(
            "Upload a CSV containing phone_number and all 15 "
            "customer features required by the prediction model."
        )
    )

    st.caption(
        "Required fields: phone_number, age, job, marital, education, "
        "default, balance, housing, loan, contact, day, month, "
        "campaign, pdays, previous, and poutcome."
    )

    # =============================================================
    # 2. PROCESS UPLOADED CSV
    # =============================================================

    if uploaded_file is not None:

        try:
            df = pd.read_csv(uploaded_file)

        except Exception as error:

            st.error(
                f"❌ Unable to read the CSV file: {error}"
            )

            df = None

        if df is not None:

            # -----------------------------------------------------
            # VALIDATE REQUIRED COLUMNS
            # -----------------------------------------------------

            REQUIRED_FIELDS = [
                "phone_number"
            ] + FEATURE_FIELDS

            missing_cols = [
                column
                for column in REQUIRED_FIELDS
                if column not in df.columns
            ]

            if missing_cols:

                st.error(
                    "❌ The uploaded CSV is missing the following "
                    "required columns:"
                )

                st.code(
                    ", ".join(missing_cols)
                )

                st.warning(
                    "Please check the CSV column names and upload "
                    "the file again."
                )

            # -----------------------------------------------------
            # VALIDATE EMPTY DATASET
            # -----------------------------------------------------

            elif df.empty:

                st.error(
                    "❌ The uploaded CSV does not contain any "
                    "customer records."
                )

            # -----------------------------------------------------
            # VALIDATE PHONE NUMBERS
            # -----------------------------------------------------

            elif df["phone_number"].isna().any():

                st.error(
                    "❌ Some customer records do not have a phone "
                    "number. Every customer must have a phone "
                    "number so the prediction can be linked to "
                    "the correct customer record."
                )

            elif (
                df["phone_number"]
                .astype(str)
                .str.strip()
                .eq("")
                .any()
            ):

                st.error(
                    "❌ Some customer records have an empty phone "
                    "number. Please provide a phone number for "
                    "every customer."
                )

            # -----------------------------------------------------
            # VALID DATA
            # -----------------------------------------------------

            else:

                st.success(
                    f"✅ Customer data loaded successfully — "
                    f"{len(df):,} records ready."
                )

                # =================================================
                # DATA PREVIEW
                # =================================================

                st.markdown("### 👀 Data Preview")

                st.caption(
                    "Review the uploaded customer records before "
                    "starting the batch prediction."
                )

                st.dataframe(
                    df.head(10),
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    f"Showing the first "
                    f"{min(10, len(df)):,} of "
                    f"{len(df):,} customer records."
                )

                st.divider()

                # =================================================
                # BATCH INFORMATION
                # =================================================

                st.markdown("### 📦 Batch Information")

                batch_col1, batch_col2 = st.columns(2)

                with batch_col1:

                    st.metric(
                        "File Name",
                        uploaded_file.name
                    )

                with batch_col2:

                    st.metric(
                        "Total Customers",
                        f"{len(df):,}"
                    )

                st.caption(
                    "A unique Batch ID will be created when you "
                    "start the prediction."
                )

                st.divider()

                # =================================================
                # RUN BATCH PREDICTION
                # =================================================

                st.markdown("### 🔮 Generate Batch Predictions")

                st.write(
                    "The system will create a Batch ID and send each "
                    "customer record through the API Gateway for "
                    "AI prediction."
                )

                if st.button(
                    "🔮 Run Batch Prediction",
                    type="primary",
                    use_container_width=True
                ):

                    try:

                        # =========================================
                        # STEP 1 — CREATE BATCH
                        # =========================================

                        with st.spinner(
                            "Creating batch..."
                        ):

                            batch = create_batch_upload(
                                file_name=uploaded_file.name,
                                total_records=len(df)
                            )

                        batch_id = int(
                            batch["batch_id"]
                        )

                        st.session_state.current_batch_id = (
                            batch_id
                        )

                        st.success(
                            f"📦 Batch created successfully — "
                            f"Batch ID: **{batch_id}**"
                        )

                        # =========================================
                        # STEP 2 — GENERATE PREDICTIONS
                        # =========================================

                        progress_bar = st.progress(
                            0.0,
                            text="Preparing customer records..."
                        )

                        def update_progress(frac):

                            progress_bar.progress(
                                frac,
                                text=(
                                    f"Generating predictions... "
                                    f"{int(frac * 100)}%"
                                )
                            )

                        results_df = predict_many(
                            df,
                            batch_id=batch_id,
                            progress_callback=update_progress
                        )

                        progress_bar.empty()

                        # =========================================
                        # STEP 3 — SAVE RESULTS
                        # =========================================

                        if results_df is not None:

                            st.session_state.last_batch_results = (
                                results_df
                            )

                            st.session_state.current_batch_id = (
                                batch_id
                            )

                            st.success(
                                f"✅ Batch prediction completed "
                                f"successfully for "
                                f"{len(results_df):,} customers."
                            )

                    except requests.exceptions.HTTPError as error:

                        st.error(
                            f"❌ API error while processing the batch: "
                            f"{error}"
                        )

                    except requests.exceptions.ConnectionError:

                        st.error(
                            "❌ Unable to connect to the API Gateway. "
                            "Please check that the Gateway service "
                            "is running."
                        )

                    except requests.exceptions.Timeout:

                        st.error(
                            "❌ The API Gateway request timed out. "
                            "Please try again."
                        )

                    except Exception as error:

                        st.error(
                            f"❌ Batch prediction failed: {error}"
                        )


    # =============================================================
    # 3. RETRIEVE EXISTING BATCH
    # =============================================================
    st.divider()

    st.markdown(
        "### 🔎 Retrieve Existing Batch"
    )

    st.write(
        "Enter a Batch ID to retrieve previously processed "
        "customer prediction results."
    )

    batch_id_input = st.number_input(
        "Batch ID",
        min_value=1,
        step=1,
        value=None,
        placeholder="Enter Batch ID"
    )

    if st.button(
        "🔎 Load Batch",
        use_container_width=True
    ):

        if batch_id_input is None:

            st.warning(
                "⚠️ Please enter a Batch ID."
            )

        else:

            batch_id = int(batch_id_input)

            try:

                with st.spinner(
                    f"Retrieving Batch {batch_id}..."
                ):

                    batch_data = get_batch_results(
                        batch_id
                    )

                # -------------------------------------------------
                # CHECK RESULTS
                # -------------------------------------------------

                results = batch_data.get(
                    "results",
                    []
                )

                if not results:

                    st.warning(
                        f"⚠️ Batch {batch_id} exists, "
                        f"but no prediction results were found."
                    )

                else:

                    # -------------------------------------------------
                    # CONVERT RESULTS TO DATAFRAME
                    # -------------------------------------------------

                    retrieved_df = pd.DataFrame(
                        results
                    )

                    # -------------------------------------------------
                    # SAVE RESULTS
                    # -------------------------------------------------

                    st.session_state.last_batch_results = (
                        retrieved_df
                    )

                    st.session_state.current_batch_id = (
                        batch_id
                    )

                    st.success(
                        f"✅ Batch {batch_id} loaded successfully — "
                        f"{len(retrieved_df):,} prediction results found."
                    )

                    st.rerun()

            except requests.exceptions.HTTPError as error:

                st.error(
                    f"❌ Unable to retrieve Batch "
                    f"{batch_id}: {error}"
                )

            except requests.exceptions.RequestException as error:

                st.error(
                    "❌ Unable to connect to the API Gateway."
                )

            except Exception as error:

                st.error(
                    f"❌ Failed to retrieve batch: {error}"
                )


    # =============================================================
    # 4. DISPLAY BATCH RESULTS
    # =============================================================

    if (
        "last_batch_results" in st.session_state
        and st.session_state.last_batch_results is not None
    ):

        results_df = (
            st.session_state.last_batch_results
        )

        st.divider()

        st.markdown("### 📈 Batch Prediction Results")

        # ---------------------------------------------------------
        # CURRENT BATCH
        # ---------------------------------------------------------

        current_batch_id = st.session_state.get(
            "current_batch_id"
        )

        if current_batch_id is not None:

            st.info(
                f"📦 Currently viewing Batch ID: "
                f"**{current_batch_id}**"
            )

        st.write(
            "Review the AI-generated predictions and identify "
            "customers with higher subscription probabilities."
        )

        # =========================================================
        # KPI SUMMARY
        # =========================================================

        k1, k2, k3 = st.columns(3)

        total_customers = len(
            results_df
        )

        # ---------------------------------------------------------
        # PREDICTED SUBSCRIBERS
        # ---------------------------------------------------------

        if "prediction" in results_df.columns:

            predicted_yes = int(
                (
                    results_df["prediction"]
                    .astype(str)
                    .str.lower()
                    == "yes"
                ).sum()
            )

        elif "subscription" in results_df.columns:

            predicted_yes = int(
                (
                    results_df["subscription"]
                    .astype(str)
                    .str.lower()
                    == "yes"
                ).sum()
            )

        else:

            predicted_yes = 0

        # ---------------------------------------------------------
        # SUBSCRIPTION RATE
        # ---------------------------------------------------------

        subscription_rate = (
            predicted_yes / total_customers
            if total_customers > 0
            else 0
        )

        # ---------------------------------------------------------
        # HIGH-POTENTIAL CUSTOMERS
        # ---------------------------------------------------------

        if "probability" in results_df.columns:

            high_potential = int(
                (
                    pd.to_numeric(
                        results_df["probability"],
                        errors="coerce"
                    )
                    >= 0.70
                ).sum()
            )

        else:

            high_potential = 0

        k1.metric(
            "Customers Scored",
            f"{total_customers:,}"
        )

        k2.metric(
            "Predicted Subscribers",
            f"{predicted_yes:,}"
        )

        k3.metric(
            "High-Potential Customers",
            f"{high_potential:,}",
            help=(
                "Customers with a predicted subscription "
                "probability of 70% or higher."
            )
        )

        st.caption(
            f"Predicted subscription rate: "
            f"{subscription_rate * 100:.1f}%"
        )

        st.divider()

        # =========================================================
        # EXPLORE RESULTS
        # =========================================================

        st.markdown("### 🔍 Explore Results")

        st.write(
            "Sort customers by subscription probability to "
            "prioritise potential prospects."
        )

        sort_choice = st.radio(
            "Sort results by",
            [
                "Highest probability first",
                "Lowest probability first",
                "Original order"
            ],
            horizontal=True
        )

        display_df = results_df.copy()

        # ---------------------------------------------------------
        # SORT RESULTS
        # ---------------------------------------------------------

        if "probability" in display_df.columns:

            display_df["probability"] = pd.to_numeric(
                display_df["probability"],
                errors="coerce"
            )

            if sort_choice == "Highest probability first":

                display_df = display_df.sort_values(
                    "probability",
                    ascending=False
                )

            elif sort_choice == "Lowest probability first":

                display_df = display_df.sort_values(
                    "probability",
                    ascending=True
                )

        # =========================================================
        # FORMAT RESULTS FOR DISPLAY
        # =========================================================

        if "probability" in display_df.columns:

            display_df["probability"] = (
                display_df["probability"] * 100
            ).round(1)

        display_df = display_df.rename(
            columns={
                "batch_id": "Batch ID",
                "customer_id": "Customer ID",
                "phone_number": "Phone Number",
                "probability": "Subscription Probability (%)",
                "prediction": "Predicted Subscription",
                "subscription": "Predicted Subscription"
            }
        )

        # =========================================================
        # DISPLAY TABLE
        # =========================================================

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # =========================================================
        # EXPORT RESULTS
        # =========================================================

        st.divider()

        st.markdown("### 📥 Export Results")

        st.write(
            "Download the current batch prediction results "
            "as a CSV file for campaign planning or further analysis."
        )

        csv_bytes = (
            display_df
            .to_csv(index=False)
            .encode("utf-8")
        )

        export_batch_id = st.session_state.get(
            "current_batch_id",
            "results"
        )

        st.download_button(
            "⬇️ Download Batch Results",
            data=csv_bytes,
            file_name=(
                f"batch_{export_batch_id}_predictions.csv"
            ),
            mime="text/csv",
            use_container_width=True
        )

# ---------------------------------------------------------------
# TAB 3: ANALYST VIEW
# ---------------------------------------------------------------
with tab3:
    st.subheader("📈 Campaign Analytics")

    st.write(
        "Review historical prediction results to understand customer "
        "subscription patterns and campaign performance. The analytics "
        "are based on prediction records logged by the system."
    )

    st.info(
        "💡 This view retrieves historical prediction records through "
        "the API Gateway and summarises the results for campaign analysis."
    )

    # =============================================================
    # FETCH HISTORICAL RESULTS
    # =============================================================
    with st.spinner("Loading campaign analytics..."):

        try:
            raw_results = call_results_api()

            records_df = pd.DataFrame(raw_results)

        except requests.exceptions.ConnectionError:
            st.error(
                "❌ Unable to connect to the API Gateway. "
                "Please make sure the Gateway and Database Service "
                "are running."
            )

            records_df = pd.DataFrame()

        except requests.exceptions.Timeout:
            st.error(
                "❌ The request timed out while retrieving "
                "historical prediction records."
            )

            records_df = pd.DataFrame()

        except Exception as error:
            st.error(
                f"❌ Unable to load campaign analytics: {error}"
            )

            records_df = pd.DataFrame()

    # =============================================================
    # ANALYTICS
    # =============================================================
    if not records_df.empty:

        # ---------------------------------------------------------
        # NORMALISE SUBSCRIPTION RESULT
        # ---------------------------------------------------------
        if "prediction" in records_df.columns:

            subscription_values = (
                records_df["prediction"]
                .astype(str)
                .str.lower()
            )

            predicted_subscribers = int(
                (subscription_values == "yes").sum()
            )

            total_predictions = len(records_df)

            subscription_rate = (
                predicted_subscribers / total_predictions
                if total_predictions > 0
                else 0
            )

        else:
            predicted_subscribers = 0
            total_predictions = len(records_df)
            subscription_rate = 0

        # =========================================================
        # KPI SUMMARY
        # =========================================================
        st.markdown("### 📊 Campaign Summary")

        kpi1, kpi2, kpi3 = st.columns(3)

        kpi1.metric(
            "Total Predictions",
            f"{total_predictions:,}"
        )

        kpi2.metric(
            "Predicted Subscribers",
            f"{predicted_subscribers:,}"
        )

        kpi3.metric(
            "Predicted Subscription Rate",
            f"{subscription_rate * 100:.1f}%"
        )

        st.divider()

        # =========================================================
        # PERFORMANCE BY JOB
        # =========================================================
        if "job" in records_df.columns:

            st.markdown(
                "### 👥 Predicted Subscription Rate by Job"
            )

            st.caption(
                "Percentage of customers predicted to subscribe "
                "within each job category."
            )

            records_df["subscribed"] = (
                records_df["prediction"]
                .astype(str)
                .str.lower()
                == "yes"
            )

            by_job = (
                records_df
                .groupby("job")["subscribed"]
                .mean()
                .reset_index()
            )

            by_job["conversion_rate"] = (
                by_job["subscribed"] * 100
            ).round(1)

            by_job = by_job.drop(
                columns=["subscribed"]
            )

            by_job = by_job.rename(
                columns={
                    "conversion_rate":
                    "Predicted Subscription Rate (%)"
                }
            )

            st.bar_chart(
                by_job.set_index("job")
            )

        else:
            st.info(
                "Job information is not available in the "
                "historical prediction records."
            )

        st.divider()

        # =========================================================
        # PREDICTION PROBABILITY DISTRIBUTION
        # =========================================================
        if "probability" in records_df.columns:

            st.markdown(
                "### 🎯 Prediction Probability Distribution"
            )

            st.caption(
                "Distribution of predicted probabilities generated "
                "by the AI model."
            )

            probability_df = records_df[
                ["probability"]
            ].copy()

            # Convert probability from decimal to percentage
            probability_df["probability"] = (
                probability_df["probability"] * 100
            )

            # Round probabilities into whole-number percentage groups
            probability_counts = (
                probability_df["probability"]
                .round(0)
                .value_counts()
                .sort_index()
                .rename_axis("Subscription Probability (%)")
                .reset_index(name="Number of Predictions")
            )

            st.bar_chart(
                probability_counts,
                x="Subscription Probability (%)",
                y="Number of Predictions"
            )

        # =========================================================
        # RECENT LOGGED PREDICTIONS
        # =========================================================
        st.divider()

        st.markdown(
            "### 🕘 Recent Prediction Records"
        )

        st.caption(
            "Most recently logged predictions retrieved from "
            "the Database Service."
        )

        recent_records = records_df.head(10)

        st.dataframe(
            recent_records,
            use_container_width=True,
            hide_index=True
        )

    else:

        # =========================================================
        # NO DATA
        # =========================================================
        st.info(
            "ℹ️ No historical prediction records are available yet."
        )

        st.write(
            "Generate predictions from the Customer Prediction or "
            "Batch Customer Prediction tabs. Once predictions are "
            "logged by the Database Service, they will appear here."
        )