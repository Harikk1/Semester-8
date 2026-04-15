# 🚀 Enterprise SmartOps Microservices Lab

This project is a realistic, production-style microservices application designed to test **Enterprise SmartOps** platforms. It includes 3 interconnected services, persistence, caching, and built-in chaos/failure simulation.

## 🏗 Architecture
- **User Service (Port 8000):** Entry point. Handles cache (Redis) and calls Order Service.
- **Order Service (Port 8001):** Manages order logic, persists to PostgreSQL, and calls Payment Service with retries.
- **Payment Service (Port 8002):** Processes payments and injects random failures/latency.

## 🛠 Tech Stack
- **Framework:** FastAPI (Python 3.10)
- **Database:** PostgreSQL (Persistence)
- **Cache:** Redis
- **Monitoring:** Prometheus Metrics (`/metrics`)
- **Logging:** JSON-formatted logs for ELK/Splunk compatibility.
- **Tracing:** Trace/Request ID propagation.

---

## 🚀 Getting Started (Docker Compose)

### 1. Build and Start
```bash
docker-compose up --build
```

### 2. Verify Services
- **User Service:** http://localhost:8000/health
- **Order Service:** http://localhost:8001/health
- **Payment Service:** http://localhost:8002/health
- **Prometheus:** http://localhost:9090

### 3. Send a Test Request
```bash
curl -X POST http://localhost:8000/register_order \
     -H "Content-Type: application/json" \
     -d '{"user_id": 1, "amount": 99.99}'
```

---

## 💥 Failure & Chaos Simulation

Testing SmartOps requires realistic anomalies. Use these endpoints to trigger them:

### CPU Stress
Toggles high CPU usage for N seconds.
`GET http://localhost:8000/simulate/cpu-stress?duration=30`

### Memory Leak
Simulates a memory leak by allocating MBs of memory.
`GET http://localhost:8000/simulate/memory-stress?mb=200`

### Random Failures
The **Payment Service** has a default 10% failure rate and 0.5s latency. Change these via Env Vars in `docker-compose.yml`:
- `FAILURE_RATE`: 0.0 to 1.0
- `MAX_LATENCY`: value in seconds

### Crash Service
Force kill a service process to test K8s self-healing.
`GET http://localhost:8002/simulate/crash`

---

## 📈 Load Testing (k6)

Generate traffic spikes to test autoscaling and anomaly detection.

1. **Install k6:** [k6.io](https://k6.io/docs/getting-started/installation/)
2. **Run Test:**
```bash
k6 run k6/load_test.js
```

---

## ☸ Kubernetes Deployment

### 1. Build Images
Ensure your images are available to your cluster (e.g., Push to registry or use local Minikube/Kind load).

### 2. Deploy Manifests
```bash
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/deployments.yaml
kubectl apply -f k8s/hpa.yaml
```

---

## 📊 SmartOps Monitoring Integration

### Anomaly Detection
SmartOps should monitor the following metrics from `/metrics`:
- `python_info`: Process status.
- `*_requests_total`: Monitor the `status` label for 5xx spikes.
- `*_request_latency_seconds`: Monitor for latency degradation.
- `python_gc_objects_collected`: Monitor for possible memory leaks.

### Root Cause Analysis (RCA)
Each log entry includes a `request_id`. SmartOps can correlate errors across services using this ID:
`User Service (req-123) -> Order Service (ord-1-456) -> Payment Service (req-123)`
*Note: The Request ID from User Service is passed as `X-Request-ID` header.*

---

## 📂 Project Structure
```text
microservices-lab/
├── user_service/        # Entrypoint (Port 8000)
├── order_service/       # DB Logic (Port 8001)
├── payment_service/     # Core Processing (Port 8002)
├── database/            # SQL Init scripts
├── k8s/                 # K8s Manifests
├── k6/                  # Load test scripts
├── docker-compose.yml   # Local orchestration
└── requirements.txt     # Python Deps
```
