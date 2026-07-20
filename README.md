# AIAD
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

