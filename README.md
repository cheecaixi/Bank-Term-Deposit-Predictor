# AIAD

# 1. Project Objectives
Machine Learning Goal: Train and validate a classification model to predict customer term deposit subscriptions using demographic and historical campaign data.

Engineering Goal: Architect and deploy the end-to-end Machine Learning pipeline as a modular, 5-microservice system (AI Inference, API Gateway, Dashboard, Database, and Monitoring) on Kubernetes (Minikube).

Operational Goal: Ensure high system availability, fault tolerance, and horizontal pod autoscaling (HPA) for the inference engine to support high-volume, concurrent requests during peak marketing campaigns.

# 2. Target Users
Primary Users (Telesales & Bank Agents): Utilize the real-time UI during customer calls to receive instant subscription probabilities, allowing them to dynamically adapt sales strategies.

Secondary Users (Marketing Analysts & Managers): Evaluate aggregate performance metrics, campaign trends, and customer conversion rates via the analytics interface to optimize resource allocation.

Technical Users (DevOps & System Administrators): Monitor system performance, API request latency, container health, and model drift using the centralized logging service.

# 3. Expected Outcomes
Functional Deliverable: A fully containerized microservices application hosted on Kubernetes, leveraging an API gateway for dynamic service discovery and request routing.

Business Value: Enhanced campaign conversion rates and lower operational overhead achieved through data-driven customer prioritization.

Technical Quality Outcomes: A resilient, scalable architecture capable of handling peak workloads via autoscaling, supported by end-to-end observability and persistent data logging.

Here’s a clear **architecture sketch in words** for your chosen dataset (Bank Marketing & Customer Behavior) and how to split the microservices among 4 members, with one extra service added for fairness:

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

