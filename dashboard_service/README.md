# Dashboard Service — Bank Marketing AI Application

**Owner:** Student C  
**Project:** EGT307 — Bank Marketing & Customer Behaviour

## Overview

The Dashboard Service is a Streamlit web application that provides a user
interface for customer prediction and campaign analysis.

It contains three main tabs:

1. **Single Prediction** — Predicts one customer's likelihood of subscribing
   to a term deposit during a live customer call.
2. **Batch Prediction** — Uploads a CSV of multiple customers and generates
   predictions for the entire dataset.
3. **Analyst View** — Displays historical prediction statistics and
   customer-segment insights.

The Dashboard communicates with backend services **only through the API
Gateway**.

```text
[Dashboard]
     │
     ▼
[API Gateway]
     │
     ├──► [AI Inference Service]
     │
     ├──► [Database Service]
     │
     └──► [Monitoring Service]
```

---

## Main Features

### 1. Single Prediction

Designed for telesales agents or bank staff during a customer call.

The agent enters 15 customer features:

- Age
- Job
- Marital status
- Education
- Credit default
- Account balance
- Housing loan
- Personal loan
- Contact method
- Last contact day
- Last contact month
- Current campaign contacts
- Days since previous contact
- Previous campaign contacts
- Previous campaign outcome

The Dashboard sends the data to the API Gateway, which forwards it to the
AI Inference Service.

The result displays:

- Subscription probability
- Predicted outcome
- Prediction status

The prediction is also stored through the Database Service for later
analysis.

### 2. Batch Prediction

Allows users to upload a CSV containing multiple customer records.

The Dashboard:

1. Validates the required columns.
2. Displays a preview of the uploaded data.
3. Sends customers for prediction through the API Gateway.
4. Displays and sorts prediction results.
5. Allows the results to be downloaded as a CSV file.

Batch prediction is useful for analysing a larger customer list before or
during a marketing campaign.

### 3. Analyst View

Provides an overview of historical model predictions retrieved through the
API Gateway.

It can display:

- Total predictions
- Predicted subscription rate
- High-potential customers
- Prediction rate by job type
- Historical prediction records

> The subscription rate represents **model-predicted subscriptions**, not
> confirmed customer conversions.

---

## System Communication

### Single Prediction

```text
Customer
   │
   ▼
Dashboard
   │
   │ POST /api/predict
   ▼
API Gateway
   │
   ▼
AI Inference Service
   │
   ▼
Prediction Result
   │
   ├──► Database Service
   │
   ▼
Dashboard
```

### Analyst View

```text
Dashboard
   │
   │ GET /api/results
   ▼
API Gateway
   │
   ▼
Database Service
   │
   ▼
PostgreSQL
```

The Dashboard does not directly call the Inference, Database, or Monitoring
services.

---

## API Gateway Endpoints Used

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/predict` | Send one customer for prediction |
| `GET` | `/api/results` | Retrieve historical prediction records |

The API Gateway handles communication between the Dashboard and backend
microservices.

---

## Running Locally

### Prerequisites

- Python 3.11+
- API Gateway running
- Required backend services running

### Install Dependencies

```powershell
cd dashboard-service
python -m pip install -r requirements.txt
```

### Start Dashboard

```powershell
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

The Dashboard connects to the API Gateway at:

```text
http://localhost:8080
```

---

## Configuration

The API Gateway URL can be configured using the `GATEWAY_URL` environment
variable.

### PowerShell

```powershell
$env:GATEWAY_URL = "http://localhost:8080"
streamlit run app.py
```

| Variable | Purpose | Default |
|---|---|---|
| `GATEWAY_URL` | API Gateway address | `http://localhost:8080` |

---

## Docker

Build the image:

```powershell
docker build -t dashboard-service .
```

Run the Dashboard:

```powershell
docker run -p 8501:8501 `
  -e GATEWAY_URL=http://host.docker.internal:8080 `
  dashboard-service
```

Open:

```text
http://localhost:8501
```

---

## Service Dependencies

| Service | Purpose | Port |
|---|---|---:|
| Dashboard | User interface | 8501 |
| API Gateway | Request routing | 8080 |
| AI Inference | ML prediction | 7000 |
| Database Service | Customer and prediction storage | 8000 |
| PostgreSQL | Persistent database | 5432 |
| Monitoring Service | System monitoring and logging | 7002 |

---

## Project Structure

```text
dashboard-service/
│
├── app.py
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Current Status

The Dashboard Service provides:

- Real-time single customer prediction
- Batch customer prediction
- Historical prediction analytics
- API Gateway integration
- CSV upload and result download
- Docker support
- Kubernetes deployment support

The Dashboard is the **presentation layer** of the Bank Marketing
microservices system and relies on the API Gateway for backend communication.