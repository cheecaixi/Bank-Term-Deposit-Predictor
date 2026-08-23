"""
Bank Marketing Dashboard Service
=================================
Member C's microservice. Talks ONLY to the API Gateway (Member B) --
never directly to Inference, Database, or Monitoring.
"""

import os
import time
import pandas as pd
import requests
import streamlit as st
import hashlib

# ---------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------
GATEWAY_URL = os.getenv("GATEWAY_URL","http://localhost:8080")

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
    st.session_state.history = []  # Stores the recent single-customer predictions made during the current session
if "gateway_url" not in st.session_state:
    st.session_state.gateway_url = GATEWAY_URL #Stores the API Gateway address
if "current_batch_id" not in st.session_state:
    st.session_state.current_batch_id = None #Stores the Batch ID currently being viewed/processed
if "last_batch_results" not in st.session_state:
    st.session_state.last_batch_results = None #Stores the latest batch prediction results so they remain available after Streamlit reruns

# ---------------------------------------------------------------
# DEFAULT CUSTOMER FORM VALUES
# ---------------------------------------------------------------
if "age" not in st.session_state:
    st.session_state.age = 35

if "job" not in st.session_state:
    st.session_state.job = JOB_OPTIONS[0]

if "marital" not in st.session_state:
    st.session_state.marital = MARITAL_OPTIONS[0]

if "education" not in st.session_state:
    st.session_state.education = EDUCATION_OPTIONS[0]

if "default" not in st.session_state:
    st.session_state.default = YES_NO_OPTIONS[0]

if "balance" not in st.session_state:
    st.session_state.balance = 1000.0

if "housing" not in st.session_state:
    st.session_state.housing = YES_NO_OPTIONS[0]

if "loan" not in st.session_state:
    st.session_state.loan = YES_NO_OPTIONS[0]

if "contact" not in st.session_state:
    st.session_state.contact = CONTACT_OPTIONS[0]

if "day" not in st.session_state:
    st.session_state.day = 15

if "month" not in st.session_state:
    st.session_state.month = MONTH_OPTIONS[0]

if "campaign" not in st.session_state:
    st.session_state.campaign = 1

if "pdays" not in st.session_state:
    st.session_state.pdays = -1

if "previous" not in st.session_state:
    st.session_state.previous = 0

if "poutcome" not in st.session_state:
    st.session_state.poutcome = POUTCOME_OPTIONS[0]

# ---------------------------------------------------------------
# API CALLS -- matches Member B's FastAPI gateway 
# ---------------------------------------------------------------
def call_predict_api(record: dict) -> dict:
    """
    Send customer data to the API Gateway and return the prediction.
    """
    url = f"{st.session_state.gateway_url}/api/predict"
    response = requests.post(url, json=record, timeout=10)
    response.raise_for_status()
    return response.json()

def get_all_batches() -> list:
    """
    Retrieve all uploaded batches from the API Gateway.
    Used to check whether a CSV file has already been uploaded.
    """
    url = f"{st.session_state.gateway_url}/api/batch-uploads"
    response = requests.get(url,timeout=10)
    response.raise_for_status()
    return response.json()

def search_customer_by_phone(phone_number: str):
    """
    Retrieve an existing customer and ALL 15 prediction features
    using only the phone number.

    This does NOT access the batch CSV/dataset.
    The API Gateway retrieves the customer from the database.
    """

    url = (
        f"{st.session_state.gateway_url}"
        f"/api/customers/phone/{phone_number}"
    )

    response = requests.get(url, timeout=10)

    if response.status_code == 404:
        return None

    response.raise_for_status()

    customer = response.json()

    # Make sure the database/API returned all 15 model features.
    missing_features = [
        field
        for field in FEATURE_FIELDS
        if field not in customer or customer[field] is None
    ]

    if missing_features:
        raise ValueError(
            "Customer was found, but the API response is missing "
            "the following features: "
            + ", ".join(missing_features)
        )

    return customer

def get_option_index(options, value):
    try:
        return options.index(value)
    except ValueError:
        return 0

