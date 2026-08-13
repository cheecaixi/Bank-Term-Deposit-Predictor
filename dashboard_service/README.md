# Dashboard Service — Bank Marketing AI Application

Owner: Student C
Part of the EGT307 microservices project (Bank Marketing & Customer Behaviour).

## What this service does

A Streamlit web app with three tabs:

1. **Single Prediction** — an agent fills in one customer's details and gets an
   instant subscription-probability score, for use during a live call.
2. **Batch Prediction** — an agent (or manager) uploads a CSV of many customers
   and gets predictions for all of them at once, downloadable as a CSV.
3. **Analyst View** — KPI tiles and charts summarising campaign performance,
   for marketing analysts/managers.

## How it fits into the system

```
[Dashboard] --HTTP--> [API Gateway] --> [Inference Service]
                                    --> [Database Service]
                                    --> [Monitoring Service]
```

The dashboard never calls Inference/Database/Monitoring directly — everything
goes through the API Gateway.

## Running locally (without Docker)

```bash
cd dashboard-service
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

By default the app runs in **MOCK mode** (`USE_MOCK = True` in `app.py`), so it
works standalone even before the Gateway/Inference services exist. To connect
to the real backend once it's ready, set `USE_MOCK = False` in `app.py` and set
the `GATEWAY_URL` environment variable.

## Running with Docker

```bash
docker build -t dashboard-service .
docker run -p 8501:8501 -e GATEWAY_URL=http://localhost:8000 dashboard-service
```

## Environment variables

| Variable      | Purpose                             | Default                 |
|---------------|--------------------------------------|--------------------------|
| `GATEWAY_URL` | Base URL of the API Gateway service | `http://localhost:8000` |

## Expected API contract (agreed with Inference/Gateway team)

**POST `/predict`** — single customer
```json
Request:  {"age": 35, "job": "management", "marital": "married", ...}
Response: {"probability": 0.73, "prediction": "yes"}
```

**POST `/predict/batch`** — many customers
```json
Request:  {"records": [{...}, {...}, ...]}
Response: {"results": [{"probability": 0.73, "prediction": "yes"}, ...]}
```

## Known issues / limitations

- Currently uses mock prediction logic until the real Inference service is ready.
- Analyst View uses sample/placeholder data until the Database/Monitoring
  services are connected.
- No authentication yet — to be added once API Gateway auth is finalised.
