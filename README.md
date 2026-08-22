# AIAD

## Start the database service

The easiest setup uses Docker Compose. It downloads PostgreSQL, builds the
FastAPI database service, waits for PostgreSQL to become ready, and starts both
containers:
The **Bank Term Deposit Predictor** is a machine learning and microservices-based application designed to predict whether a bank customer is likely to subscribe to a term deposit.

The project combines a trained machine learning model with a modular microservices architecture. Customer information is submitted through the dashboard, processed through the API Gateway and AI Inference Service, stored through the Database Service, and monitored through the Monitoring Service.

The complete system is containerized using Docker and deployed on Kubernetes (Minikube) to support scalability, fault tolerance, and service availability.

---

## 2. Project Objectives

**Machine Learning Goal:** Train and validate a classification model to predict customer term deposit subscriptions using demographic and historical campaign data.

**Engineering Goal:** Architect and deploy the end-to-end Machine Learning pipeline as a modular 5-microservice system consisting of AI Inference, API Gateway, Dashboard, Database, and Monitoring services.

**Operational Goal:** Ensure high system availability, fault tolerance, monitoring, persistent storage, and horizontal pod autoscaling for the API Gateway and Dashboard services.

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
                         └───────┬────────┬────────┘
                                 │        │
                    ┌────────────┘        └──────────────┐
                    ▼                                    ▼
          ┌─────────────────────┐              ┌─────────────────────┐
          │   AI Inference      │              │   Database Service  │
          │      Member A       │              │      Member D       │
          │  ML Prediction      │              │ Customer & Results  │
          └─────────────────────┘              └──────────┬──────────┘
                                                          │
                                                          ▼
                                             ┌─────────────────────┐
                                             │     PostgreSQL      │
                                             │   Persistent Data   │
                                             └─────────────────────┘

                         ┌─────────────────────────┐
                         │   Monitoring Service    │
                         │        Member D         │
                         │ Logs, Health & Metrics  │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │   Monitoring Storage    │
                         │     SQLite / PVC        │
                         └─────────────────────────┘

      Monitoring checks the health and performance of the other services.
      The API Gateway sends request logs to the Monitoring Service.

### Architecture Flow

```markdown
```text
Dashboard
    │
    ▼
API Gateway
    ├──────────────► AI Inference Service
    │                    └── Prediction
    │
    ├──────────────► Database Service
    │                    └── PostgreSQL
    │
    └──────────────► Monitoring Service
                         └── Logs, Health & Metrics
                              └── SQLite / PVC

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

The API Gateway exposes the following routes:

```text
/api/predict
/api/results
/api/customers/{customer_id}
/api/batch-uploads
/api/logs
/api/monitoring/status
/api/monitoring/metrics

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

Username:

```text
postgres
```

---

# 11. Database Service Setup

The Database Service can also be tested independently during development.

Navigate to the Database Service directory:

```powershell
cd D:\Bank-Term-Deposit-Predictor\database_service
docker compose up --build -d
docker compose ps
```

Then open <http://localhost:8000/docs>. For the full first-time setup,
verification commands, stopping instructions, and troubleshooting, read the
[database service guide](database_service/README.md).

# 1. Project Objectives
Machine Learning Goal: Train and validate a classification model to predict customer term deposit subscriptions using demographic and historical campaign data.

Engineering Goal: Architect and deploy the end-to-end Machine Learning pipeline as a modular, 5-microservice system (AI Inference, API Gateway, Dashboard, Database, and Monitoring) on Kubernetes (Minikube).

Operational Goal: Ensure high system availability, fault tolerance, and horizontal pod autoscaling (HPA) for the inference engine to support high-volume, concurrent requests during peak marketing campaigns.

<<<<<<< Updated upstream
# 2. Target Users
Primary Users (Telesales & Bank Agents): Utilize the real-time UI during customer calls to receive instant subscription probabilities, allowing them to dynamically adapt sales strategies.

Secondary Users (Marketing Analysts & Managers): Evaluate aggregate performance metrics, campaign trends, and customer conversion rates via the analytics interface to optimize resource allocation.

Technical Users (DevOps & System Administrators): Monitor system performance, API request latency, container health, and model drift using the centralized logging service.

# 3. Expected Outcomes
Functional Deliverable: A fully containerized microservices application hosted on Kubernetes, leveraging an API gateway for dynamic service discovery and request routing.

Business Value: Enhanced campaign conversion rates and lower operational overhead achieved through data-driven customer prioritization.

Technical Quality Outcomes: A resilient, scalable architecture capable of handling peak workloads via autoscaling, supported by end-to-end observability and persistent data logging.

Here’s a clear **architecture sketch in words** for your chosen dataset (Bank Marketing & Customer Behavior) and how to split the microservices among 4 members, with one extra service added for fairness:
=======
> **Note:** When running the complete project, return to the project root and use the root-level `docker-compose.yaml`. Use the Database Service Compose file only when testing that service independently.
>>>>>>> Stashed changes

---

### 🏗️ Microservices Layout

**1. AI Inference Service (Member A)**  
- Trains and serves the ML model (predicts if a customer subscribes).  
- REST API for predictions.  
- Docker + Kubernetes scaling.  

**2. API Gateway Service (Member B)**  
- Routes requests between inference, database, dashboard, and monitoring.  
- Handles authentication and load balancing.  
- Docker + Kubernetes deployment.  

**3. Dashboard Service (Member C)**  
- Visualizes predictions, customer behavior insights, campaign success rates.  
- User‑friendly interface (Streamlit/Flask/React).  
- Docker + Kubernetes deployment.  

**4. Database Service (Member D)**  
- Stores customer records, predictions, logs.  
- Schema design + persistence.  
- Docker + Kubernetes deployment.  

**5. Extra Service (also Member D)** → **Monitoring/Logging Service**  
- Collects logs from inference + API gateway.  
- Tracks model accuracy, campaign outcomes, errors.  
- Provides analytics endpoints for dashboard.  
- Docker + Kubernetes deployment.  

---

<<<<<<< Updated upstream
### 🔑 Why this works
- Everyone owns a **full microservice** with Dockerfile + Kubernetes manifest.  
- The database member has **two connected services (DB + Monitoring)**, making their workload equal to ML and dashboard members.  
- Each service has **coding, deployment, and engineering depth**.  
- Clear GitHub commit history shows contributions per member.  

---

### 📊 Visual Flow (text sketch)
```
[Dashboard] <--> [API Gateway] <--> [AI Inference]
                                <--> [Database]
                                <--> [Monitoring/Logging]
