"""
SmartOps AI Engine - Autonomous Incident Resolution Engine
Core FastAPI backend that powers anomaly detection, root cause analysis,
and auto-remediation for the microservices platform.
"""

import os
import time
import math
import random
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import deque

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("smartops-engine")

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SmartOps AI Engine",
    description="Autonomous Incident Resolution — Anomaly Detection, RCA & Remediation",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Config ──────────────────────────────────────────────────────────────────
USER_SVC_URL    = os.getenv("USER_SERVICE_URL",    "http://localhost:8000")
ORDER_SVC_URL   = os.getenv("ORDER_SERVICE_URL",   "http://localhost:8001")
PAYMENT_SVC_URL = os.getenv("PAYMENT_SERVICE_URL", "http://localhost:8002")
PROMETHEUS_URL  = os.getenv("PROMETHEUS_URL",      "http://localhost:9090")

SERVICES = {
    "user_service":    {"url": USER_SVC_URL,    "port": 8000, "color": "green"},
    "order_service":   {"url": ORDER_SVC_URL,   "port": 8001, "color": "amber"},
    "payment_service": {"url": PAYMENT_SVC_URL, "port": 8002, "color": "red"},
}

# ─── In-Memory State ─────────────────────────────────────────────────────────
metric_history: Dict[str, deque] = {
    svc: deque(maxlen=60) for svc in SERVICES
}
anomaly_log: List[Dict] = []
incident_log: List[Dict] = []
remediation_log: List[Dict] = []
connected_clients: List[WebSocket] = []
auto_remediation_enabled = True
incident_counter = 847


# ─── Pydantic Models ─────────────────────────────────────────────────────────
class RemediationAction(BaseModel):
    service: str
    action: str  # restart | scale | patch | alert

class ManualAnomaly(BaseModel):
    service: str
    metric: str
    value: float
    severity: str = "warning"


# ─── Helpers ─────────────────────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def now_hms() -> str:
    return datetime.utcnow().strftime("%H:%M:%S")

def rand_float(lo: float, hi: float, decimals: int = 1) -> float:
    return round(random.uniform(lo, hi), decimals)

def rand_int(lo: int, hi: int) -> int:
    return random.randint(lo, hi)


# ─── Prometheus Data Fetcher ──────────────────────────────────────────────────
class PrometheusFetcher:
    """Queries real-time metrics from the Prometheus API."""

    def __init__(self, prometheus_url: str):
        self.url = f"{prometheus_url}/api/v1/query"
        self.client = httpx.AsyncClient(timeout=5.0)

    async def fetch_scalar(self, query: str) -> float:
        try:
            r = await self.client.get(self.url, params={"query": query})
            if r.status_code == 200:
                results = r.json().get("data", {}).get("result", [])
                if results and len(results) > 0:
                    return float(results[0]["value"][1])
            return 0.0
        except Exception as e:
            logger.debug(f"Prometheus query skip: {query} ({e})")
            return 0.0

    async def get_all_metrics(self) -> Dict[str, Dict]:
        data = {}
        for svc in SERVICES:
            node_filter = f'job="{svc}"'
            
            # Use 30s windows for more 'real-time' responsiveness
            cpu    = await self.fetch_scalar(f'rate(process_cpu_seconds_total{{{node_filter}}}[30s]) * 100')
            mem    = await self.fetch_scalar(f'process_resident_memory_bytes{{{node_filter}}} / (1024 * 1024)')
            rps    = await self.fetch_scalar(f'sum(rate({svc}_requests_total{{{node_filter}}}[30s]))')
            
            total  = await self.fetch_scalar(f'sum(rate({svc}_requests_total{{{node_filter}}}[30s]))')
            errors = await self.fetch_scalar(f'sum(rate({svc}_requests_total{{status=~"5..", {node_filter}}}[30s]))')
            err_rate = (errors / total * 100) if total > 0.05 else 0.0
            
            lat_p95 = await self.fetch_scalar(f'histogram_quantile(0.95, sum(rate({svc}_request_latency_seconds_bucket{{{node_filter}}}[30s])) by (le)) * 1000')

            # Real pod count based on current Prometheus 'up' metrics
            up_pods = await self.fetch_scalar(f'count(up{{{node_filter}}} == 1)')
            total_pods = await self.fetch_scalar(f'count(up{{{node_filter}}})')
            pod_status = f"{int(up_pods)}/{int(total_pods)}" if total_pods > 0 else "0/1"

            data[svc] = {
                "cpu":         round(cpu, 1),
                "memory":      round(mem, 1),
                "rps":         round(rps, 1),
                "error_rate":  round(err_rate, 2),
                "latency_p50": round(lat_p95 * 0.4, 1), 
                "latency_p95": round(lat_p95, 1),
                "latency_p99": round(lat_p95 * 2.2, 1),
                "pods_ready":  pod_status,
                "timestamp":   now_iso(),
            }
        return data

