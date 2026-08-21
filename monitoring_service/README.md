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

## Run with Kubernetes (Minikube)

The Kubernetes deployment reads non-sensitive settings from
`k8s/configmap.yaml` and stores its SQLite database on `monitoring-pvc`. It
does not require a Secret because it currently uses no credentials or tokens.

Build the Compose image, load it into Minikube, and apply the manifests from
the repository root:

```powershell
docker compose -f monitoring_service\compose.yaml build
minikube image load monitoring_service-monitoring-service:latest

kubectl apply -f monitoring_service\k8s\configmap.yaml
kubectl apply -f monitoring_service\k8s\persistent-volume-claim.yaml
kubectl apply -f monitoring_service\k8s\service.yaml
kubectl apply -f monitoring_service\k8s\deployment.yaml

kubectl rollout status deployment/monitoring-service --timeout=120s
kubectl get pods
kubectl get service monitoring-service
kubectl get pvc monitoring-pvc
```

The ConfigMap uses Kubernetes Service DNS names:

```text
AI_SERVICE_URL=http://ai-inference-service:7000
GATEWAY_SERVICE_URL=http://api-gateway-service:8080
DATABASE_SERVICE_URL=http://database-service:8000
MONITORING_DATABASE_PATH=/data/monitoring.db
```

Verify that Kubernetes injected these values:

```powershell
kubectl exec deployment/monitoring-service -- printenv AI_SERVICE_URL
kubectl exec deployment/monitoring-service -- printenv GATEWAY_SERVICE_URL
kubectl exec deployment/monitoring-service -- printenv DATABASE_SERVICE_URL
kubectl exec deployment/monitoring-service -- printenv MONITORING_DATABASE_PATH
```

The service currently needs no Kubernetes Secret because it uses no password,
token, or API key. Add a Secret if authenticated monitoring targets or external
integrations are introduced later.

Forward the Kubernetes service to host port `7003`:

```powershell
kubectl port-forward service/monitoring-service 7003:7002
```

Keep that command running, then test in another terminal:

```powershell
Invoke-RestMethod http://localhost:7003/health
Invoke-RestMethod http://localhost:7003/status | ConvertTo-Json -Depth 10
```

Open <http://localhost:7003/docs>. Port `7003` avoids conflicting with a
Compose monitoring container already published on host port `7002`.

`/health` checks the monitoring pod itself. `/status` checks the AI, gateway,
and database services. It can report `degraded` while the monitoring pod is
healthy if one of those other services has not been deployed in Kubernetes.

### Kubernetes troubleshooting

If the pod does not become ready:

```powershell
kubectl get pods
kubectl describe pod -l app=monitoring-service
kubectl logs deployment/monitoring-service
```

If the pod reports `ErrImageNeverPull`, rebuild and reload its local image:

```powershell
docker compose -f monitoring_service\compose.yaml build
minikube image load monitoring_service-monitoring-service:latest
kubectl rollout restart deployment/monitoring-service
```
