# SmartOps AI: Autonomous Operations Platform

SmartOps AI is a state-of-the-art AIOps platform designed for autonomous incident detection, root cause analysis (RCA), and remediation.

## 🚀 Quick Start Guide

To run the entire platform, follow these steps in **three separate terminals**:

### 1. Launch Infrastructure
Starts Prometheus, Redis, and the Microservices (User, Order, Payment).
```powershell
cd server
docker-compose up -d
```
*Verification: Prometheus will be live at [http://localhost:9090](http://localhost:9090).*

### 2. Start SmartOps AI Engine
Starts the FastAPI backend for real-time telemetry analytics and anomaly detection.
```powershell
cd server/smartops_engine
python -m uvicorn main:app --host 0.0.0.0 --port 9000 --reload
```
*API will be live at [http://localhost:9000](http://localhost:9000).*

### 3. Start The Dashboard (Client)
Starts the ultra-minimalist React dashboard.
```powershell
cd client
npm run dev
```
*Dashboard will be live at [http://localhost:5173](http://localhost:5173).*

---

## 🛠 Features
- **Ultra-Minimalist Dashboard**: A professional "Command Interface" with Light/Dark theme support.
- **Autonomous Remediation**: Real-time detection and resolution of system anomalies.
- **Secure Access**: Integrated Google Login and Operator Profile management.
- **Telemetry Flow**: Live infrastructure metrics synced via WebSockets.

## 📦 Architecture
- **Server**: FastAPI, Prometheus, Docker, Python Microservices.
- **Client**: React, Vite, Chart.js, Lucide-React.