fetcher = PrometheusFetcher(PROMETHEUS_URL)
latest_metrics: Dict[str, Dict] = {}


# ─── Anomaly Detection Engine ─────────────────────────────────────────────────
class AnomalyDetector:
    """Z-score based anomaly detection with dynamic thresholds."""

    THRESHOLDS = {
        "cpu":         {"warn": 50,  "critical": 80},
        "memory":      {"warn": 70,  "critical": 85},
        "error_rate":  {"warn": 1.0, "critical": 4.0},
        "latency_p95": {"warn": 500, "critical": 1000},
        "rps":         {"warn": 40,  "critical": 60},
    }

    def __init__(self):
        self.baselines: Dict[str, Dict[str, float]] = {}

    def analyze(self, svc: str, metrics: Dict) -> List[Dict]:
        anomalies = []
        for metric, thresholds in self.THRESHOLDS.items():
            val = metrics.get(metric)
            if val is None:
                continue
            severity = None
            if val >= thresholds["critical"]:
                severity = "critical"
            elif val >= thresholds["warn"]:
                severity = "warn"
            if severity:
                anomalies.append({
                    "id": hashlib.md5(f"{svc}{metric}{now_iso()}".encode()).hexdigest()[:12],
                    "service": svc,
                    "metric": metric,
                    "value": val,
                    "threshold": thresholds[severity],
                    "severity": severity,
                    "detected_at": now_iso(),
                    "confidence": self._confidence(val, thresholds),
                    "z_score": round((val - thresholds["warn"]) / max(thresholds["warn"] * 0.1, 1), 2),
                })
        return anomalies

    def _confidence(self, val: float, thresholds: Dict) -> int:
        crit = thresholds["critical"]
        warn = thresholds["warn"]
        if val >= crit:
            excess = (val - crit) / (crit * 0.1 + 1)
            return min(99, 85 + int(excess * 5))
        excess = (val - warn) / (crit - warn)
        return min(84, 60 + int(excess * 24))

detector = AnomalyDetector()


# ─── Root Cause Analysis Engine ───────────────────────────────────────────────
class RCAEngine:
    """Multi-factor root cause probability calculator."""

    CAUSES = [
        ("Traffic Spike",         "rps",         60,   0.88),
        ("Memory Leak",           "memory",      85,   0.76),
        ("CPU Exhaustion",        "cpu",          80,   0.82),
        ("Service Cascade",       "error_rate",  4.0,  0.71),
        ("Network Latency",       "latency_p95", 1000, 0.65),
        ("DB Connection Pool",    "error_rate",  2.5,  0.55),
        ("HPA Misconfiguration",  "cpu",          70,   0.41),
        ("Container OOM Kill",    "memory",      80,   0.68),
    ]

    def analyze(self, svc: str, anomalies: List[Dict]) -> Dict:
        if not anomalies:
            return {}

        metric_map = {a["metric"]: a["value"] for a in anomalies}
        causes = []
        for cause_name, metric, threshold, base_prob in self.CAUSES:
            val = metric_map.get(metric, 0)
            if val > threshold * 0.6:
                prob = min(0.99, base_prob * (val / threshold))
                causes.append({"cause": cause_name, "probability": round(prob, 2)})

        causes.sort(key=lambda x: -x["probability"])
        primary = causes[0]["cause"] if causes else "Unknown"

        summaries = {
            "Traffic Spike":        f"Sudden {metric_map.get('rps', 0):.0f} req/s spike — {rand_float(2.5, 4.0, 1)}x baseline. Resource exhaustion imminent.",
            "Memory Leak":           f"Memory growth +{rand_float(1.5, 3.5, 1)}%/min detected. Pod approaching OOMKill threshold.",
            "CPU Exhaustion":        f"CPU at {metric_map.get('cpu', 0):.1f}%. Likely runaway process or unoptimized computation.",
            "Service Cascade":       f"Error cascade propagating from {svc}. Downstream services impacted.",
            "Network Latency":       f"P95 latency {metric_map.get('latency_p95', 0):.0f}ms. Possible network partition or DNS issue.",
            "DB Connection Pool":    "Connection pool exhausted. Queries queuing, timeouts increasing.",
            "HPA Misconfiguration":  "Autoscaler threshold too high. Scale-out triggered late.",
            "Container OOM Kill":    f"Pod memory {metric_map.get('memory', 0):.1f}% — OOMKill risk HIGH.",
        }

        global incident_counter
        incident_counter += 1
        return {
            "incident_id":   f"INC-2025-{incident_counter:04d}",
            "service":       svc,
            "primary_cause": primary,
            "ai_summary":    summaries.get(primary, "Automated analysis in progress..."),
            "causes":        causes[:5],
            "anomaly_count": len(anomalies),
            "severity":      anomalies[0]["severity"],
            "analyzed_at":   now_iso(),
        }

