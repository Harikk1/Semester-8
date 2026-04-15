# SmartOps AI – Autonomous Incident Resolution Engine
> **Enterprise AIOps Platform** · Python + FastAPI · Docker + Kubernetes · Prometheus + Grafana · HTML/CSS/JS

---

## 🏗 Project Structure

```
Smart-Ops/
├── smartops-ai.html              ← Full-stack dashboard (open in browser)
├── start.bat                     ← Quick-start Windows launcher
├── start_engine.py               ← Python quick-start script
├── docker-compose.yml            ← Full stack: all services + monitoring
│
├── smartops_engine/              ← AI Engine (FastAPI backend)
│   ├── main.py                   ← Core: anomaly detect, RCA, remediation
│   ├── requirements.txt
│   └── Dockerfile
│
└── microservices-lab/            ← Simulated microservices
    ├── user_service/             ← User + Redis session
    ├── order_service/            ← Orders + PostgreSQL
    ├── payment_service/          ← Payments (chaos-ready)
    ├── database/init.sql
    ├── prometheus.yml
    ├── docker-compose.yml        ← Microservices only
    └── k8s/                      ← Kubernetes manifests
        ├── deployments.yaml
        ├── services.yaml
        └── hpa.yaml
```

---

## 🚀 Quick Start (3 options)

### Option 1 – Dashboard only (instant, no install)
```bash
# Just open the HTML file in your browser
start smartops-ai.html
```
> The dashboard runs in **Simulation Mode** automatically — full live charts, anomalies, RCA, and remediation without any backend.

---

### Option 2 – With AI Engine (WebSocket live data)
```bash
# Windows
start.bat

# Or Python
python start_engine.py
```
Then open `smartops-ai.html` → the dashboard auto-connects to `ws://localhost:9000/ws`.

---

### Option 3 – Full Docker Stack (all services)
```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Dashboard | `open smartops-ai.html` |
| AI Engine | http://localhost:9000 |
| API Docs | http://localhost:9000/docs |
| User Service | http://localhost:8000 |
| Order Service | http://localhost:8001 |
| Payment Service | http://localhost:8002 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/smartops123) |

---

## 🧠 AI Engine — REST API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/metrics` | Current metrics for all services |
| `GET` | `/api/metrics/history/{service}` | Historical metric data |
| `GET` | `/api/anomalies` | All detected anomalies |
| `GET` | `/api/incidents` | Root Cause Analysis results |
| `GET` | `/api/remediation` | Remediation action log |
| `POST` | `/api/simulate/{scenario}/{service}` | Trigger chaos scenario |
| `POST` | `/api/simulate/reset` | Reset all scenarios |
| `POST` | `/api/auto-remediation/toggle` | Toggle auto-mode |
| `WS` | `/ws` | Live metrics + alerts stream |

### Chaos Scenarios
```
cpu_stress   → Simulates CPU overload (→ stress-ng)
mem_leak     → Gradual memory growth  (→ OOMKill risk)
crash        → Pod crash + restart    (→ SIGKILL)
net_delay    → Network latency inject (→ tc netem)
```

---

## 📊 Dashboard Tabs

| Tab | Description |
|---|---|
| **Overview** | Live KPIs — CPU, Memory, RPS, Error Rate, Latency |
| **Services** | Per-service health cards + topology map |
| **Anomalies** | Real-time anomaly feed with AI confidence scores |
| **Root Cause** | ML-powered RCA with probability-ranked causes |
| **Remediation** | Auto-remediation queue + playbook library |
| **Logs** | Elasticsearch-style log stream with filter |
| **Load Test** | k6 results — VU timeline, latency percentiles |
| **Infrastructure** | K8s cluster, Docker images, monitoring stack |
| **Simulate** | Chaos engineering — trigger & observe AI response |

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| AI Engine | Python 3.11 + FastAPI + WebSockets |
| Microservices | FastAPI + SQLAlchemy + Redis |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Metrics | Prometheus (scrape 5s) |
| Visualization | Grafana + Chart.js |
| Log Analysis | Elasticsearch |
| Load Testing | k6 (JavaScript) |
| Containerization | Docker + Docker Compose |
| Orchestration | Kubernetes + HPA |
| Frontend | Vanilla HTML/CSS/JS (zero dependencies) |
| Fonts | Inter + JetBrains Mono (Google Fonts) |

---

## ⚙ Kubernetes Deploy

```bash
kubectl apply -f microservices-lab/k8s/deployments.yaml
kubectl apply -f microservices-lab/k8s/services.yaml
kubectl apply -f microservices-lab/k8s/hpa.yaml
```

---

*Built with SmartOps AI – Autonomous Incident Resolution Engine v2.0*
