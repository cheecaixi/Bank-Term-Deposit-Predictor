# Database Service

This FastAPI microservice stores customers, campaign history, model predictions,
batch uploads, and historical bank-marketing data in PostgreSQL.

## Prerequisites

Install the following before starting:

- Python 3.11 or newer
- Docker Desktop
- Git (optional)

Docker Desktop must be open and its Docker engine must be running.

## Run locally

All commands below use PowerShell and start from the project root.

### 1. Open the correct directory

The directory name contains an underscore, not a hyphen.

```powershell
cd D:\Bank-Term-Deposit-Predictor\database_service
```

### 2. Create and activate a virtual environment

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

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Start PostgreSQL

First confirm that Docker Desktop is running:

```powershell
docker info
```

Create and start the PostgreSQL container:

```powershell
docker run --name bank-postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=bank_marketing `
  -p 5432:5432 `
  -d postgres:16
```

For later sessions, start the existing container instead:

```powershell
docker start bank-postgres
```

Confirm that it is running:

```powershell
docker ps
```

The service uses this connection by default:

```text
postgresql+psycopg2://postgres:postgres@localhost:5432/bank_marketing
```

To use another database, set `DATABASE_URL` before starting the API:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://USER:PASSWORD@HOST:5432/DATABASE"
```

### 5. Start the API

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The database tables are created automatically when the application starts.

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
| `POST` | `/campaign-history` | Add campaign history |
| `GET` | `/campaign-history/{customer_id}` | Get a customer's campaign history |
| `POST` | `/predictions` | Save a prediction |
| `GET` | `/predictions/customer/{customer_id}` | Get a customer's predictions |
| `POST` | `/batch-uploads` | Register a batch upload |
| `GET` | `/batch-uploads` | List batch uploads |
| `GET` | `/batch-uploads/{batch_id}` | Retrieve one batch |
| `GET` | `/batch-uploads/{batch_id}/customers` | List customers in a batch |
| `GET` | `/batch-uploads/{batch_id}/results` | Get results for a batch |
| `POST` | `/historical-data` | Store a historical record |
| `GET` | `/historical-data` | List historical records |

Use the Swagger page at `/docs` to inspect request schemas and test endpoints.

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