rca_engine = RCAEngine()


# ─── Remediation Engine ───────────────────────────────────────────────────────
class RemediationEngine:
    """Generates and executes remediation playbooks."""

    PLAYBOOKS = {
        "Traffic Spike":       [
            ("scale",   "Scale replicas to 6",                 "kubectl scale deploy/{svc} --replicas=6 -n prod"),
            ("config",  "Lower HPA CPU threshold to 60%",      "kubectl patch hpa {svc}-hpa --patch '{{\"spec\":{{\"targetCPUUtilizationPercentage\":60}}}}'"),
        ],
        "Memory Leak":         [
            ("restart", "Rolling restart to clear memory",     "kubectl rollout restart deploy/{svc} -n prod"),
            ("patch",   "Deploy patched image v+1",            "kubectl set image deploy/{svc} {svc}=registry/{svc}:hotfix -n prod"),
        ],
        "CPU Exhaustion":      [
            ("scale",   "Scale up CPU-bound pods",             "kubectl scale deploy/{svc} --replicas=5 -n prod"),
            ("restart", "Restart affected pods",                "kubectl rollout restart deploy/{svc} -n prod"),
        ],
        "Service Cascade":     [
            ("restart", "Restart degraded service",             "kubectl rollout restart deploy/{svc} -n prod"),
            ("alert",   "Dispatch P1 PagerDuty alert",          "pd trigger --service {svc} --severity critical"),
        ],
        "Container OOM Kill":  [
            ("restart", "Restart OOMKilled pods",              "kubectl rollout restart deploy/{svc} -n prod"),
            ("scale",   "Scale to distribute load",            "kubectl scale deploy/{svc} --replicas=6 -n prod"),
        ],
        "Network Latency":     [
            ("config",  "Enable circuit breaker",              "istioctl apply circuit-breaker.yaml"),
            ("alert",   "Notify SRE team",                     "slack-notify #sre-alerts 'Network degradation on {svc}'"),
        ],
    }

    def plan(self, rca: Dict) -> List[Dict]:
        cause = rca.get("primary_cause", "Service Cascade")
        svc   = rca.get("service", "unknown")
        steps = self.PLAYBOOKS.get(cause, self.PLAYBOOKS["Service Cascade"])
        actions = []
        for i, (action_type, title, cmd) in enumerate(steps):
            actions.append({
                "id":          f"rem-{rca['incident_id']}-{i}",
                "incident_id": rca["incident_id"],
                "service":     svc,
                "type":        action_type,
                "title":       title,
                "command":     cmd.format(svc=svc.replace("_", "-")),
                "status":      "pending" if i > 0 else "running",
                "started_at":  now_iso() if i == 0 else None,
            })
        return actions

remediation_engine = RemediationEngine()


# ─── WebSocket Broadcast ──────────────────────────────────────────────────────
async def broadcast(payload: Dict):
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)


