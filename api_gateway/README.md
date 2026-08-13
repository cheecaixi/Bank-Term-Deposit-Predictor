
## API Gateway Microservice (Member B)

## Overview
The **API Gateway** serves as the central entry point and orchestrator for the Bank Term Deposit Predictor platform. It manages routing, incoming data validation, CORS configuration, error handling, and security between the **Dashboard Frontend (Member C)**, **AI Inference Engine (Member A)**, and **Database/Monitoring Services (Member D)**.

---

## Microservice Architecture & Data Flow

```text
  ┌─────────────────────────────────────────┐
  │      Member C: Dashboard Service        │
  │        (Streamlit UI / Port 8501)       │
  └────────────────────┬────────────────────┘
                       │
                       │ HTTP Requests (JSON)
                       ▼
  ┌─────────────────────────────────────────┐
  │       Member B: API Gateway             │
  │        (FastAPI / Port 8080)            │
  └────────┬───────────┬───────────┬────────┘
           │           │           │
 ┌─────────┘           │           └─────────┐
 ▼                     ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ Member A: AI      │ │ Member D: Database│ │ Member D: Monitor │
│ (Inference/7000)  │ │ Service (7001)    │ │ Service (7002)    │
└───────────────────┘ └───────────────────┘ └───────────────────┘

```

---

## API Endpoints & Routes

| Method | Route | Target Microservice | Description |
| --- | --- | --- | --- |
| `GET` | `/` | API Gateway | Root status and welcome message. |
| `GET` | `/health` | API Gateway | Liveness probe health check. |
| `POST` | `/api/predict` | Member A (AI) & Member D (DB) | Validates customer features, requests AI prediction, and persists result. |
| `GET` | `/api/results` | Member D (Database) | Retrieves historical prediction records. |
| `PUT` | `/api/customers/{id}` | Member D (Database) | Updates existing customer record details. |
| `DELETE` | `/api/customers/{id}` | Member D (Database) | Deletes a customer record. |
| `GET` | `/api/logs` | Member D (Monitoring) | Retrieves system latency and execution logs. |

---

## Tech Stack

* **Framework:** Python 3.10+, FastAPI
* **Async HTTP Client:** `httpx`
* **Data Validation:** Pydantic
* **Containerization:** Docker
* **Orchestration:** Kubernetes (Deployment, Service)

---

## How to Run Locally (GitHub Codespaces / Terminal)

### 1. Install Dependencies

```bash
cd api_gateway
pip install -r requirements.txt

```

### 2. Start the FastAPI Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

```

### 3. Interactive Documentation (Swagger UI)

Visit the interactive Swagger UI to view and test all routes:

```text
http://localhost:8080/docs

```

---

## Containerization & Kubernetes Setup

### 1. Build Docker Image

```bash
docker build -t api-gateway:v1 .

```

### 2. Run Container Locally

```bash
docker run -p 8080:8080 api-gateway:v1

```

### 3. Deploy to Kubernetes Cluster (Minikube)

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

```