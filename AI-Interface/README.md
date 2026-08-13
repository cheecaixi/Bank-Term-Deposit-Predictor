## AI Inference Microservice

## Overview

The **AI Inference Microservice** is responsible for the machine learning component of the Bank Term Deposit Predictor platform. It processes the Bank Marketing dataset, trains and evaluates multiple classification models, and serves the selected trained model through a **FastAPI REST API**.

The service receives validated customer information from the **API Gateway (Member B)**, processes the input using the saved machine learning pipeline, and returns the predicted term deposit subscription outcome together with its probability.

---

## Microservice Architecture & Data Flow

```text
  ┌─────────────────────────────────────────┐
  │       Member C: Dashboard Service       │
  │         (Streamlit / Port 8501)         │
  └────────────────────┬────────────────────┘
                       │
                       ▼
  ┌─────────────────────────────────────────┐
  │        Member B: API Gateway            │
  │         (FastAPI / Port 8080)           │
  └────────────────────┬────────────────────┘
                       │
                       │ POST /predict
                       ▼
  ┌─────────────────────────────────────────┐
  │      Member A: AI Inference Service     │
  │         (FastAPI / Port 7000)           │
  │                                         │
  │  Preprocessing → Trained ML Model       │
  │               → Prediction              │
  └────────────────────┬────────────────────┘
                       │
                       │ Prediction Result
                       ▼
  ┌─────────────────────────────────────────┐
  │              API Gateway                │
  └─────────────────────────────────────────┘
```

---

## Machine Learning Pipeline

The AI component follows the following workflow:

```text
Bank Marketing Dataset
        ↓
Data Cleaning
        ↓
Feature Preparation
        ↓
Train and Test Split
        ↓
Class Imbalance Handling
        ↓
Model Training
        ↓
Model Comparison
        ↓
Best Model Selection
        ↓
Model Evaluation
        ↓
Save best_model.joblib
        ↓
FastAPI Inference Service
```

Four classification algorithms are currently compared:

* **Random Forest**
* **Gradient Boosting**
* **XGBoost**
* **LightGBM**

Model performance is evaluated using multiple metrics due to the imbalanced target distribution:

* Accuracy
* Precision
* Recall
* F1 Score
* ROC AUC

The selected model is saved as:

```text
models/best_model.joblib
```

---

## Feature Engineering & Preprocessing

The model uses **15 customer and campaign features**:

| Feature | Description |
| --- | --- |
| `age` | Customer age |
| `job` | Customer occupation |
| `marital` | Marital status |
| `education` | Education level |
| `default` | Credit default status |
| `balance` | Account balance |
| `housing` | Housing loan status |
| `loan` | Personal loan status |
| `contact` | Contact communication type |
| `day` | Last contact day |
| `month` | Last contact month |
| `campaign` | Number of contacts during the current campaign |
| `pdays` | Days since previous campaign contact |
| `previous` | Number of previous contacts |
| `poutcome` | Outcome of the previous marketing campaign |

Numerical features are standardized using `StandardScaler`, while categorical features are converted into numerical representations using `OneHotEncoder`.

The `duration` feature is intentionally excluded because the final call duration is only known after a marketing call has taken place. Excluding it allows the model to generate predictions using information available before or during customer targeting.

---

## AI Interface Folder Structure

```text
AI-Interface/
│
├── inference/
│   ├── __init__.py
│   ├── app.py
│   └── schemas.py
│
├── models/
│   └── best_model.joblib
│
├── cleaning.py
├── config.py
├── evaluate.py
├── features.py
├── train.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── README.md
```

### Main Components

| File | Purpose |
| --- | --- |
| `cleaning.py` | Loads and cleans the Bank Marketing dataset |
| `features.py` | Prepares numerical and categorical features |
| `train.py` | Trains, compares, selects, and saves the ML model |
| `evaluate.py` | Evaluates the final saved model and generates evaluation outputs |
| `config.py` | Stores shared paths, threshold, model information, and API configuration |
| `inference/schemas.py` | Defines and validates the customer input structure |
| `inference/app.py` | Provides the FastAPI inference endpoints |
| `models/best_model.joblib` | Stores the final trained machine learning pipeline |

