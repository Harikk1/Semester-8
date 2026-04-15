# 🚀 SmartOps AI - Quick Start Guide

## Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js 18+
- npm or yarn

## Step 1: Start Infrastructure (Terminal 1)

```bash
cd server
docker-compose up -d
```

**Wait 30 seconds** for all services to start. Verify:
```bash
docker-compose ps
```

All services should show "healthy" status.

## Step 2: Start SmartOps Engine (Terminal 2)

```bash
cd server/smartops_engine
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 9000 --reload
```

You should see:
```
INFO:     SmartOps AI Engine started with ENHANCED ACCURACY MODE
```

## Step 3: Start Dashboard (Terminal 3)

```bash
cd client
npm install
npm run dev
```

Dashboard will be available at: **http://localhost:5173**

## Step 4: Test the System

### Option A: Generate Demo Incident (Instant)

1. Open dashboard: http://localhost:5173
2. Login with any email (e.g., `admin@smartops.ai`)
3. Navigate to **"Root Cause"** tab
4. Click **"Generate Demo Incident"** button
5. Watch the incident appear in real-time!

### Option B: Trigger Real Anomaly

1. Navigate to **"Root Cause"** tab
2. Click **"CPU Stress Test"** or **"Memory Leak Test"**
3. Wait 15-30 seconds for detection
4. Watch anomaly → RCA → remediation flow

### Option C: API Testing

```bash
# Generate demo incident
curl -X POST http://localhost:9000/api/demo/generate-incident

# Trigger CPU stress
curl -X POST http://localhost:9000/api/simulate/cpu_stress/order_service

# Check incidents
curl http://localhost:9000/api/incidents

# Check anomalies
curl http://localhost:9000/api/anomalies
```

## What You Should See

### Root Cause Page Features:
- ✅ **Live Updates** - Refreshes every second with pulse animation
- ✅ **Incident Cards** - Shows primary cause, severity, correlation strength
- ✅ **Contributing Factors** - Probability bars with correlated metrics
- ✅ **Remediation Protocol** - Auto-generated kubectl commands
- ✅ **Affected Metrics** - Visual tags showing impacted metrics
- ✅ **Real-Time Timestamps** - Live clock and incident analysis time

### Expected Incident Example:
```
CPU Exhaustion
ID: INC-2025-0848 | CRITICAL | Correlation: 85%

CPU utilization critical at 92.5% (163% above baseline). 
P95 latency degraded to 1250ms. Likely compute-bound workload 
or inefficient algorithm.

Contributing Factors:
- CPU Exhaustion: 94.1% (correlated: latency_p95)
- Thread Pool Exhaustion: 89.3% (correlated: latency_p95)
- Network Latency: 65.2%

Remediation Protocol:
✅ Scale up CPU-bound pods (RUNNING)
⏳ Restart affected pods (PENDING)
```

## Troubleshooting

### Services Not Starting
```bash
# Check Docker logs
docker-compose logs -f

# Restart specific service
docker-compose restart order_service
```

### No Incidents Appearing
1. Check WebSocket connection (green "SYNC ACTIVE" badge)
2. Click "Generate Demo Incident" for instant test
3. Check browser console for errors (F12)
4. Verify engine is running: `curl http://localhost:9000/health`

### Prometheus Not Scraping
```bash
# Check Prometheus targets
open http://localhost:9090/targets

# All should show "UP" status
```

## Load Testing

```bash
# Install k6
# macOS: brew install k6
# Windows: choco install k6
# Linux: https://k6.io/docs/getting-started/installation/

# Run load test
cd server/microservices-lab
k6 run k6/load_test.js
```

Expected results:
- Success rate: >95%
- P95 latency: <2000ms
- Anomalies detected: 5-15
- Incidents generated: 2-5

## Monitoring URLs

- **Dashboard**: http://localhost:5173
- **SmartOps API**: http://localhost:9000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/smartops123)
- **User Service**: http://localhost:8000
- **Order Service**: http://localhost:8001
- **Payment Service**: http://localhost:8002

## Next Steps

1. **Explore Tabs**:
   - Overview: System health and throughput
   - Services: Individual service metrics
   - Anomalies: Real-time anomaly detection
   - Root Cause: Incident analysis (you are here!)
   - System Logs: Structured logging

2. **Test Scenarios**:
   - Generate multiple incidents
   - Compare correlation strengths
   - Watch auto-remediation
   - Monitor system recovery

3. **Advanced Testing**:
   - Run k6 load test
   - Trigger multiple simultaneous anomalies
   - Test service cascade failures
   - Validate RCA accuracy

## Stopping the System

```bash
# Stop dashboard (Ctrl+C in Terminal 3)
# Stop engine (Ctrl+C in Terminal 2)

# Stop infrastructure
cd server
docker-compose down

# Clean up (optional)
docker-compose down -v  # Removes volumes
```

## Support

- Check logs: `docker-compose logs -f`
- API docs: http://localhost:9000/docs
- Test script: `bash test_accuracy.sh`

---

**Enjoy SmartOps AI Beast Mode! 🚀**