```

### Initial system architecture diagram
```
                         ┌──────────────────────┐
                         │      Dashboard       │
                         │ Predictions & Charts │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     API Gateway      │
                         │ Validation & Routing │
                         └───────┬──────┬───────┘
                                 │      │
                    ┌────────────┘      └─────────────┐
                    ▼                                 ▼
        ┌──────────────────────┐          ┌──────────────────────┐
        │ AI Inference Service │          │   Database Service   │
        │ Predict Yes / No     │          │ Customers & Results  │
        └──────────┬───────────┘          └──────────┬───────────┘
                   │                                  │
                   └──────────────┬───────────────────┘
                                  ▼
                       ┌──────────────────────┐
                       │ Monitoring / Logging │
                       │ Requests, Predictions│
                       │ Errors & Performance │
                       └──────────────────────┘
```

- Dashboard shows predictions + insights.  
- API Gateway is the traffic controller.  
- AI Inference is the brain.  
- Database is the memory.  
- Monitoring/Logging is the performance tracker.  

---
Since you’ve already chosen the **Bank Marketing & Customer Behavior dataset**, here’s the logical order to tackle the project so your team doesn’t get stuck later:

---
=======
# 13. Kubernetes Deployment

The final system is designed to run on Kubernetes using Minikube.

The Kubernetes deployment includes:

* AI Inference Deployment
* AI Inference Service
* API Gateway HPA
* Dashboard HPA
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
```

Apply the Kubernetes configurations:

```powershell
kubectl apply -f AI-Interface/k8s/
kubectl apply -f api_gateway/k8s/
kubectl apply -f database_service/k8s/
kubectl apply -f dashboard_service/k8s/
kubectl apply -f monitoring_service/k8s/
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

---

# 14. Horizontal Pod Autoscaling

Horizontal Pod Autoscaling (HPA) is configured for the API Gateway and Dashboard services.

Each HPA maintains between 2 and 5 replicas and scales the number of pods according to average CPU utilisation. This helps the system handle increased API requests and dashboard traffic during busy periods.

The AI Inference Service currently runs with multiple Kubernetes replicas, but it does not have a separate HPA configuration.
>>>>>>> Stashed changes

### 🪜 Recommended Order of Work

**Step 1 – Define the Problem & Split Roles**  
- Agree on the prediction task (e.g., *predict if a customer subscribes to a product*).  
- Confirm microservice ownership:  
  - Member A → AI Inference (ML model)  
  - Member B → API Gateway  
  - Member C → Dashboard  
  - Member D → Database + Extra Service (e.g., Monitoring/Logging)

---

**Step 2 – Model Development (Member A)**  
- Train a baseline ML model (Logistic Regression or Random Forest).  
- Test locally in Jupyter/Colab to confirm it works.  
- Save the trained model file (`.pkl` or `.joblib`).  
👉 Do this first because the **inference service is the “brain”** of the system — other services depend on its outputs.

---

**Step 3 – Database & Schema Setup (Member D)**  
- Design schema for storing customer records + predictions.  
- Build DB service and Monitoring/Logging service.  
- Test queries locally.  
👉 This ensures you have a place to store and retrieve results before connecting the API gateway.

---

**Step 4 – API Gateway (Member B)**  
- Build routes:  
  - `/predict` → calls inference service.  
  - `/results` → fetches from database.  
  - `/logs` → fetches monitoring data.  
- Test routing between services.  
👉 This is the “traffic controller” — it connects ML, DB, and dashboard.

---

**Step 5 – Dashboard (Member C)**  
- Build frontend to visualize predictions, campaign success rates, logs.  
- Connect to API gateway endpoints.  
👉 This is the “face” of the project — but it depends on the API being ready.

---

**Step 6 – Dockerize Each Service (All Members)**  
- Write Dockerfiles for each microservice.  
- Push images to Docker Hub.  
- Verify each service runs correctly in isolation.  

---

**Step 7 – Kubernetes Deployment (All Members)**  
- Write YAML manifests for each service.  
- Deploy on Kubernetes cluster.  
- Test scaling (e.g., inference service under load).  

---

### 🔑 Key Point
Start with **model development (Step 2)** because everything else (API, DB, dashboard) depends on having predictions to work with. Then move to **database setup**, followed by **API gateway**, and finally **dashboard**. Docker + Kubernetes come last once all services are working locally.

---