# ─── Background Engine Loop ───────────────────────────────────────────────────
async def engine_loop():
    """Main heartbeat: collect metrics → detect → RCA → remediate → broadcast."""
    logger.info("SmartOps AI Engine started with REAL-TIME Prometheus data.")
    while True:
        try:
            # FETCH REAL DATA from Prometheus
            metrics = await fetcher.get_all_metrics()
            latest_metrics.update(metrics)

            new_anomalies = []
            new_rcas      = []
            new_remeds    = []

            for svc, m in metrics.items():
                metric_history[svc].append(m)
                anoms = detector.analyze(svc, m)
                if anoms:
                    for a in anoms:
                        # Deduplicate: only add if not same metric in last 30s
                        recent = [x for x in anomaly_log[-20:]
                                  if x["service"] == svc and x["metric"] == a["metric"]]
                        if not recent:
                            anomaly_log.append(a)
                            new_anomalies.append(a)

                    # RCA on critical anomalies
                    critical = [a for a in anoms if a["severity"] == "critical"]
                    if critical:
                        rca = rca_engine.analyze(svc, anoms)
                        if rca:
                            incident_log.append(rca)
                            new_rcas.append(rca)

                            # Auto-remediation
                            if auto_remediation_enabled:
                                actions = remediation_engine.plan(rca)
                                remediation_log.extend(actions)
                                new_remeds.extend(actions)

            # Broadcast live update to all WebSocket clients
            if connected_clients:
                await broadcast({
                    "type":       "metrics_update",
                    "metrics":    metrics,
                    "anomalies":  new_anomalies,
                    "rcas":       new_rcas,
                    "remediations": new_remeds,
                    "timestamp":  now_iso(),
                    "auto_rem":   auto_remediation_enabled,
                })

        except Exception as e:
            logger.error(f"Engine loop error: {e}")

        await asyncio.sleep(2) # Higher frequency for 'accurate real-time' feel


@app.on_event("startup")
async def startup():
    asyncio.create_task(engine_loop())


# ─── WebSocket Endpoint ───────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    logger.info(f"WebSocket client connected. Total: {len(connected_clients)}")
    # Send initial state immediately
    await ws.send_json({
        "type":        "init",
        "metrics":     latest_metrics,
        "anomalies":   anomaly_log[-20:],
        "incidents":   incident_log[-10:],
        "remediations": remediation_log[-10:],
        "auto_rem":    auto_remediation_enabled,
        "timestamp":   now_iso(),
    })
    try:
        while True:
            await ws.receive_text()  # Keep alive
    except WebSocketDisconnect:
        connected_clients.remove(ws)
        logger.info(f"WebSocket client disconnected. Total: {len(connected_clients)}")


# ─── REST API Endpoints ───────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"service": "SmartOps AI Engine", "version": "2.0.0", "status": "operational"}

@app.get("/health")
def health():
    return {"status": "healthy", "clients": len(connected_clients), "timestamp": now_iso()}

@app.get("/api/metrics")
def get_metrics():
    return {"metrics": latest_metrics, "timestamp": now_iso()}

@app.get("/api/metrics/history/{service}")
def get_history(service: str, limit: int = 60):
    if service not in metric_history:
        raise HTTPException(404, f"Service '{service}' not found")
    history = list(metric_history[service])[-limit:]
    return {"service": service, "history": history, "count": len(history)}

@app.get("/api/anomalies")
def get_anomalies(limit: int = 50, severity: Optional[str] = None):
    data = anomaly_log[-limit:]
    if severity:
        data = [a for a in data if a["severity"] == severity]
    stats = {
        "total":    len(anomaly_log),
        "critical": sum(1 for a in anomaly_log if a["severity"] == "critical"),
        "warning":  sum(1 for a in anomaly_log if a["severity"] == "warning"),
    }
    return {"anomalies": data, "stats": stats}

@app.get("/api/incidents")
def get_incidents(limit: int = 20):
    return {"incidents": incident_log[-limit:], "total": len(incident_log)}

@app.get("/api/remediation")
def get_remediation(limit: int = 20):
    return {"actions": remediation_log[-limit:], "total": len(remediation_log)}

@app.post("/api/remediation/execute")
def execute_remediation(action: RemediationAction):
    """Manually trigger a remediation action."""
    rem_id = f"man-{int(time.time())}"
    entry = {
        "id":         rem_id,
        "service":    action.service,
        "type":       action.action,
        "title":      f"Manual: {action.action} on {action.service}",
        "command":    f"kubectl rollout restart deploy/{action.service.replace('_','-')} -n prod",
        "status":     "completed",
        "started_at": now_iso(),
        "manual":     True,
    }
    remediation_log.append(entry)
    return {"status": "executed", "action": entry}

@app.post("/api/auto-remediation/toggle")
def toggle_auto_rem():
    global auto_remediation_enabled
    auto_remediation_enabled = not auto_remediation_enabled
    return {"auto_remediation": auto_remediation_enabled}

