# AIAD – Bank Term Deposit Predictor

## 1. Project Overview

The **Bank Term Deposit Predictor** is a machine learning and microservices-based application designed to predict whether a bank customer is likely to subscribe to a term deposit.

The project combines a trained machine learning model with a modular microservices architecture. Customer information is submitted through the dashboard, processed through the API Gateway and AI Inference Service, stored through the Database Service, and monitored through the Monitoring Service.

The complete system is containerized using Docker and deployed on Kubernetes (Minikube) to support scalability, fault tolerance, and service availability.

---

## 2. Project Objectives

**Machine Learning Goal:** Train and validate a classification model to predict customer term deposit subscriptions using demographic and historical campaign data.

**Engineering Goal:** Architect and deploy the end-to-end Machine Learning pipeline as a modular 5-microservice system consisting of AI Inference, API Gateway, Dashboard, Database, and Monitoring services.

**Operational Goal:** Ensure high system availability, fault tolerance, and horizontal pod autoscaling (HPA) for the AI Inference Service to support high-volume and concurrent requests during peak marketing campaigns.

---

## 3. Target Users

### Primary Users – Telesales & Bank Agents

Utilize the real-time dashboard during customer calls to receive instant subscription probabilities, allowing them to dynamically adapt sales strategies.

### Secondary Users – Marketing Analysts & Managers

Evaluate aggregate performance metrics, campaign trends, customer conversion rates, and customer prioritisation results through the analytics interface to optimize resource allocation.

### Technical Users – DevOps & System Administrators

Monitor system performance, API request latency, service health, errors, and model-related metrics through the centralized monitoring service.

---

## 4. Expected Outcomes

**Functional Deliverable:** A fully containerized microservices application hosted on Kubernetes, leveraging an API Gateway for service communication, request routing, and service integration.

**Business Value:** Enhanced campaign conversion rates and lower operational overhead through data-driven customer prediction and prioritisation.

**Technical Quality Outcomes:** A resilient and scalable architecture capable of handling peak workloads through autoscaling, supported by system monitoring, persistent data storage, and end-to-end logging.

---

# 5. Project Team & Contributions

The project is divided among four members, with each member responsible for specific microservices and technical components.

| Member                | Component                          | Main Responsibilities                                                                                                                                                                                                                    |
| --------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Member A – Amanda** | **AI Inference Service**           | Develop and train the machine learning model, implement the prediction API, configure prediction thresholds, package the trained model, create Docker/Kubernetes deployment, and configure HPA for scalable inference.                   |
| **Member B – Mya**    | **API Gateway Service**            | Develop the central API Gateway, route requests between the Dashboard, AI Inference, Database, and Monitoring services, implement API endpoints, request validation, and service integration.                                            |
| **Member C – Cai Xi** | **Dashboard Service**              | Develop the Streamlit dashboard, display prediction and analytics results, implement customer prioritisation and batch result exploration, integrate the dashboard with the API Gateway, and create Docker/Kubernetes deployment.        |
| **Member D – Su**     | **Database & Monitoring Services** | Develop the Database Service and PostgreSQL integration, design database schemas, manage customer, prediction, and campaign data, develop the Monitoring Service, collect system metrics/logs, and create Docker/Kubernetes deployments. |

### Component Ownership

* **Member A – Amanda:** AI Inference Service
* **Member B – Mya:** API Gateway Service
* **Member C – Cai Xi:** Dashboard Service
* **Member D – Su:** Database Service and Monitoring Service
* **PostgreSQL:** Persistent database infrastructure supporting the Database Service

---

# 6. Microservices Architecture

The system consists of **5 application microservices** supported by a PostgreSQL database.

### 6.1 AI Inference Service – Member A

The AI Inference Service is responsible for serving the trained machine learning model.

Responsibilities include:

* Loading the trained ML model.
* Receiving customer information through a REST API.
* Generating subscription predictions.
* Returning subscription probability.
* Applying the configured prediction threshold.
* Measuring prediction processing time.
* Supporting horizontal scaling through Kubernetes HPA.

### 6.2 API Gateway Service – Member B

The API Gateway acts as the central traffic controller for the system.

Responsibilities include:

* Receiving requests from the Dashboard.
* Routing prediction requests to the AI Inference Service.
* Sending customer information to the Database Service.
* Retrieving prediction and analytics results.
* Communicating with the Monitoring Service.
* Validating API requests.
* Providing a single entry point for the frontend.

### 6.3 Dashboard Service – Member C

The Dashboard provides the user-facing interface of the application.

Responsibilities include:

* Providing an interactive Streamlit interface.
* Submitting customer information for prediction.
* Displaying subscription predictions and probabilities.
* Displaying customer prioritisation results.
* Allowing users to explore batch prediction results.
* Displaying analytics and campaign insights.
* Communicating with the backend through the API Gateway.

### 6.4 Database Service – Member D

The Database Service manages persistent application data.

Responsibilities include:

* Storing customer records.
* Storing prediction results.
* Storing campaign history.
* Supporting batch uploads and batch results.
* Providing REST API endpoints for data access.
* Connecting to PostgreSQL for persistent storage.

### 6.5 Monitoring Service – Member D

The Monitoring Service provides system observability.

Responsibilities include:

* Monitoring service health.
* Tracking API requests.
* Monitoring response times.
* Tracking errors.
* Collecting prediction-related metrics.
* Storing monitoring information.
* Providing monitoring endpoints for system analysis.

---

# 7. System Architecture

The overall system follows the communication flow below:

```text
                         ┌─────────────────────────┐
                         │       Dashboard         │
                         │       Member C          │
                         │       Streamlit         │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │      API Gateway        │
                         │        Member B         │
                         │   Routing & Validation  │
                         └───────┬───────┬─────────┘
                                 │       │
                    ┌────────────┘       └──────────────┐
                    ▼                                   ▼
          ┌─────────────────────┐             ┌─────────────────────┐
          │   AI Inference      │             │   Database Service  │
          │      Member A       │             │      Member D       │
          │  ML Prediction      │             │ Customer & Results  │
          └──────────┬──────────┘             └──────────┬──────────┘
                     │                                   │
                     └────────────────┬──────────────────┘
                                      ▼
                           ┌─────────────────────┐
                           │     Monitoring      │
                           │      Member D       │
                           │ Logs & Performance  │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │     PostgreSQL      │
                           │   Persistent Data   │
                           └─────────────────────┘
```

### Architecture Flow

```text
Dashboard
    │
    ▼
API Gateway
    │
    ├──────────────► AI Inference Service
    │                    │
    │                    └── Prediction
    │
    ├──────────────► Database Service
    │                    │
    │                    └── PostgreSQL
    │
    └──────────────► Monitoring Service
                         │
                         └── Logs & Metrics
```

The Dashboard does not directly communicate with the AI Inference Service or PostgreSQL. Requests are routed through the API Gateway, providing a centralized entry point and clear separation between the frontend and backend services.

---

# 8. Recommended Development Order

### Step 1 – Define the Problem & Split Roles

Agree on the prediction task:

> Predict whether a customer is likely to subscribe to a bank term deposit.

Confirm microservice ownership:

* Member A → AI Inference
* Member B → API Gateway
* Member C → Dashboard
* Member D → Database + Monitoring

### Step 2 – Model Development

**Member A** develops and validates the machine learning model.

Tasks include:

* Data preprocessing
* Model training
* Model evaluation
* Hyperparameter tuning
* Threshold selection
* Model saving

The trained model is then made available to the AI Inference Service.

### Step 3 – Database & Monitoring

**Member D** develops:

* Database schema
* PostgreSQL integration
* Database API
* Customer storage
* Prediction storage
* Campaign history
* Monitoring and logging

### Step 4 – API Gateway

**Member B** develops the central API Gateway.

Example routes include:

```text
/predict
/results
/customers
/campaign-history
/batch-uploads
/monitoring
```

The API Gateway connects the Dashboard with the backend services.

### Step 5 – Dashboard

**Member C** develops the Streamlit Dashboard.

The Dashboard connects to the API Gateway and provides:

* Prediction interface
* Customer prioritisation
* Batch upload/result exploration
* Analytics
* Campaign insights

### Step 6 – Dockerisation

Each service is containerized using its own Dockerfile.

The complete system can then be started using Docker Compose.

### Step 7 – Kubernetes Deployment

After the services have been tested locally:

* Create Kubernetes Deployments.
* Create Kubernetes Services.
* Configure service-to-service communication.
* Deploy to Minikube.
* Configure HPA.
* Test scaling and service availability.

---

# 9. Run the Entire System Using Docker Compose

The project includes a Docker Compose configuration for running the complete system locally.

The Compose environment contains **6 containers**:

1. PostgreSQL Database
2. AI Inference Service
3. Database Service
4. Monitoring Service
5. API Gateway Service
6. Dashboard Service

Start the complete system with:

```powershell
docker compose up --build -d
```

### Verification & Status Check

Check whether all containers are running:

```powershell
docker compose ps
```

Stream the logs to check for startup errors:

```powershell
docker compose logs -f
```

To stop viewing the logs, press:

```text
Ctrl + C
```

The containers will continue running in the background.

---

# 10. Access Service Endpoints

After starting Docker Compose, the following services can be accessed from the host machine:

| Service                              | Member | URL                                                      |
| ------------------------------------ | ------ | -------------------------------------------------------- |
| **Dashboard**                        | Cai Xi | [http://localhost:8501](http://localhost:8501)           |
| **API Gateway Documentation**        | Mya    | [http://localhost:8080/docs](http://localhost:8080/docs) |
| **Database Service Documentation**   | Su     | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **AI Inference API Documentation**   | Amanda | [http://localhost:7000/docs](http://localhost:7000/docs) |
| **Monitoring Service Documentation** | Su     | [http://localhost:7002/docs](http://localhost:7002/docs) |

### PostgreSQL

PostgreSQL is exposed on:

```text
localhost:5432
```

Database:

```text
bank_marketing
```

---

# 11. Database Service Setup

The Database Service can also be tested independently during development.

Navigate to the Database Service directory:

```powershell
cd D:\Bank-Term-Deposit-Predictor\database_service
```

Start the database service:

```powershell
docker compose up --build -d
```

Check the running containers:

```powershell
docker compose ps
```

Then open:

```text
http://localhost:8000/docs
```

For detailed first-time setup, verification commands, stopping instructions, and troubleshooting, refer to the Database Service README:

```text
database_service/README.md
```

> **Note:** When running the complete project, use the root-level `docker-compose.yml` instead of the individual Database Service Compose configuration.

---

# 12. Environment & Service Communication

Docker Compose provides an internal network that allows services to communicate using their service names.

For example:

```text
Dashboard
    ↓
http://api-gateway:8080

API Gateway
    ↓
http://ai-inference:7000
http://database-service:8000
http://monitoring-service:7002

Database Service
    ↓
postgres-db:5432
```

The services use the following environment variables:

### Dashboard

```text
GATEWAY_URL=http://api-gateway:8080
```

### API Gateway

```text
INFERENCE_SERVICE_URL=http://ai-inference:7000
DATABASE_SERVICE_URL=http://database-service:8000
MONITORING_SERVICE_URL=http://monitoring-service:7002
```

### Monitoring Service

```text
AI_SERVICE_URL=http://ai-inference:7000
GATEWAY_SERVICE_URL=http://api-gateway:8080
DATABASE_SERVICE_URL=http://database-service:8000
```

This allows services to communicate within the Docker Compose network using service names rather than `localhost`.

---

# 13. Kubernetes Deployment

The final system is designed to run on Kubernetes using Minikube.

The Kubernetes deployment includes:

* AI Inference Deployment
* AI Inference Service
* AI Inference HPA
* API Gateway Deployment
* API Gateway Service
* Dashboard Deployment
* Dashboard Service
* Database Deployment
* Database Service
* Monitoring Deployment
* Monitoring Service

Start Minikube:

```powershell
minikube start
minikube status
```

Apply the Kubernetes configurations:

```powershell
kubectl apply -f database_service/k8s/
kubectl apply -f AI-Interface/k8s/
kubectl apply -f monitoring_service/k8s/
kubectl apply -f api_gateway/k8s/
kubectl apply -f dashboard_service/k8s/
```

Open:

```powershell
minikube service dashboard-service
```

Check deployments:

```powershell
kubectl get deployments
```

Check pods:

```powershell
kubectl get pods
```

Check services:

```powershell
kubectl get services
```

Check HPA:

```powershell
kubectl get hpa
```

Check all:

```powershell
kubectl get all
```

---

# 14. Horizontal Pod Autoscaling

The AI Inference Service is designed to support horizontal scaling under increased workloads.

The HPA monitors resource utilisation and can increase or decrease the number of AI Inference pods according to demand.

```text
                    Incoming Requests
                           │
                           ▼
                  AI Inference Service
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
            AI Pod 1             AI Pod 2
                 │                   │
                 └─────────┬─────────┘
                           │
                       HPA Controller
                           │
                    Scale Up / Down
```

This allows the system to handle increased prediction requests during high-volume marketing campaigns.

---

# 15. Stopping & Cleaning Up

### Stop Containers

To stop the containers while preserving database volume data:

```powershell
docker compose down
```

### Remove Containers and Volumes

To completely reset the database and remove persistent volume data:

```powershell
docker compose down -v
```

> **Warning:** `docker compose down -v` removes the Docker volumes used by the application. Any data stored in those volumes will be deleted.

---

# 16. Key System Features

The completed system provides:

* Machine learning-based term deposit prediction
* Customer subscription probability
* Configurable prediction threshold
* Real-time prediction through the Dashboard
* Customer prioritisation
* Batch upload and batch result exploration
* Persistent customer and prediction storage
* Campaign history
* API Gateway-based service communication
* Centralised monitoring
* Docker containerisation
* Docker Compose orchestration
* Kubernetes deployment
* Horizontal Pod Autoscaling
* Modular microservices architecture

---

# 17. System Summary

The Bank Term Deposit Predictor integrates machine learning, microservices, containerisation, and Kubernetes into a complete end-to-end system.

```text
Customer
   │
   ▼
Dashboard
(Member C)
   │
   ▼
API Gateway
(Member B)
   │
   ├──────────────► AI Inference
   │                (Member A)
   │                     │
   │                     ▼
   │                 Prediction
   │
   ├──────────────► Database Service
   │                (Member D)
   │                     │
   │                     ▼
   │                 PostgreSQL
   │
   └──────────────► Monitoring Service
                    (Member D)
                         │
                         ▼
                    Logs & Metrics
```

The architecture separates responsibilities across independent services while allowing the components to communicate through well-defined APIs. Docker Compose provides a convenient local development environment, while Kubernetes and HPA provide the scalability and resilience required for production-style deployment.
