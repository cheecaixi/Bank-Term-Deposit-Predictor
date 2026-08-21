# AI Inference Microservice

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
├── inference/
│   ├── __init__.py
│   ├── app.py
│   └── schemas.py
├── training/
│   ├── __init__.py
│   ├── cleaning.py
│   ├── evaluate.py
│   ├── features.py
│   └── train.py
├── models/
│   └── best_model.joblib
├── results/
│   └── evaluation/
│       ├── confusion_matrix.png
│       ├── feature_importance.csv
│       ├── feature_importance.png
│       ├── final_metrics.csv
│       ├── precision_recall_curve.png
│       └── roc_curve.png
├── k8s/
│   └── ai-inference.yaml
├── .dockerignore
├── config.py
├── docker-compose.yaml
├── Dockerfile
├── requirements.txt
└── README.md
```

### Main Components

| File | Purpose |
| --- | --- |
| `training/cleaning.py` | Loads and cleans the Bank Marketing dataset |
| `training/features.py` | Prepares numerical and categorical features and builds the preprocessing pipeline |
| `training/train.py` | Trains, compares, selects, and saves the ML model |
| `training/evaluate.py` | Evaluates the saved model and generates metrics and visualizations |
| `config.py` | Stores shared paths, threshold, model information, and API configuration |
| `inference/schemas.py` | Defines and validates the customer input structure |
| `inference/app.py` | Provides the FastAPI inference endpoints |
| `models/best_model.joblib` | Stores the final trained machine learning pipeline |
| `docker-compose.yaml` | Builds, runs, and health-checks the service locally with Docker Compose |
| `k8s/ai-inference.yaml` | Defines the Kubernetes Deployment and internal Service |

---

## API Endpoints & Routes

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/` | Returns the AI Inference Service status |
| `GET` | `/health` | Returns HTTP 200 when the model is loaded, or HTTP 503 when it is unavailable |
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
* **Machine Learning:** Scikit-learn, XGBoost, LightGBM
* **Class Imbalance Handling:** imbalanced-learn / SMOTE
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
python -m training.train
```

The selected model will be saved to:

```text
models/best_model.joblib
```

### 4. Evaluate the Model

```bash
python -m training.evaluate
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

The API Gateway should use the following internal URL in Kubernetes:

```text
http://ai-inference-service:7000
```

---

## Model Retraining

The machine learning model can be retrained without changing the API contract used by the other microservices.

To retrain:

```bash
python -m training.train
```

This updates:

```text
models/best_model.joblib
```

After retraining, the AI Inference Service must be restarted so that the updated model is loaded into memory.

As long as the `/predict` request and response formats remain unchanged, the **API Gateway and Dashboard do not require modification when the underlying machine learning model is updated**.

---

## Docker

Run all Docker commands in this section from inside the `AI-Interface` directory.

### Run with Docker Compose

Build and start the service in the background:

```bash
docker compose up -d --build
```

Check the container and health status:

```bash
docker compose ps
```

View recent logs:

```bash
docker compose logs --tail 30 ai-inference
```

Stop and remove the Compose container and network:

```bash
docker compose down
```

### Build and Run with Docker

Build the local image:

```bash
docker build -t ai-inference:v1 .
```

Run the image:

```bash
docker run --rm -p 7000:7000 ai-inference:v1
```

### Publish to Docker Hub

The Kubernetes manifest uses `amandalobo1/ai-inference:v1`. Tag and push the tested local image before deploying it:

```bash
docker tag ai-inference:v1 amandalobo1/ai-inference:v1
docker login
docker push amandalobo1/ai-inference:v1
```

Use a new version tag whenever the application, dependencies, or trained model changes.

---

## Kubernetes Deployment

The manifest at `k8s/ai-inference.yaml` contains:

* A two-replica `Deployment` for the inference API.
* CPU and memory requests and limits.
* Readiness and liveness probes using `/health`.
* A `ClusterIP` Service named `ai-inference-service` on port 7000.

The current service does not require a ConfigMap because it has no environment-specific runtime settings. Add one only if settings such as the prediction threshold are changed to read from environment variables.

Start Minikube and deploy the service:

```bash
minikube start
kubectl apply -f k8s/ai-inference.yaml
```

Check the deployment:

```bash
kubectl rollout status deployment/ai-inference
kubectl get pods -l app=ai-inference
kubectl get service ai-inference-service
```

Inspect service logs if a pod is not ready:

```bash
kubectl logs -l app=ai-inference --tail=100
```

Remove the Kubernetes resources:

```bash
kubectl delete -f k8s/ai-inference.yaml
```

---

## Verification Checklist

Before committing or deploying changes:

1. Run `python -m training.train` only when the model needs to be retrained.
2. Run `python -m training.evaluate` to regenerate evaluation results.
3. Run `docker compose up -d --build --force-recreate`.
4. Confirm `docker compose ps` reports the container as healthy.
5. Confirm `http://localhost:7000/health` returns a healthy response.
6. Test a prediction through `http://localhost:7000/docs`.
7. Push the versioned image before applying the Kubernetes manifest.

---

## Known Limitations

* The inference service requires `models/best_model.joblib` to start successfully.
* The saved model must be loaded with compatible dependency versions; `scikit-learn` is pinned in `requirements.txt` for model compatibility.
* Training and evaluation expect the dataset at `../data/Bank_Marketing_Dataset.csv` relative to this service directory.
* The Kubernetes Service is internal to the cluster. External clients should communicate through the API Gateway.