def update_customer(customer_id: int, customer_data: dict) -> dict:
    """
    Update an existing customer through the API Gateway.

    The API Gateway forwards the update to the Database Service
    using the customer's existing customer ID.

    Returns:
        Updated customer record.
    """
    url = (
        f"{st.session_state.gateway_url}"
        f"/api/customers/{customer_id}"
    )

    response = requests.put(
        url,
        json=customer_data,
        timeout=10
    )

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
    Send one manual customer prediction to the API Gateway.

    Manual predictions must never be associated with a batch.
    """
    try:
        manual_record = record.copy()

        # IMPORTANT:
        # Prevent an existing customer's batch_id from being reused.
        manual_record["batch_id"] = None

        return call_predict_api(manual_record)

    except Exception as e:
        st.error(
            f"Could not reach the API Gateway at "
            f"{st.session_state.gateway_url}: {e}"
        )

        return None

# ---------------------------------------------------------------
# BATCH CUSTOMER PREDICTION
# ---------------------------------------------------------------
def calculate_file_hash(uploaded_file) -> str:
    """
    Calculate SHA-256 hash of the uploaded CSV file.
    Used to identify duplicate CSV uploads.
    """
    file_bytes = uploaded_file.getvalue()
    return hashlib.sha256(file_bytes).hexdigest()

def create_batch_upload(file_name: str, total_records: int, file_hash: str) -> dict:
    """
    Create a new batch record through the API Gateway.
    The request is forwarded to the Database Service,
    which creates and returns the Batch ID.
    """
    url = f"{st.session_state.gateway_url}/api/batch-uploads"
    response = requests.post(url, 
                             json={"file_name": file_name,
                                   "total_records": total_records,
                                   "file_hash": file_hash},
                                   timeout=10)
    response.raise_for_status()
    return response.json()

def check_existing_batch(file_hash: str):
    """
    Check whether the uploaded CSV already exists
    using its SHA-256 file hash.
    """
    url = (
        f"{st.session_state.gateway_url}"
        f"/api/batch-uploads/check/{file_hash}"
    )

    response = requests.get(url, timeout=10)
    response.raise_for_status()
    result = response.json()

    if result.get("exists"):
        return result

    return None

def predict_many(df: pd.DataFrame,batch_id: int,progress_callback=None):
    """
    Generate predictions for all customers in a batch.

    All prediction requests are sent through the API Gateway.
    Temporary connection/server errors are retried.
    """
    results = []
    total_records = len(df)

    for index, row in df.iterrows():

        # ---------------------------------------------------------
        # BUILD CUSTOMER RECORD
        # ---------------------------------------------------------
        record = {"phone_number": str(row["phone_number"]).strip(),
            "batch_id": batch_id,
            "age": int(row["age"]),
            "job": str(row["job"]),
            "marital": str(row["marital"]),
            "education": str(row["education"]),
            "default": str(row["default"]),
            "balance": float(row["balance"]),
            "housing": str(row["housing"]),
            "loan": str(row["loan"]),
            "contact": str(row["contact"]),
            "day": int(row["day"]),
            "month": str(row["month"]),
            "campaign": int(row["campaign"]),
            "pdays": int(row["pdays"]),
            "previous": int(row["previous"]),
            "poutcome": str(row["poutcome"])
        }
        # ---------------------------------------------------------
        # RETRY PREDICTION REQUEST
        # ---------------------------------------------------------
        max_retries = 3
        result = None

        for attempt in range(max_retries):
            try:
                result = call_predict_api(record)
                break

            except requests.exceptions.HTTPError as error:
                status_code = (
                    error.response.status_code
                    if error.response is not None
                    else None
                )
                if (
                    status_code in [500, 502, 503, 504]
                    and attempt < max_retries - 1
                ):
                    wait_time = 2 ** attempt

                    st.warning(
                        f"⚠️ Row {index + 1}: "
                        f"API temporarily unavailable "
                        f"(HTTP {status_code}). "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                error_message = (
                    error.response.text
                    if error.response is not None
                    else str(error)
                )

                st.error(
                    f"❌ Batch prediction failed at row "
                    f"{index + 1}.\n\n"
                    f"Status code: {status_code}\n\n"
                    f"API response:\n{error_message}"
                )

                return None

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout
            ) as error:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    st.warning(
                        f"⚠️ Row {index + 1}: "
                        "API Gateway temporarily unavailable. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                st.error(
                    f"❌ Row {index + 1} failed after "
                    f"{max_retries} attempts.\n\n"
                    f"Error: {error}"
                )

                return None

            except Exception as error:
                st.error(
                    f"❌ Unexpected error at row "
                    f"{index + 1}: {error}"
                )
                return None

        # ---------------------------------------------------------
        # CHECK RESULT
        # ---------------------------------------------------------
        if result is None:
            st.error(
                f"❌ No prediction result received "
                f"for row {index + 1}."
            )
            return None

        # ---------------------------------------------------------
        # VALIDATE API RESPONSE
        # ---------------------------------------------------------
        if "probability" not in result:
            st.error(
                f"❌ API response for row {index + 1} "
                "does not contain 'probability'."
            )
            return None

        # Member B's Gateway contract uses "prediction".
        if "prediction" not in result:
            st.error(
                f"❌ API response for row {index + 1} "
                "does not contain 'prediction'."
            )
            return None

        # ---------------------------------------------------------
        # STORE RESULT
        # ---------------------------------------------------------
        results.append(result)

        # ---------------------------------------------------------
        # UPDATE PROGRESS
        # ---------------------------------------------------------
        if progress_callback and total_records > 0:
            progress_callback(len(results) / total_records)

    # -------------------------------------------------------------
    # BUILD RESULT DATAFRAME
    # -------------------------------------------------------------
    out = df.copy()
    out["batch_id"] = batch_id
    out["probability"] = [result["probability"]
                          for result in results]

    out["prediction"] = [result["prediction"]
                         for result in results]
    return out

def get_batch_results(batch_id: int):
    """
    Retrieve previously stored prediction results
    for a specific Batch ID through the API Gateway.
    """
    url = (
        f"{st.session_state.gateway_url}"
        f"/api/batch-uploads/"
        f"{batch_id}/results"
    )
    response = requests.get(url,timeout=10)
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
    "AI-assisted customer prioritisation for term deposit campaigns.")
tab1, tab2, tab3, tab4 = st.tabs(["👨‍💼 Customer Prediction", "📂 Batch Prediction", "📊 Campaign Analytics", "🖥️ System Monitoring"])

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

            st.error(
                "❌ Please enter a phone number before "
                "generating a prediction."
            )
        elif not phone_number.strip().isdigit() or len(phone_number.strip()) != 8:

            st.error(
                "❌ Invalid phone number. "
                "Phone number must contain exactly 8 digits."
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

                        st.session_state.age = 35
                        st.session_state.job = JOB_OPTIONS[0]
                        st.session_state.marital = MARITAL_OPTIONS[0]
                        st.session_state.education = EDUCATION_OPTIONS[0]
                        st.session_state.default = YES_NO_OPTIONS[0]
                        st.session_state.balance = 1000.0
                        st.session_state.balance_sgd = 1000.0 * 1.48
                        st.session_state.housing = YES_NO_OPTIONS[0]
                        st.session_state.loan = YES_NO_OPTIONS[0]
                        st.session_state.contact = CONTACT_OPTIONS[0]
                        st.session_state.day = 15
                        st.session_state.month = MONTH_OPTIONS[0]
                        st.session_state.campaign = 1
                        st.session_state.pdays = -1
                        st.session_state.previous = 0
                        st.session_state.poutcome = POUTCOME_OPTIONS[0]

                        st.info(
                            "ℹ️ No existing customer was found. " \
                            "You can enter the customer information manually below."
                        )

                    else:

                        # ---------------------------------------------------------
                        # Store the complete customer record
                        # ---------------------------------------------------------
                        st.session_state.found_customer = customer
                        st.session_state.customer_id = customer["customer_id"]

                        # ---------------------------------------------------------
                        # Load ALL 15 model features into widget state
                        # ---------------------------------------------------------
                        st.session_state.age = int(customer["age"])
                        st.session_state.job = str(customer["job"])
                        st.session_state.marital = str(customer["marital"])
                        st.session_state.education = str(customer["education"])
                        st.session_state.default = str(customer["default"])

                        st.session_state.balance = float(customer["balance"])
                        st.session_state.housing = str(customer["housing"])
                        st.session_state.loan = str(customer["loan"])

                        st.session_state.contact = str(customer["contact"])
                        st.session_state.day = int(customer["day"])
                        st.session_state.month = str(customer["month"])
                        st.session_state.campaign = int(customer["campaign"])
                        st.session_state.pdays = int(customer["pdays"])
                        st.session_state.previous = int(customer["previous"])
                        st.session_state.poutcome = str(customer["poutcome"])

                        st.success(
                            f"✅ Existing customer found — "
                            f"Customer ID: {customer['customer_id']}"
                        )

                except Exception as e:
                    st.error(
                        f"❌ Unable to search customer: {e}"
                    )

    # =============================================================
    # EXISTING CUSTOMER STATUS
    # =============================================================
    existing_customer = st.session_state.get("found_customer")
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

        # ---------------------------------------------------------
        # Customer / demographic information
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # Financial information
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # Campaign information
        # ---------------------------------------------------------
        default_contact = existing_customer.get(
            "contact",
            CONTACT_OPTIONS[0]
        )

        default_day = existing_customer.get(
            "day",
            15
        )

        default_month = existing_customer.get(
            "month",
            MONTH_OPTIONS[0]
        )

        default_campaign = existing_customer.get(
            "campaign",
            1
        )

        default_pdays = existing_customer.get(
            "pdays",
            -1
        )

        default_previous = existing_customer.get(
            "previous",
            0
        )

        default_poutcome = existing_customer.get(
            "poutcome",
            POUTCOME_OPTIONS[0]
        )

    else:

        # ---------------------------------------------------------
        # New customer defaults
        # ---------------------------------------------------------
        default_age = 35
        default_job = JOB_OPTIONS[0]
        default_marital = MARITAL_OPTIONS[0]
        default_education = EDUCATION_OPTIONS[0]
        default_default = YES_NO_OPTIONS[0]

        default_balance = 1000.0
        default_housing = YES_NO_OPTIONS[0]
        default_loan = YES_NO_OPTIONS[0]

        default_contact = CONTACT_OPTIONS[0]
        default_day = 15
        default_month = MONTH_OPTIONS[0]
        default_campaign = 1
        default_pdays = -1
        default_previous = 0
        default_poutcome = POUTCOME_OPTIONS[0]

    # =============================================================
    # CUSTOMER INFORMATION FORM
    # =============================================================
    with st.form("single_predict_form"):

        # =========================================================
        # CUSTOMER INFORMATION
        # =========================================================
        st.markdown("### 👤 Customer Information")

        st.caption("Basic demographic and financial information.")

        col1, col2, col3 = st.columns(3)

        with col1:
            age = st.number_input(
                "Age",
                min_value=18,
                max_value=100,
                key="age",
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
                key="job",
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
                key="marital",
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
                key="education",
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
                key="default",
                help=(
                    "Whether the customer fail to repay borrowed money."
                )
            )

        st.divider()

        # =========================================================
        # FINANCIAL & LOAN INFORMATION
        # =========================================================
        st.markdown("### 💰 Financial & Loan Information")

        st.caption("Information about the customer's account balance and existing loans.")

        col1, col2, col3 = st.columns(3)

        EUR_TO_SGD = 1.48

        with col1:
            balance_sgd = st.number_input(
                "Account Balance (SGD)",
                min_value=-1000000.0,
                value=float(default_balance) * EUR_TO_SGD,
                step=100.0,
                help=(
                    "Enter the customer's account balance in Singapore dollars. "
                    "The value will be converted to euros before being sent "
                    "to the AI model."
                )
            )

            balance = balance_sgd / EUR_TO_SGD

            st.caption(
                f"≈ EUR €{balance:,.2f} sent to AI model"
            )

        with col2:
            housing = st.selectbox(
                "Housing Loan",
                YES_NO_OPTIONS,
                index=get_option_index(
                    YES_NO_OPTIONS,
                    default_housing
                ),
                key="housing",
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
                key="loan",
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

        st.caption("Information about the customer's contact history during the current and previous marketing campaigns.")

        col1, col2, col3 = st.columns(3)

        with col1:
            contact = st.selectbox(
                "Contact Method",
                CONTACT_OPTIONS,
                index=get_option_index(
                    CONTACT_OPTIONS,
                    default_contact
                ),
                key="contact",
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
                value=int(default_day),
                key="day",
                help=(
                    "Day of the month when the customer "
                    "was last contacted."
                )
            )

        with col3:
            month = st.selectbox(
                "Last Contact Month",
                MONTH_OPTIONS,
                index=get_option_index(
                    MONTH_OPTIONS,
                    default_month
                ),
                key="month",
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
                key="campaign",
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
                key="pdays",
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
                key="previous",
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
                index=get_option_index(
                    POUTCOME_OPTIONS,
                    default_poutcome
                ),
                key="poutcome",
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
            # Build updated customer record
            # -----------------------------------------------------
            record = {
                "phone_number": phone_number.strip(),

                # Customer information
                "age": age,
                "job": job,
                "marital": marital,
                "education": education,
                "default": default,
                "balance": balance,
                "housing": housing,
                "loan": loan,

                # Campaign information
                "contact": contact,
                "day": day,
                "month": month,
                "campaign": campaign,
                "pdays": pdays,
                "previous": previous,
                "poutcome": poutcome
            }

            # -----------------------------------------------------
            # Update existing customer if one was found
            # -----------------------------------------------------
            existing_customer = st.session_state.get(
                "found_customer"
            )

            customer_id = st.session_state.get(
                "customer_id"
            )

            try:

                if existing_customer and customer_id is not None:

                    with st.spinner(
                        "Updating existing customer information..."
                    ):

                        update_customer(
                            customer_id=customer_id,
                            customer_data=record
                        )

                    st.success(
                        f"✅ Customer {customer_id} information "
                        "has been updated."
                    )

                # -------------------------------------------------
                # Generate prediction
                # -------------------------------------------------
                with st.spinner(
                    "Generating subscription prediction..."
                ):

                    result = predict_one(record)

                # -------------------------------------------------
                # Display prediction result
                # -------------------------------------------------
                if result:

                    probability = result["probability"]

                    subscription = result.get(
                        "subscription",
                        result.get("prediction")
                    )

                    processing_time = result.get(
                        "processing_time_seconds"
                    )

                    returned_customer_id = result.get(
                        "customer_id",
                        customer_id
                    )

                    st.divider()

                    st.markdown(
                        "### 📊 Prediction Result"
                    )

                    # -------------------------------------------------
                    # Customer identification
                    # -------------------------------------------------
                    if returned_customer_id is not None:

                        st.caption(
                            f"Customer ID: {returned_customer_id} "
                            f"• Phone: {phone_number}"
                        )

                    # -------------------------------------------------
                    # Probability
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

                        # ---------------------------------------------
                        # Campaign priority
                        # ---------------------------------------------
                        if probability >= 0.70:

                            priority = "🟢 High Priority"

                            priority_description = (
                                "The model estimates a strong likelihood "
                                "of subscription. Prioritise this customer "
                                "for campaign follow-up."
                            )

                        elif probability >= 0.60:

                            priority = "🟡 Medium Priority"

                            priority_description = (
                                "The model estimates a moderate likelihood "
                                "of subscription. Consider this customer "
                                "for campaign follow-up."
                            )

                        else:

                            priority = "🔴 Low Priority"

                            priority_description = (
                                "The model estimates a lower likelihood "
                                "of subscription. This does not mean "
                                "the customer will not subscribe."
                            )

                        st.write(
                            "**Campaign Priority**"
                        )

                        if probability >= 0.70:
                            st.success(priority)

                        elif probability >= 0.60:
                            st.warning(priority)

                        else:
                            st.error(priority)

                        st.write(
                            priority_description
                        )

                    # -------------------------------------------------
                    # Prediction interpretation
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
                            "time": time.strftime("%H:%M:%S"),
                            "phone_number": phone_number,
                            "job": job,
                            "age": age,
                            "probability": probability,
                            "prediction": subscription
                        }
                    )

            except requests.exceptions.HTTPError as error:

                status_code = (
                    error.response.status_code
                    if error.response is not None
                    else None
                )

                error_message = (
                    error.response.text
                    if error.response is not None
                    else str(error)
                )

                st.error(
                    f"❌ Customer update or prediction failed.\n\n"
                    f"HTTP Status: {status_code}\n\n"
                    f"Details: {error_message}"
                )

            except requests.exceptions.RequestException as error:

                st.error(
                    "❌ Unable to communicate with the API Gateway.\n\n"
                    f"Details: {error}"
                )

            except Exception as error:

                st.error(
                    f"❌ Unexpected error: {error}"
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
        "Upload a CSV file to generate predictions for multiple "
        "customers, or retrieve results from an existing Batch ID."
    )

    st.info(
        "💡 Previously uploaded CSV files cannot be uploaded again. "
        "If the file already exists, the system will retrieve its "
        "stored prediction results."
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

            # =====================================================
            # CALCULATE FILE HASH
            # =====================================================
            try:

                file_hash = calculate_file_hash(
                    uploaded_file
                )

            except Exception as error:

                st.error(
                    f"❌ Unable to calculate the file hash: {error}"
                )

                st.stop()

            # =====================================================
            # CHECK DUPLICATE FILE
            # =====================================================
            try:

                existing_batch = check_existing_batch(
                    file_hash
                )

            except requests.exceptions.HTTPError as error:

                status_code = (
                    error.response.status_code
                    if error.response is not None
                    else None
                )

                if status_code == 503:

                    st.error(
                        "❌ The batch upload service is currently "
                        "unavailable (HTTP 503).\n\n"
                        "Please make sure the API Gateway and "
                        "Database Service are running."
                    )

                elif status_code == 404:

                    st.error(
                        "❌ Batch upload check endpoint was not found "
                        "(HTTP 404).\n\n"
                        "Please check the API Gateway route."
                    )

                else:

                    st.error(
                        f"❌ API error while checking previous uploads.\n\n"
                        f"HTTP status: {status_code}\n\n"
                        f"Details: {error}"
                    )

                existing_batch = None

            except requests.exceptions.ConnectionError:

                st.error(
                    "❌ Unable to connect to the API Gateway.\n\n"
                    "Please check that the API Gateway is running."
                )

                existing_batch = None

            except requests.exceptions.Timeout:

                st.error(
                    "❌ The request timed out while checking "
                    "previous uploads."
                )

                existing_batch = None

            except Exception as error:

                st.error(
                    f"❌ Unexpected error while checking "
                    f"previous uploads:\n\n{error}"
                )

                existing_batch = None

            # =====================================================
            # SCENARIO A — DUPLICATE CSV
            # =====================================================
            if existing_batch is not None:

                try:

                    existing_batch_id = int(
                        existing_batch["batch_id"]
                    )

                except (KeyError, TypeError, ValueError) as error:

                    st.error(
                        f"❌ Invalid Batch ID returned by API: {error}"
                    )

                    st.stop()

                st.warning(
                    "⚠️ This CSV file has already been uploaded."
                )

                st.info(
                    f"📦 Existing Batch ID: **{existing_batch_id}**\n\n"
                    "The existing prediction results will be retrieved "
                    "instead of creating a duplicate batch."
                )

                # =================================================
                # RETRIEVE EXISTING RESULTS
                # =================================================
                try:

                    with st.spinner(
                        f"Loading Batch {existing_batch_id}..."
                    ):

                        existing_batch_data = (
                            get_batch_results(
                                existing_batch_id
                            )
                        )

                    existing_results = (
                        existing_batch_data.get(
                            "results",
                            []
                        )
                    )

                    # =============================================
                    # RESULTS FOUND
                    # =============================================
                    if existing_results:

                        existing_results_df = pd.DataFrame(
                            existing_results
                        )

                        st.session_state.last_batch_results = (
                            existing_results_df
                        )

                        st.session_state.current_batch_id = (
                            existing_batch_id
                        )

                        st.success(
                            f"✅ Batch {existing_batch_id} loaded — "
                            f"{len(existing_results_df):,} "
                            "prediction results found."
                        )

                    # =============================================
                    # NO RESULTS — RESUME BATCH
                    # =============================================
                    else:

                        st.warning(
                            f"⚠️ Batch {existing_batch_id} exists, "
                            "but no prediction results were found."
                        )

                        st.info(
                            "This batch appears to have been created "
                            "but the predictions were not completed."
                        )

                        if st.button(
                            f"🔄 Resume Batch "
                            f"{existing_batch_id} Prediction",
                            type="primary",
                            use_container_width=True
                        ):

                            progress_bar = None

                            try:

                                progress_bar = st.progress(
                                    0.0,
                                    text="Preparing customer records..."
                                )

                                def update_progress(frac):

                                    progress_bar.progress(
                                        frac,
                                        text=(
                                            "Generating predictions... "
                                            f"{int(frac * 100)}%"
                                        )
                                    )

                                results_df = predict_many(
                                    df,
                                    batch_id=existing_batch_id,
                                    progress_callback=update_progress
                                )

                                if progress_bar is not None:
                                    progress_bar.empty()

                                if results_df is not None:

                                    st.session_state.last_batch_results = (
                                        results_df
                                    )

                                    st.session_state.current_batch_id = (
                                        existing_batch_id
                                    )

                                    st.success(
                                        f"✅ Batch "
                                        f"{existing_batch_id} "
                                        f"prediction completed "
                                        f"successfully for "
                                        f"{len(results_df):,} "
                                        "customers."
                                    )
                                else:

                                    st.error(
                                        f"❌ Batch "
                                        f"{existing_batch_id} "
                                        "prediction was not completed."
                                    )
                            except Exception as error:

                                if progress_bar is not None:
                                    progress_bar.empty()

                                st.error(
                                    f"❌ Unable to resume Batch "
                                    f"{existing_batch_id}: {error}"
                                )
                except Exception as error:

                    st.error(
                        f"❌ Failed to retrieve Batch "
                        f"{existing_batch_id}: {error}"
                    )

            # =====================================================
            # SCENARIO B — NEW CSV
            # =====================================================
            else:
                st.success(
                    "🆕 This CSV file was not found in the database. "
                    "It can be processed as a new batch."
                )

                # =================================================
                # VALIDATE REQUIRED COLUMNS
                # =================================================
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
                        "❌ The uploaded CSV is missing "
                        "the following required columns:"
                    )

                    st.code(
                        ", ".join(missing_cols)
                    )

                # =================================================
                # EMPTY DATASET
                # =================================================
                elif df.empty:

                    st.error(
                        "❌ The uploaded CSV does not contain "
                        "any customer records."
                    )

                # =================================================
                # PHONE NUMBER VALIDATION
                # =================================================
                elif df["phone_number"].isna().any():

                    st.error(
                        "❌ Some customer records do not have "
                        "a phone number."
                    )

                elif (
                    df["phone_number"]
                    .astype(str)
                    .str.strip()
                    .eq("")
                    .any()
                ):
                    st.error(
                        "❌ Some customer records have "
                        "an empty phone number."
                    )

                # =================================================
                # VALID CSV
                # =================================================
                else:

                    st.success(
                        f"✅ Customer data loaded successfully — "
                        f"{len(df):,} records ready."
                    )

                    # =============================================
                    # DATA PREVIEW
                    # =============================================
                    st.markdown("### 👀 Data Preview")

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

                    # =============================================
                    # BATCH INFORMATION
                    # =============================================
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

                    st.divider()

                    # =============================================
                    # RUN BATCH
                    # =============================================
                    st.markdown("### 🔮 Generate Batch Predictions")

                    st.write(
                        "The system will create a new Batch ID, "
                        "generate predictions for every customer, "
                        "and store the results in the database."
                    )

                    if st.button(
                        "🔮 Run Batch Prediction",
                        type="primary",
                        use_container_width=True
                    ):

                        progress_bar = None
                        batch_id = None

                        try:

                            # =====================================
                            # CREATE BATCH
                            # =====================================
                            with st.spinner(
                                "Registering new batch..."
                            ):

                                batch = create_batch_upload(
                                    file_name=uploaded_file.name,
                                    total_records=len(df),
                                    file_hash=file_hash
                                )

                            if not batch:

                                st.error(
                                    "❌ The API returned an empty "
                                    "response while creating the batch."
                                )

                                st.stop()

                            if "batch_id" not in batch:

                                st.error(
                                    "❌ The API response does not "
                                    "contain a Batch ID."
                                )

                                st.stop()

                            batch_id = int(
                                batch["batch_id"]
                            )

                            st.info(
                                f"📦 New Batch ID assigned: "
                                f"**{batch_id}**"
                            )

                            st.session_state.current_batch_id = (
                                batch_id
                            )

                            # =====================================
                            # GENERATE PREDICTIONS
                            # =====================================
                            progress_bar = st.progress(
                                0.0,
                                text="Preparing customer records..."
                            )

                            def update_progress(frac):

                                progress_bar.progress(
                                    frac,
                                    text=(
                                        "Generating predictions... "
                                        f"{int(frac * 100)}%"
                                    )
                                )

                            results_df = predict_many(
                                df,
                                batch_id=batch_id,
                                progress_callback=update_progress
                            )

                            if progress_bar is not None:
                                progress_bar.empty()

                            # =====================================
                            # STORE RESULTS
                            # =====================================
                            if results_df is not None:

                                st.session_state.last_batch_results = (
                                    results_df
                                )

                                st.session_state.current_batch_id = (
                                    batch_id
                                )

                                st.success(
                                    f"✅ Batch {batch_id} prediction "
                                    f"completed successfully for "
                                    f"{len(results_df):,} customers."
                                )
                            else:

                                st.error(
                                    f"❌ Batch {batch_id} prediction "
                                    "was not completed."
                                )

                        except Exception as error:

                            if progress_bar is not None:
                                progress_bar.empty()

                            st.error(
                                f"❌ Batch prediction failed: {error}"
                            )

    # =============================================================
    # 3. RETRIEVE EXISTING BATCH
    # =============================================================
    st.divider()

    st.markdown("### 🔎 Retrieve Existing Batch")

    st.write(
        "Search the database for a previously processed Batch ID "
        "and retrieve its stored prediction results."
    )

    batch_id_input = st.number_input(
        "Batch ID",
        min_value=1,
        step=1,
        value=None,
        placeholder="Enter Batch ID"
    )

    if st.button("🔎 Load Batch", use_container_width=True):

        if batch_id_input is None:

            st.warning(
                "⚠️ Please enter a Batch ID."
            )

        else:
            batch_id = int(batch_id_input)

            try:

                with st.spinner(
                    f"Searching database for Batch {batch_id}..."
                ):

                    batch_data = get_batch_results(
                        batch_id
                    )

                if not isinstance(batch_data, dict):
                    st.error(
                        "❌ Invalid response received from "
                        "the API Gateway."
                    )

                else:
                    results = batch_data.get(
                        "results",
                        []
                    )

                    if not results:
                        st.warning(
                            f"⚠️ Batch {batch_id} was found, "
                            "but no prediction results are available."
                        )

                    else:
                        retrieved_df = pd.DataFrame(results)
                        st.session_state.last_batch_results = (retrieved_df)
                        st.session_state.current_batch_id = (batch_id)

                        st.success(
                            f"✅ Batch {batch_id} retrieved successfully — "
                            f"{len(retrieved_df):,} results found."
                        )
            except Exception as error:

                st.error(
                    f"❌ Failed to retrieve Batch "
                    f"{batch_id}: {error}"
                )

    # =============================================================
    # 4. DISPLAY BATCH RESULTS
    # =============================================================
    if (
        "last_batch_results" in st.session_state
        and st.session_state.last_batch_results is not None
    ):

        results_df = (
            st.session_state.last_batch_results.copy()
        )

        st.divider()

        st.markdown("### 📈 Batch Prediction Results")

        current_batch_id = st.session_state.get(
            "current_batch_id"
        )

        if current_batch_id is not None:

            st.info(
                f"📦 Currently viewing Batch ID: "
                f"**{current_batch_id}**"
            )

        # =========================================================
        # NORMALISE PREDICTION COLUMN
        # =========================================================
        if "prediction" in results_df.columns:

            prediction_column = "prediction"

        elif "subscription" in results_df.columns:

            prediction_column = "subscription"

        else:

            prediction_column = None

        # =========================================================
        # NORMALISE SUBSCRIPTION VALUES
        # =========================================================
        if prediction_column is not None:

            def is_subscriber(value):

                if pd.isna(value):
                    return False

                value_str = str(value).strip().lower()

                return value_str in [
                    "1",
                    "1.0",
                    "yes",
                    "true",
                    "subscribe",
                    "subscribed"
                ]

            results_df["_is_subscriber"] = (
                results_df[prediction_column]
                .apply(is_subscriber)
            )

        # =========================================================
        # CONVERT PROBABILITY
        # =========================================================
        if "probability" in results_df.columns:

            results_df["probability"] = pd.to_numeric(
                results_df["probability"],
                errors="coerce"
            )

        # =========================================================
        # CAMPAIGN PRIORITY
        # =========================================================
        if "probability" in results_df.columns:

            def get_priority(probability):

                if pd.isna(probability):

                    return "⚪ Unknown"

                if probability >= 0.70:

                    return "🟢 High Priority"

                elif probability >= 0.60:

                    return "🟡 Medium Priority"

                else:

                    return "🔴 Low Priority"

            results_df["Campaign Priority"] = (
                results_df["probability"]
                .apply(get_priority)
            )

        # =========================================================
        # KPI SUMMARY
        # =========================================================
        st.markdown("### 📊 Batch Summary")

        k1, k2, k3, k4 = st.columns(4)

        total_customers = len(results_df)

        # ---------------------------------------------------------
        # PREDICTED SUBSCRIBERS
        # ---------------------------------------------------------
        if "_is_subscriber" in results_df.columns:

            predicted_yes = int(
                results_df["_is_subscriber"].sum()
            )

        else:
            predicted_yes = 0

        subscription_rate = (
            predicted_yes / total_customers
            if total_customers > 0
            else 0
        )

        # ---------------------------------------------------------
        # PRIORITY COUNTS
        # ---------------------------------------------------------
        if "probability" in results_df.columns:

            high_priority = int(
                (
                    results_df["probability"]
                    >= 0.70
                ).sum()
            )

            medium_priority = int(
                (
                    (results_df["probability"] >= 0.60)
                    &
                    (results_df["probability"] < 0.70)
                ).sum()
            )

            low_priority = int(
                (
                    results_df["probability"] < 0.60
                ).sum()
            )

        else:
            high_priority = 0
            medium_priority = 0
            low_priority = 0

        # =========================================================
        # DISPLAY KPIs
        # =========================================================
        k1.metric(
            "Customers Scored",
            f"{total_customers:,}"
        )

        k2.metric(
            "Predicted Subscribers",
            f"{predicted_yes:,}"
        )

        k3.metric(
            "🟢 High Priority",
            f"{high_priority:,}"
        )

        k4.metric(
            "🟡 Medium Priority",
            f"{medium_priority:,}"
        )

        st.caption(
            f"Predicted subscription rate: "
            f"{subscription_rate * 100:.1f}%"
        )

        st.caption(
            f"🔴 Low Priority: "
            f"{low_priority:,} customers"
        )

        st.divider()

        # =========================================================
        # EXPLORE RESULTS
        # =========================================================
        st.markdown("### 🔍 Explore Results")

        st.write("Use campaign priority and subscription probability to identify customers for follow-up.")

        sort_choice = st.radio(
            "Sort results by",
            [
                "Highest priority first",
                "Highest probability first",
                "Lowest probability first",
                "Original order"
            ],
            horizontal=True
        )

        display_df = results_df.copy()

        # =========================================================
        # SORT RESULTS
        # =========================================================
        if sort_choice == "Highest priority first":

            if "probability" in display_df.columns:

                display_df["_priority_order"] = (
                    display_df["probability"]
                    .apply(
                        lambda x:
                        0
                        if not pd.isna(x) and x >= 0.70
                        else 1
                        if not pd.isna(x) and x >= 0.60
                        else 2
                        if not pd.isna(x)
                        else 3
                    )
                )

                display_df = display_df.sort_values(
                    [
                        "_priority_order",
                        "probability"
                    ],
                    ascending=[
                        True,
                        False
                    ]
                )

                display_df = display_df.drop(
                    columns=["_priority_order"]
                )

        elif (
            sort_choice == "Highest probability first"
            and "probability" in display_df.columns
        ):

            display_df = display_df.sort_values(
                "probability",
                ascending=False
            )

        elif (
            sort_choice == "Lowest probability first"
            and "probability" in display_df.columns
        ):

            display_df = display_df.sort_values(
                "probability",
                ascending=True
            )

        # =========================================================
        # FORMAT PROBABILITY
        # =========================================================
        if "probability" in display_df.columns:

            display_df["probability"] = (
                display_df["probability"] * 100
            ).round(1)

        # =========================================================
        # REMOVE INTERNAL COLUMN
        # =========================================================
        if "_is_subscriber" in display_df.columns:

            display_df = display_df.drop(columns=["_is_subscriber"])

        # =========================================================
        # RENAME COLUMNS
        # =========================================================
        display_df = display_df.rename(
            columns={
                "batch_id": "Batch ID",
                "customer_id": "Customer ID",
                "phone_number": "Phone Number",
                "probability":
                    "Subscription Probability (%)",
                "prediction":
                    "Predicted Subscription",
                "subscription":
                    "Predicted Subscription"
            }
        )

        # =========================================================
        # DISPLAY RESULTS
        # =========================================================
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        # =========================================================
        # PRIORITY EXPLANATION
        # =========================================================
        st.markdown("### 🎯 Campaign Priority")

        priority_col1, priority_col2, priority_col3 = (st.columns(3))

        with priority_col1:

            st.success(
                "🟢 **High Priority — ≥70%**"
            )

            st.caption(
                "Strong likelihood of subscription. "
                "Prioritise for campaign follow-up."
            )

        with priority_col2:

            st.warning(
                "🟡 **Medium Priority — 60–69%**"
            )

            st.caption(
                "Moderate likelihood of subscription. "
                "Consider for campaign follow-up."
            )

        with priority_col3:

            st.error(
                "🔴 **Low Priority — <60%**"
            )

            st.caption(
                "Lower likelihood of subscription. "
                "This does not mean the customer will not subscribe."
            )

        # =========================================================
        # EXPORT RESULTS
        # =========================================================
        st.divider()

        st.markdown(
            "### 📥 Export Results"
        )

        st.write(
            "Download the current batch prediction results "
            "with campaign priority."
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
        "Review historical prediction results to understand "
        "customer subscription patterns and campaign performance."
    )

    st.info(
        "💡 Analytics are based on prediction records retrieved "
        "through the API Gateway from the Database Service."
    )

    # =============================================================
    # FETCH HISTORICAL RESULTS
    # =============================================================
    with st.spinner(
        "Loading campaign analytics..."
    ):

        try:

            raw_results = call_results_api()

            records_df = pd.DataFrame(
                raw_results
            )

        except requests.exceptions.ConnectionError:

            st.error(
                "❌ Unable to connect to the API Gateway. "
                "Please make sure the Gateway and Database "
                "Service are running."
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

        # =========================================================
        # NORMALISE PREDICTION COLUMN
        # =========================================================
        if "prediction" in records_df.columns:

            prediction_column = "prediction"

        elif "subscription" in records_df.columns:

            prediction_column = "subscription"

        else:

            prediction_column = None

        # =========================================================
        # NORMALISE SUBSCRIPTION RESULT
        # =========================================================
        if prediction_column is not None:

            def is_subscriber(value):

                if pd.isna(value):

                    return False

                value_str = (
                    str(value)
                    .strip()
                    .lower()
                )

                return value_str in [
                    "1",
                    "1.0",
                    "yes",
                    "true",
                    "subscribe",
                    "subscribed"
                ]

            records_df["subscribed"] = (
                records_df[prediction_column]
                .apply(is_subscriber)
            )

        else:

            records_df["subscribed"] = False

        # =========================================================
        # KPI CALCULATIONS
        # =========================================================
        total_predictions = len(records_df)

        predicted_subscribers = int(records_df["subscribed"].sum())

        subscription_rate = (
            predicted_subscribers
            / total_predictions
            if total_predictions > 0
            else 0
        )

        # =========================================================
        # CAMPAIGN PRIORITY
        # =========================================================
        if "probability" in records_df.columns:

            records_df["probability"] = pd.to_numeric(
                records_df["probability"],
                errors="coerce"
            )

            def get_priority(probability):

                if pd.isna(probability):

                    return "⚪ Unknown"

                if probability >= 0.70:

                    return "🟢 High Priority"

                elif probability >= 0.60:

                    return "🟡 Medium Priority"

                else:

                    return "🔴 Low Priority"

            records_df["Campaign Priority"] = (
                records_df["probability"]
                .apply(get_priority)
            )

        # =========================================================
        # KPI SUMMARY
        # =========================================================
        st.markdown(
            "### 📊 Campaign Summary"
        )

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

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

        # =========================================================
        # PRIORITY COUNTS
        # =========================================================
        if "probability" in records_df.columns:

            high_priority = int(
                (
                    records_df["probability"]
                    >= 0.70
                ).sum()
            )

            medium_priority = int(
                (
                    (records_df["probability"] >= 0.60)
                    &
                    (records_df["probability"] < 0.70)
                ).sum()
            )

            low_priority = int(
                (
                    records_df["probability"] < 0.60
                ).sum()
            )

        else:

            high_priority = 0
            medium_priority = 0
            low_priority = 0

        kpi4.metric(
            "🟢 High Priority",
            f"{high_priority:,}"
        )

        st.caption(
            f"🟢 High Priority: {high_priority:,} | "
            f"🟡 Medium Priority: {medium_priority:,} | "
            f"🔴 Low Priority: {low_priority:,}"
        )

        st.divider()

        # =========================================================
        # PREDICTED SUBSCRIPTION BY JOB
        # =========================================================
        if "job" in records_df.columns:

            st.markdown("### 👥 Predicted Subscription Rate by Job")

            st.caption("Percentage of customers predicted to subscribe within each job category.")

            by_job = (
                records_df
                .groupby("job")["subscribed"]
                .mean()
                .reset_index()
            )

            by_job["Predicted Subscription Rate (%)"] = (
                by_job["subscribed"] * 100
            ).round(1)

            by_job = by_job.drop(
                columns=["subscribed"]
            )

            st.bar_chart(
                by_job.set_index("job")
            )

        else:
            st.info("Job information is not available in the historical prediction records.")

        st.divider()

        # =========================================================
        # PRIORITY DISTRIBUTION
        # =========================================================
        if "Campaign Priority" in records_df.columns:

            st.markdown("### 🎯 Campaign Priority Distribution")

            priority_counts = (
                records_df["Campaign Priority"]
                .value_counts()
                .reindex(
                    [
                        "🟢 High Priority",
                        "🟡 Medium Priority",
                        "🔴 Low Priority",
                        "⚪ Unknown"
                    ],
                    fill_value=0
                )
                .rename_axis("Campaign Priority")
                .reset_index(
                    name="Number of Customers"
                )
            )

            st.bar_chart(
                priority_counts.set_index(
                    "Campaign Priority"
                )
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
                "Distribution of subscription probabilities "
                "generated by the AI model."
            )

            probability_df = (
                records_df[
                    ["probability"]
                ]
                .dropna()
                .copy()
            )

            probability_df["probability"] = (
                probability_df["probability"] * 100
            )

            probability_counts = (
                probability_df["probability"]
                .round(0)
                .value_counts()
                .sort_index()
                .rename_axis(
                    "Subscription Probability (%)"
                )
                .reset_index(
                    name="Number of Predictions"
                )
            )

            st.bar_chart(
                probability_counts,
                x="Subscription Probability (%)",
                y="Number of Predictions"
            )

        st.divider()

        # =========================================================
        # SUBSCRIPTION RESULT DISTRIBUTION
        # =========================================================
        st.markdown("### 📌 Prediction Outcome")

        outcome_counts = pd.DataFrame(
            {
                "Prediction": [
                    "Predicted Subscribe",
                    "Predicted No Subscribe"
                ],
                "Customers": [
                    predicted_subscribers,
                    total_predictions - predicted_subscribers
                ]
            }
        )

        st.bar_chart(
            outcome_counts.set_index(
                "Prediction"
            )
        )

        st.divider()

        # =========================================================
        # RECENT PREDICTION RECORDS
        # =========================================================
        st.markdown("### 🕘 Recent Prediction Records")

        st.caption(
            "Most recently logged predictions retrieved "
            "from the Database Service."
        )

        recent_records = (
            records_df
            .head(10)
            .copy()
        )

        # Do not expose internal helper column
        if "subscribed" in recent_records.columns:

            recent_records = recent_records.drop(
                columns=["subscribed"]
            )

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
            "Generate predictions from the Customer Prediction "
            "or Batch Customer Prediction tabs. Once predictions "
            "are logged by the Database Service, they will appear here."
        )

# ============================================================
# TAB 4 — SYSTEM MONITORING
# ============================================================
with tab4:

    st.header("🖥️ System Monitoring")
    st.caption("Monitor microservice health, system metrics and recent logs.")

    # --------------------------------------------------------
    # Helper function
    # --------------------------------------------------------
    def get_monitoring_data(endpoint):
        try:
            response = requests.get(
                f"{st.session_state.gateway_url}{endpoint}",
                timeout=5
            )

            if response.status_code == 200:
                return response.json()

            st.error(
                f"Monitoring request failed "
                f"(HTTP {response.status_code})"
            )
            return None

        except requests.exceptions.RequestException as e:
            st.error(f"Unable to connect to API Gateway: {e}")
            return None

    # --------------------------------------------------------
    # Refresh button
    # --------------------------------------------------------
    col_refresh, col_status = st.columns([1, 4])

    with col_refresh:
        refresh = st.button(
            "🔄 Refresh",
            key="monitoring_refresh"
        )

    with col_status:
        st.info(
            "Monitoring data is retrieved through the API Gateway."
        )

    # --------------------------------------------------------
    # SERVICE STATUS
    # --------------------------------------------------------
    st.subheader("🟢 Service Status")

    status_data = get_monitoring_data(
        "/api/monitoring/status"
    )

    if status_data:

        overall_status = status_data.get(
            "overall_status",
            "unknown"
        )

        services = status_data.get(
            "services",
            []
        )

        # Overall status
        if overall_status == "healthy":
            st.success("🟢 All monitored services are healthy.")
        else:
            st.warning(
                "🟠 System status is degraded. "
                "Check the service status below."
            )

        # Service status cards
        if services:

            cols = st.columns(len(services))

            for col, service in zip(cols, services):

                with col:

                    service_name = service.get(
                        "service",
                        "Unknown"
                    )

                    service_status = service.get(
                        "status",
                        "unknown"
                    )

                    response_time = service.get(
                        "response_time_ms",
                        0
                    )

                    if service_status == "healthy":
                        st.success(
                            f"🟢 {service_name}"
                        )
                    else:
                        st.error(
                            f"🔴 {service_name}"
                        )

                    st.metric(
                        "Response Time",
                        f"{response_time} ms"
                    )

                    status_code = service.get(
                        "status_code"
                    )

                    if status_code:
                        st.caption(
                            f"HTTP Status: {status_code}"
                        )

    else:
        st.warning(
            "Unable to retrieve service status."
        )

    st.divider()

    # --------------------------------------------------------
    # SYSTEM METRICS
    # --------------------------------------------------------
    st.subheader("📊 System Metrics")

    metrics_data = get_monitoring_data(
        "/api/monitoring/metrics"
    )

    if metrics_data:

        total_logs = metrics_data.get(
            "total_logs",
            0
        )

        total_errors = metrics_data.get(
            "total_errors",
            0
        )

        total_warnings = metrics_data.get(
            "total_warnings",
            0
        )

        average_response = metrics_data.get(
            "average_response_time_ms"
        )

        maximum_response = metrics_data.get(
            "maximum_response_time_ms"
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "Total Logs",
                total_logs
            )

        with col2:
            st.metric(
                "Errors",
                total_errors
            )

        with col3:
            st.metric(
                "Warnings",
                total_warnings
            )

        with col4:
            if average_response is not None:
                st.metric(
                    "Avg Response",
                    f"{average_response:.2f} ms"
                )
            else:
                st.metric(
                    "Avg Response",
                    "N/A"
                )

        with col5:
            if maximum_response is not None:
                st.metric(
                    "Max Response",
                    f"{maximum_response:.2f} ms"
                )
            else:
                st.metric(
                    "Max Response",
                    "N/A"
                )

        # ----------------------------------------------------
        # Metrics by service
        # ----------------------------------------------------
        by_service = metrics_data.get(
            "by_service",
            []
        )

        if by_service:

            st.subheader("📈 Metrics by Service")

            service_df = pd.DataFrame(
                by_service
            )

            st.dataframe(
                service_df,
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning(
            "Unable to retrieve system metrics."
        )

    st.divider()

    # --------------------------------------------------------
    # SYSTEM LOGS
    # --------------------------------------------------------
    st.subheader("📋 Recent System Logs")

    logs_data = get_monitoring_data(
        "/api/logs?limit=100"
    )

    if logs_data:

        if isinstance(logs_data, list):

            logs_df = pd.DataFrame(
                logs_data
            )

        else:

            logs_df = pd.DataFrame(
                logs_data
            )

        if not logs_df.empty:

            # ----------------------------------------------
            # Log filters
            # ----------------------------------------------
            filter_col1, filter_col2 = st.columns(2)

            with filter_col1:

                services = ["All"]

                if "service" in logs_df.columns:
                    services += sorted(
                        logs_df["service"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                selected_service = st.selectbox(
                    "Filter by Service",
                    services,
                    key="monitoring_service_filter"
                )

            with filter_col2:

                levels = ["All"]

                if "level" in logs_df.columns:
                    levels += sorted(
                        logs_df["level"]
                        .dropna()
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                selected_level = st.selectbox(
                    "Filter by Level",
                    levels,
                    key="monitoring_level_filter"
                )

            # ----------------------------------------------
            # Apply filters
            # ----------------------------------------------
            filtered_logs = logs_df.copy()

            if (
                selected_service != "All"
                and "service" in filtered_logs.columns
            ):
                filtered_logs = filtered_logs[
                    filtered_logs["service"]
                    == selected_service
                ]

            if (
                selected_level != "All"
                and "level" in filtered_logs.columns
            ):
                filtered_logs = filtered_logs[
                    filtered_logs["level"]
                    == selected_level
                ]

            # ----------------------------------------------
            # Display logs
            # ----------------------------------------------
            st.dataframe(
                filtered_logs,
                use_container_width=True,
                hide_index=True
            )
            st.caption(
                f"Showing {len(filtered_logs)} log(s)"
            )
        else:
            st.info(
                "No system logs available."
            )
    else:
        st.warning(
            "Unable to retrieve system logs."
        )        