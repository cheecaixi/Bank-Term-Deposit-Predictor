# Bank Marketing Dashboard – Member C

## Project Overview
A Streamlit dashboard microservice for the Bank Marketing AI system. It allows users to:
- Predict subscription likelihood for individual customers.
- Upload and process customer batches.
- View campaign analytics and prediction results.

The dashboard communicates only with the API Gateway.

## System Architecture

The project follows a microservices architecture consisting of independent services.

```text
                    ┌─────────────────────┐
                    │       User          │
                    │    Web Browser      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Dashboard Service   │
                    │     Streamlit       │
                    │       :8501         │
                    └──────────┬──────────┘
                               │
                               │ HTTP
                               ▼
                    ┌─────────────────────┐
                    │    API Gateway      │
                    │       :8080         │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
       │ AI Inference│  │  Database   │  │  Monitoring  │
       │   Service   │  │   Service   │  │   Service    │
       └─────────────┘  └─────────────┘  └──────────────┘
```

## Microservice
Dashboard Service (Member C)
- Technology: Python, Streamlit, Pandas
- Port: 8501
- Gateway: http://localhost:8080
- Main file: app.py

## Project Files
dashboard_service/
├── app.py
├── requirements.txt
├── Dockerfile
├── README.md
├── .dockerignore
├── .gitignore
└── k8s/
    ├── dashboard_deployment.yaml
    └── dashboard_service.yaml

## Requirements
Install dependencies:
```text
pip install -r requirements.txt
```

Main dependencies:
- Streamlit
- Pandas
- Requests

hashlib is included in Python's standard library and does not need to be added to requirements.txt.

## Run Locally
```text
streamlit run app.py
```

Open:
```text
http://localhost:8501
```

## Run with Docker
Build:
```text
docker build -t bank-dashboard .
```

Run:
```text
docker run -p 8501:8501 -e GATEWAY_URL=http://host.docker.internal:8080 bank-dashboard
```

## Kubernetes
Deploy using the Dashboard Deployment and Service YAML files:
```text
kubectl apply -f dashboard-deployment.yaml
kubectl apply -f dashboard-service.yaml
```

Check:
```text
kubectl get pods
kubectl get services
```

## Dataset
The system uses the Bank Marketing Dataset to predict whether customers will subscribe to a term deposit.

## Known Limitations
- The Dashboard requires the API Gateway to be running.
- Prediction results depend on backend service availability.
- Batch processing requires a valid CSV format.