# Monitoring Service (Student D)

This independent FastAPI service monitors the AI interface, API gateway and
database service. It stores health-check and application logs in SQLite and
runs on port `7002`, matching Student B's existing
`MONITORING_SERVICE_URL` configuration.

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Monitoring service health |
| GET | `/status` | Live status of all three monitored services |
| GET | `/logs` | Recent logs; supports `limit`, `service`, `level` filters |
| POST | `/logs` | Accept an application log from another service |
| GET | `/metrics` | Log totals, errors, warnings and response times |

## Run locally

```powershell
cd D:\Bank-Term-Deposit-Predictor\monitoring_service
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 7002
```

Open <http://localhost:7002/docs>.

## Run with Docker

The Docker configuration uses `host.docker.internal` to check services that
are running on the Windows host.

```powershell
cd D:\Bank-Term-Deposit-Predictor\monitoring_service
docker compose up --build -d
```

Student B's existing default works without a code change:

```text
MONITORING_SERVICE_URL=http://localhost:7002
```
