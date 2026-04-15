# SmartOps AI – Autonomous Incident Resolution Engine
> **Enterprise AIOps Platform** · Python + FastAPI · React + Vite · Docker · Prometheus + Grafana

---

## 🏗 Project Structure

```
Smart-Ops/
├── client/                     ← React + Vite Dashboard
│   ├── src/
│   ├── Dockerfile
│   └── package.json
│
└── server/                     ← Backend & Infrastructure
    ├── docker-compose.yml      ← Full stack: all services + monitoring
    ├── prometheus.yml          ← Prometheus configuration
    │
    ├── smartops_engine/        ← AI Engine (FastAPI backend)
    │   ├── main.py             ← Core: anomaly detect, RCA, remediation
    │   └── Dockerfile
    │
    └── microservices-lab/      ← Simulated microservices
        ├── user_service/       ← User + Redis session
        ├── order_service/      ← Orders + PostgreSQL
        ├── payment_service/    ← Payments (chaos-ready)
        └── k8s/                ← Kubernetes manifests
```

---

## 🚀 Deployment

### Full Docker Stack (Recommended)
Launch the entire ecosystem including all microservices, AI engine, and the React dashboard:

```bash
cd server
docker-compose up --build
```

| Service | Access URL |
|---|---|
| **Frontend Dashboard** | http://localhost:5173 |
| AI Engine API | http://localhost:9000 |
| API Interactive Docs | http://localhost:9000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (admin/smartops123) |

---

## 🧠 AI Engine — Capabilities

The AI Engine provides real-time monitoring and autonomous resolution for the microservices cluster.

### Chaos Scenarios
You can trigger chaos directly via the Dashboard or API to observe AI response:
- `cpu_stress`   → Simulates CPU overload
- `mem_leak`     → Gradual memory growth
- `crash`        → Sudden container failure
- `net_delay`    → Injected network latency

### Auto-Remediation
When enabled, the engine will automatically attempt to resolve detected incidents (e.g., restarting crashed pods, scaling resources).

---

## 🔧 Tech Stack

- **Frontend**: React 18, Vite, Chart.js, Lucide Icons
- **AI Engine**: Python 3.11, FastAPI, WebSockets
- **Microservices**: Python, Redis, PostgreSQL
- **Monitoring**: Prometheus, Grafana
- **Infrastructure**: Docker, Docker Compose, Kubernetes

---

*Built with SmartOps AI – Autonomous Incident Resolution Engine v2.5*
