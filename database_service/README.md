# Database Service

This FastAPI microservice stores customers, campaign history, model predictions,
batch uploads, and historical bank-marketing data in PostgreSQL.

## Prerequisites

Install the following before starting:

- Python 3.11 or newer
- Docker Desktop
- Git (optional)

> **Required startup order:** Start Docker Desktop and PostgreSQL **before**
> starting the FastAPI database service. The API cannot start or serve requests
> when PostgreSQL is unavailable.

## Run locally

All commands below use PowerShell and start from the project root.

### 1. Open the correct directory

The directory name contains an underscore, not a hyphen.

```powershell
cd D:\Bank-Term-Deposit-Predictor\database_service
```

### 2. Start Docker Desktop

Open Docker Desktop and wait until it displays **Engine running**. Confirm from
PowerShell:

```powershell
docker info
```

Do not continue until this command returns Docker server information without an
error.

### 3. Create or start PostgreSQL

Check whether the project container already exists:

```powershell
docker ps -a --filter "name=bank-postgres"
```

If `bank-postgres` is listed, start it:

```powershell
docker start bank-postgres
```

If it is not listed, create it for the first time:

```powershell
docker run --name bank-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=bank_marketing `
  -p 5432:5432 `
  -d postgres:16
```

Confirm that the container is running and PostgreSQL is ready:

```powershell
docker ps --filter "name=bank-postgres"
docker exec bank-postgres pg_isready -U postgres -d bank_marketing
```

The readiness command should report `accepting connections`. Keep this
container running while using the database service.

### 4. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, allow it for the current terminal and
try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 5. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 6. Configure the PostgreSQL connection

The API uses this connection by default:

```text
postgresql+psycopg2://postgres:postgres@localhost:5432/bank_marketing
```

To use another database, set `DATABASE_URL` before starting the API:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE"
```

### 7. Start the database API

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The database tables are created automatically when the application starts.

For future sessions, the normal startup sequence is:

```powershell
docker start bank-postgres
docker exec bank-postgres pg_isready -U postgres -d bank_marketing
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Verify the service

Open these URLs in a browser:

- API root: <http://127.0.0.1:8000/>
- Health check: <http://127.0.0.1:8000/health>
- Swagger API documentation: <http://127.0.0.1:8000/docs>
- ReDoc documentation: <http://127.0.0.1:8000/redoc>

The health endpoint should return:

```json
{
  "status": "healthy"
}
```

## Available endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check service health |
| `POST` | `/customers` | Create a customer |
| `GET` | `/customers` | List customers |
| `GET` | `/customers/pending` | List customers awaiting predictions |
| `GET` | `/customers/{customer_id}` | Retrieve one customer |
| `PUT` | `/customers/{customer_id}` | Update one customer |
| `DELETE` | `/customers/{customer_id}` | Delete a customer and related campaign and prediction records |
| `POST` | `/campaign-history` | Add campaign history |
| `GET` | `/campaign-history/{customer_id}` | Get a customer's campaign history |
| `POST` | `/predictions` | Save a prediction |
| `GET` | `/predictions` | List all predictions |
| `GET` | `/predictions/customer/{customer_id}` | Get a customer's predictions |
| `POST` | `/batch-uploads` | Register a batch upload |
| `GET` | `/batch-uploads` | List batch uploads |
| `GET` | `/batch-uploads/{batch_id}` | Retrieve one batch |
| `GET` | `/batch-uploads/{batch_id}/customers` | List customers in a batch |
| `GET` | `/batch-uploads/{batch_id}/results` | Get results for a batch |
| `POST` | `/historical-data` | Store a historical record |
| `GET` | `/historical-data` | List historical records |

Use the Swagger page at `/docs` to inspect request schemas and test endpoints.

### API Gateway payloads

Create the customer first:

```json
{
  "phone_number": "+6591234567",
  "age": 35,
  "job": "management",
  "marital": "single",
  "education": "tertiary",
  "default": "no",
  "balance": 1500.0,
  "housing": "yes",
  "loan": "no",
  "batch_id": null
}
```

`PUT /customers/{customer_id}` accepts any subset of the customer fields above.

After creating the customer, use its returned `customer_id` to add campaign
information:

```json
{
  "customer_id": 1,
  "contact": "cellular",
  "day": 15,
  "month": "may",
  "campaign": 1,
  "pdays": -1,
  "previous": 0,
  "poutcome": "unknown"
}
```

Once campaign information exists, save the prediction:

```json
{
  "customer_id": 1,
  "prediction": "yes",
  "probability": 0.81,
  "model_version": "1.0"
}
```

`GET /predictions` returns all live predictions. Use
`GET /predictions/customer/{customer_id}` to filter them by customer.
`GET /historical-data` returns imported historical dataset rows and is separate
from live customer predictions.

## Stop the services

Stop Uvicorn with `Ctrl+C`. Stop PostgreSQL with:

```powershell
docker stop bank-postgres
```

The container and its data remain available and can be restarted with
`docker start bank-postgres`.

## Run the API in Docker

Start PostgreSQL as described above. Then build the API image:

```powershell
docker build -t bank-database-service .
```

Because a container cannot use its own `localhost` to reach PostgreSQL on the
Windows host, run it with `host.docker.internal` in the connection URL:

```powershell
docker run --name bank-database-api `
  -e DATABASE_URL="postgresql+psycopg2://postgres:postgres@host.docker.internal:5432/bank_marketing" `
  -p 8000:8000 `
  bank-database-service
```

## Kubernetes deployment

The manifests are under `k8s/`. Before deploying, replace the placeholder image
in `k8s/deployment.yaml`:

```yaml
image: your-dockerhub-username/database-service:latest
```

Then apply the manifests from this directory:

```powershell
kubectl apply -f k8s\persistent-volume-claim.yaml
kubectl apply -f k8s\deployment.yaml
kubectl apply -f k8s\service.yaml
```

Check the deployment:

```powershell
kubectl get pods
kubectl get services
```

## Troubleshooting

### `Cannot find path ...\database-service`

Use `database_service` with an underscore:

```powershell
cd D:\Bank-Term-Deposit-Predictor\database_service
```

### `connection refused` on port 5432

PostgreSQL is not running. Start it and check its status:

```powershell
docker start bank-postgres
docker ps
```

### `failed to connect to the docker API`

Open Docker Desktop, wait until the engine finishes starting, and rerun:

```powershell
docker info
```

### Container name already exists

Start the existing container:

```powershell
docker start bank-postgres
```

Inspect all containers if needed:

```powershell
docker ps -a
```

### Port 5432 is already in use

Another PostgreSQL instance or container is already using the port. Find the
container with:

```powershell
docker ps
```

Either use that PostgreSQL instance or map a different host port and update
`DATABASE_URL` to match.