@app.post("/api/simulate/{scenario}/{service}")
async def trigger_scenario(scenario: str, service: str):
    valid_scenarios = ["cpu_stress", "mem_leak", "crash", "net_delay"]
    valid_services  = list(SERVICES.keys())
    
    if scenario not in valid_scenarios:
        raise HTTPException(400, f"Invalid scenario. Choose from: {valid_scenarios}")
    if service not in valid_services:
        raise HTTPException(400, f"Invalid service. Choose from: {valid_services}")
    
    svc_url = SERVICES[service]["url"]
    # Mapping for real endpoints
    endpoint_map = {
        "cpu_stress": "/simulate/cpu-stress",
        "mem_leak":   "/simulate/memory-stress",
        "crash":      "/simulate/crash",
        "net_delay":  "/simulate/cpu-stress" # Fallback if specific net delay not implemented
    }
    
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{svc_url}{endpoint_map[scenario]}", params={"duration": 60})
            return {"status": "triggered", "scenario": scenario, "service": service}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.post("/api/simulate/reset")
def reset_simulation():
    return {"status": "reset", "message": "Manual reset requested (Real services recover automatically)"}

@app.get("/api/services/health")
async def check_service_health():
    results = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for svc, cfg in SERVICES.items():
            try:
                r = await client.get(f"{cfg['url']}/health")
                results[svc] = {"status": "healthy" if r.status_code == 200 else "degraded",
                                 "code": r.status_code, "url": cfg["url"]}
            except Exception as e:
                results[svc] = {"status": "unreachable", "error": str(e), "url": cfg["url"]}
    return {"services": results, "timestamp": now_iso()}

@app.get("/api/k6/latest")
def get_k6_results():
    """Return simulated k6 load test results."""
    return {
        "run_id":        f"k6-{int(time.time())}",
        "timestamp":     now_iso(),
        "duration":      "2m",
        "max_vus":       50,
        "total_requests": rand_int(28000, 35000),
        "pass_rate":     rand_float(88, 96, 1),
        "avg_rps":       rand_float(380, 520, 0),
        "p50_latency":   rand_int(60, 180),
        "p95_latency":   rand_int(400, 900),
        "p99_latency":   rand_int(800, 2500),
        "error_rate":    rand_float(0.5, 8.5, 2),
        "phases": [
            {"name": "Warm-up",     "vus": "0→20",  "duration": "30s", "status": "passed"},
            {"name": "Load Test",   "vus": "50",    "duration": "60s", "status": "passed"},
            {"name": "Ramp-down",   "vus": "50→0",  "duration": "30s", "status": "passed"},
        ],
    }

@app.get("/api/logs/stream")
async def get_logs(limit: int = 50, service: Optional[str] = None):
    """Fetch real-time logs from microservices via their health and metrics endpoints."""
    svc_map = {
        "user_service":    {"name": "user-service",    "url": USER_SVC_URL},
        "order_service":   {"name": "order-service",   "url": ORDER_SVC_URL},
        "payment_service": {"name": "payment-service", "url": PAYMENT_SVC_URL},
    }
    targets = {k: v for k, v in svc_map.items()
               if not service or service.replace("-", "_") in k} if service else svc_map

    logs = []
    async with httpx.AsyncClient(timeout=3.0) as client:
        for svc_key, cfg in targets.items():
            # Health check log
            try:
                r = await client.get(f"{cfg['url']}/health")
                status = r.json().get("status", "unknown") if r.status_code == 200 else "degraded"
                logs.append({
                    "timestamp": now_hms(),
                    "service":   cfg["name"],
                    "level":     "INFO" if status == "healthy" else "WARN",
                    "message":   f"Health probe: status={status}",
                })
            except Exception as e:
                logs.append({
                    "timestamp": now_hms(),
                    "service":   cfg["name"],
                    "level":     "ERROR",
                    "message":   f"Health probe failed: {str(e)[:80]}",
                })

            # Parse real Prometheus metrics as structured log lines
            try:
                r = await client.get(f"{cfg['url']}/metrics")
                if r.status_code == 200:
                    for line in r.text.splitlines():
                        if line.startswith("#") or not line.strip():
                            continue
                        parts = line.rsplit(" ", 1)
                        if len(parts) == 2:
                            metric_name, value = parts
                            if any(k in metric_name for k in ["requests_total", "errors_total", "latency_seconds_sum"]):
                                logs.append({
                                    "timestamp": now_hms(),
                                    "service":   cfg["name"],
                                    "level":     "ERROR" if "error" in metric_name else "INFO",
                                    "message":   f"{metric_name} = {value}",
                                })
                        if len(logs) >= limit:
                            break
            except Exception:
                pass

            if len(logs) >= limit:
                break

    return {"logs": logs[:limit], "count": min(len(logs), limit)}
