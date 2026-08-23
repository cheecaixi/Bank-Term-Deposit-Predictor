# Bank Marketing Dashboard – Member C

**Owner:** Chee Cai Xi

## Project Overview

The Bank Marketing Dashboard is a **Streamlit-based microservice** for the Bank Marketing AI system.

It provides users with a web interface to:

- Predict term-deposit subscription likelihood for individual customers.
- Upload and process customer batches.
- View prediction results and campaign analytics.
- Monitor system health and service performance.

The Dashboard communicates **only with the API Gateway** and does not directly access the AI Inference, Database, or Monitoring services.

---

## Dashboard Features

The Dashboard consists of four main tabs:

### Tab 1 – Single Customer Prediction

- Search for an existing customer using a phone number.
- Load existing customer information from the database.
- Review and edit customer information.
- Generate a new term-deposit subscription prediction.
- Display subscription probability.
- Display campaign priority:
  - 🟢 High Priority
  - 🟡 Medium Priority
  - 🔴 Low Priority
- Display the previous prediction probability and priority for existing
  customers.

### Tab 2 – Batch Prediction

- Upload a customer CSV file.
- Process multiple customers in a batch.
- Generate predictions for multiple customers.
- Retrieve results using a batch ID.
- Display prediction probabilities and subscription outcomes.
- Prioritize customers based on their predicted subscription likelihood.

### Tab 3 – Results & Analytics

- View prediction results.
- Review customer prediction information.
- Analyse campaign and prediction outcomes.
- Identify customers with higher subscription likelihood.

### Tab 4 – System Monitoring

- View system and service health information.
- Monitor relevant service performance.
- Check the operational status of the backend system.

---

## System Architecture

```text
User / Web Browser
        │
        ▼
Dashboard Service
Streamlit :8501
        │
        │ HTTP
        ▼
API Gateway :8080
        │
        ├──► AI Inference Service
        ├──► Database Service
        └──► Monitoring Service
```        
---

## Microservice

| Component | Details |
|---|---|
| Service | Dashboard Service |
| Owner | Member C – Chee Cai Xi |
| Technology | Python, Streamlit, Pandas |
| Port | 8501 |
| Main file | `app.py` |
| Local Gateway | `http://localhost:8080` |
| Kubernetes Gateway | `http://api-gateway:8080` |

---

## Project Structure

```text
dashboard_service/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── README.md
└── k8s/
    ├── dashboard_deployment.yaml
    ├── dashboard_service.yaml
    ├── configmap.yaml
    └── dashboard_hpa.yaml   
```

## Requirements

Install the required Python dependencies:

```bash
cd dashboard_service
pip install -r requirements.txt    
```

## Environment Configuration

The Dashboard uses the `GATEWAY_URL` environment variable to connect to the API Gateway.

```text
Local:       http://localhost:8080
Docker:      http://host.docker.internal:8080
Kubernetes:  http://api-gateway:8080
```

## Run Locally

Start the Streamlit Dashboard:
```bash
streamlit run app.py
```
Open the Dashboard:
```text
http://localhost:8501
```

## Run with Docker

Build the Dashboard image:
```bash
docker build -t bank-dashboard .
```
Run the container:
```bash
docker run -p 8501:8501 -e GATEWAY_URL=http://host.docker.internal:8080 bank-dashboard
```
Open the Dashboard:
```text
http://localhost:8501
```
The Dashboard image is also available on Docker Hub:
```text
cheecaixi/dashboard:latest
```

## Docker Compose

Start the Dashboard:
```bash
docker compose up --build
```
Open the Dashboard:
```text
http://localhost:8501
```
The Dashboard connects to the API Gateway using:
```text
GATEWAY_URL=http://host.docker.internal:8080
```
Stop the Dashboard:
```bash
docker compose down
```

## Kubernetes Deployment

The Dashboard is deployed using four Kubernetes resources:

- Deployment
- Service
- ConfigMap
- Horizontal Pod Autoscaler (HPA)

Start Minikube:
```bash
minikube start
```
Check the cluster status:
```bash
minikube status
```
Deploy all Dashboard resources:
```bash
kubectl apply -f k8s/
```
Check the deployed resources:
```bash
kubectl get pods
kubectl get deployments
kubectl get services
kubectl get hpa
```
The Dashboard Deployment runs multiple replicas for improved availability.

The Horizontal Pod Autoscaler is configured with:
```text
Minimum replicas: 3
Maximum replicas: 5
CPU target: 70%
```

## Dataset
The system uses the Bank Marketing Dataset to predict whether customers are likely to subscribe to a term deposit.

## Known Limitations
- The Dashboard requires the API Gateway and backend services to be available.
- Batch prediction requires a valid CSV format.
- Kubernetes autoscaling requires the Kubernetes Metrics Server.