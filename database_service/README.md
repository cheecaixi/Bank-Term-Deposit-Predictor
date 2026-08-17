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

## Recommended: start everything with Docker Compose

This is the simplest method. Docker Compose downloads the PostgreSQL image,
builds the FastAPI image, creates the database, waits until PostgreSQL is ready,
and then starts the API. You do **not** need to install Python or PostgreSQL on
Windows for this method.

### 1. Install and open Docker Desktop

Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/),
open it, and wait until it reports that the Docker engine is running.

Open PowerShell and verify Docker:

```powershell
docker --version
docker compose version
docker info
```

Do not continue if `docker info` reports that it cannot connect to the Docker
engine.

### 2. Open the database-service directory

```powershell
cd D:\Bank-Term-Deposit-Predictor\database_service
```

If the project is stored somewhere else, open that project's
`database_service` directory instead.

### 3. Download, build, and start PostgreSQL and the API

```powershell
docker compose up --build -d
```

The first run takes longer because Docker downloads the `postgres:16-alpine`
and `python:3.11-slim` images and installs every Python package listed in
`requirements.txt`.

### 4. Confirm both containers are running

```powershell
docker compose ps
docker compose logs postgres
docker compose logs database-api
```

`postgres` should show `healthy`, and `database-api` should show `running`.
The API creates its tables automatically on startup.

### 5. Open and test the service

Open the interactive API documentation:

<http://localhost:8000/docs>

Also verify the health endpoint in PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

It should return a status of `healthy`.

### Normal use after the first setup

Start the service again:

```powershell
cd D:\Bank-Term-Deposit-Predictor\database_service
docker compose up -d
```

Stop both containers without deleting the database data:

```powershell
docker compose down
```

View live API logs:

```powershell
docker compose logs -f database-api
```

Press `Ctrl+C` to stop following the logs; the containers keep running.

> `requirements.txt` installs Python packages only. The PostgreSQL Python
> driver is `psycopg2-binary`. The PostgreSQL server is supplied by the
> `postgres:16-alpine` image declared in `compose.yaml`, because a database
> server cannot be installed from a Python requirements file.

## Alternative: run the API locally and only PostgreSQL in Docker

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

## Run the API container manually

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

If the message mentions
`dockerDesktopLinuxEngine` or says that the named pipe cannot be found, the
Docker command-line tool is installed but the Docker Desktop engine is not
running.

1. Open the Windows **Start** menu.
2. Search for and open **Docker Desktop**.
3. If Docker Desktop asks you to accept terms, update WSL, or restart Windows,
   complete that prompt first.
4. Wait until Docker Desktop displays **Engine running**. Do not close Docker
   Desktop.
5. Confirm the engine is ready in PowerShell:

```powershell
docker info
```

Only after `docker info` displays both `Client` and `Server` information, run:

```powershell
cd D:\Bank-Term-Deposit-Predictor\database_service
docker compose up --build -d
docker compose ps
```

If Docker Desktop is already open, select **Troubleshoot** and then
**Restart Docker Desktop**. If it still cannot start, restart Windows and open
Docker Desktop before opening the project terminal.

### Container name already exists

The current Compose setup generates its own container names, so it can coexist
with stopped containers created by the older manual setup. Pull the latest
`compose.yaml`, or remove both `container_name:` lines if they are present in
your local copy, and run:

```powershell
docker compose up --build -d
```

You do not need to delete the old container. Inspect all containers if needed:

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