---

## API Endpoints & Routes

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/` | Returns the AI Inference Service status |
| `GET` | `/health` | Checks whether the service is healthy and the trained model is loaded |
| `GET` | `/model-info` | Returns information about the deployed model |
| `POST` | `/predict` | Receives customer features and returns a subscription prediction |

The **API Gateway** communicates with the AI service through the `/predict` endpoint.

---

## Prediction Request

Example request to:

```text
POST /predict
```

```json
{
    "age": 35,
    "job": "management",
    "marital": "single",
    "education": "tertiary",
    "default": "no",
    "balance": 2500,
    "housing": "yes",
    "loan": "no",
    "contact": "cellular",
    "day": 15,
    "month": "may",
    "campaign": 2,
    "pdays": -1,
    "previous": 0,
    "poutcome": "unknown"
}
```

Example response:

```json
{
    "prediction": 1,
    "subscription": "Yes",
    "probability": 0.6732,
    "processing_time_seconds": 0.0081
}
```

---

## Tech Stack

* **Programming Language:** Python
* **Machine Learning:** Scikit Learn, XGBoost, LightGBM
* **Class Imbalance Handling:** Imbalanced Learn / SMOTE
* **Data Processing:** Pandas, NumPy
* **Model Persistence:** Joblib
* **API Framework:** FastAPI
* **API Server:** Uvicorn
* **Data Validation:** Pydantic
* **Evaluation & Visualization:** Matplotlib
* **Containerization:** Docker
* **Orchestration:** Kubernetes / Minikube

---

## How to Run Locally

### 1. Navigate to AI Interface

```bash
cd AI-Interface
```

### 2. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Train the Model

```bash
python train.py
```

The selected model will be saved to:

```text
models/best_model.joblib
```

### 4. Evaluate the Model

```bash
python evaluate.py
```

The evaluation process generates model metrics and visualizations including the confusion matrix, ROC curve, and precision recall curve.

### 5. Start the AI Inference Service

```bash
python -m uvicorn inference.app:app --reload --host 0.0.0.0 --port 7000
```

The service will run on:

```text
http://localhost:7000
```

### 6. Interactive Documentation

Swagger UI can be used to test the API:

```text
http://localhost:7000/docs
```

The `/health`, `/model-info`, and `/predict` endpoints can be tested directly from Swagger UI.

---

## API Gateway Integration

During local development, the **API Gateway (Member B)** can communicate with this service using:

```text
http://localhost:7000
```

Prediction requests are sent to:

```text
http://localhost:7000/predict
```

The local communication flow is:

```text
Dashboard
    ↓
API Gateway :8080
    ↓
AI Inference :7000
    ↓
Machine Learning Model
    ↓
Prediction Response
```

When deployed to Kubernetes, communication will use the Kubernetes Service name instead of `localhost`.

---

## Model Retraining

The machine learning model can be retrained without changing the API contract used by the other microservices.

To retrain:

```bash
python train.py
```

This updates:

```text
models/best_model.joblib
```

After retraining, the AI Inference Service must be restarted so that the updated model is loaded into memory.

As long as the `/predict` request and response formats remain unchanged, the **API Gateway and Dashboard do not require modification when the underlying machine learning model is updated**.

---

## Containerization & Kubernetes Setup

### 1. Build Docker Image

From inside the `AI-Interface` directory:

```bash
docker build -t ai-inference:v1 .
```

### 2. Run Container Locally

```bash
docker run -p 7000:7000 ai-inference:v1
```

### 3. Kubernetes Deployment

The AI Inference Service is designed to run as an independent Kubernetes workload and communicate with the API Gateway through a Kubernetes Service.

The inference workload can subsequently support multiple replicas and horizontal pod autoscaling to handle increased prediction traffic.
