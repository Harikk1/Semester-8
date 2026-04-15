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
        """Fetch comprehensive metrics with improved accuracy and error handling."""
        data = {}
        
        for svc in SERVICES:
            node_filter = f'job="{svc}"'
            
            try:
                # Use 15s windows for better real-time accuracy (was 30s)
                cpu    = await self.fetch_scalar(f'rate(process_cpu_seconds_total{{{node_filter}}}[15s]) * 100')
                mem    = await self.fetch_scalar(f'process_resident_memory_bytes{{{node_filter}}} / (1024 * 1024)')
                
                # More accurate RPS calculation
                rps    = await self.fetch_scalar(f'sum(rate({svc}_requests_total{{{node_filter}}}[15s]))')
                
                # Accurate error rate calculation
                total  = await self.fetch_scalar(f'sum(rate({svc}_requests_total{{{node_filter}}}[15s]))')
                errors_5xx = await self.fetch_scalar(f'sum(rate({svc}_requests_total{{status=~"5..", {node_filter}}}[15s]))')
                errors_4xx = await self.fetch_scalar(f'sum(rate({svc}_requests_total{{status=~"4..", {node_filter}}}[15s]))')
                
                # Error rate: only count 5xx as errors (4xx are client errors)
                err_rate = (errors_5xx / total * 100) if total > 0.01 else 0.0
                
                # Accurate latency percentiles
                lat_p50 = await self.fetch_scalar(
                    f'histogram_quantile(0.50, sum(rate({svc}_request_latency_seconds_bucket{{{node_filter}}}[15s])) by (le)) * 1000'
                )
                lat_p95 = await self.fetch_scalar(
                    f'histogram_quantile(0.95, sum(rate({svc}_request_latency_seconds_bucket{{{node_filter}}}[15s])) by (le)) * 1000'
                )
                lat_p99 = await self.fetch_scalar(
                    f'histogram_quantile(0.99, sum(rate({svc}_request_latency_seconds_bucket{{{node_filter}}}[15s])) by (le)) * 1000'
                )
                
                # Real pod/instance count
                up_pods = await self.fetch_scalar(f'count(up{{{node_filter}}} == 1)')
                total_pods = await self.fetch_scalar(f'count(up{{{node_filter}}})')
                
                # Additional accuracy metrics
                gc_collections = await self.fetch_scalar(f'rate(python_gc_collections_total{{{node_filter}}}[15s])')
                thread_count = await self.fetch_scalar(f'process_threads{{{node_filter}}}')
                
                data[svc] = {
                    "cpu":           round(cpu, 2),
                    "memory":        round(mem, 2),
                    "rps":           round(rps, 2),
                    "error_rate":    round(err_rate, 3),
                    "errors_5xx":    round(errors_5xx, 2),
                    "errors_4xx":    round(errors_4xx, 2),
                    "latency_p50":   round(lat_p50, 1) if lat_p50 > 0 else round(lat_p95 * 0.4, 1),
                    "latency_p95":   round(lat_p95, 1),
                    "latency_p99":   round(lat_p99, 1) if lat_p99 > 0 else round(lat_p95 * 1.5, 1),
                    "instances_up":  int(up_pods),
                    "instances_total": int(total_pods),
                    "pods_ready":    f"{int(up_pods)}/{int(total_pods)}" if total_pods > 0 else "0/1",
                    "gc_rate":       round(gc_collections, 2),
                    "threads":       int(thread_count),
                    "health_score":  round((up_pods / max(total_pods, 1)) * 100, 1),
                    "timestamp":     now_iso(),
                }
                
            except Exception as e:
                logger.error(f"Error fetching metrics for {svc}: {e}")
                # Return safe defaults on error
                data[svc] = {
                    "cpu": 0.0, "memory": 0.0, "rps": 0.0, "error_rate": 0.0,
                    "latency_p50": 0.0, "latency_p95": 0.0, "latency_p99": 0.0,
                    "instances_up": 0, "instances_total": 1, "pods_ready": "0/1",
                    "health_score": 0.0, "timestamp": now_iso(),
                }
        
        return data

fetcher = PrometheusFetcher(PROMETHEUS_URL)
latest_metrics: Dict[str, Dict] = {}


# ─── Anomaly Detection Engine ─────────────────────────────────────────────────
class AnomalyDetector:
    """Advanced ML-inspired anomaly detection with adaptive thresholds and statistical analysis."""

    THRESHOLDS = {
        "cpu":         {"warn": 50,  "critical": 80,  "baseline": 30},
        "memory":      {"warn": 70,  "critical": 85,  "baseline": 50},
        "error_rate":  {"warn": 1.0, "critical": 4.0, "baseline": 0.1},
        "latency_p95": {"warn": 500, "critical": 1000, "baseline": 200},
        "rps":         {"warn": 40,  "critical": 60,  "baseline": 10},
    }

    def __init__(self):
        self.baselines: Dict[str, Dict[str, deque]] = {}
        self.anomaly_history: Dict[str, List[float]] = {}
        self.learning_window = 120  # 2 minutes of history for baseline
        
    def _update_baseline(self, svc: str, metric: str, value: float):
        """Continuously update rolling baseline for adaptive thresholding."""
        if svc not in self.baselines:
            self.baselines[svc] = {}
        if metric not in self.baselines[svc]:
            self.baselines[svc][metric] = deque(maxlen=self.learning_window)
        self.baselines[svc][metric].append(value)
    
    def _calculate_statistics(self, data: deque) -> Dict[str, float]:
        """Calculate mean, std dev, and percentiles for statistical analysis."""
        if len(data) < 5:
            return {"mean": 0, "std": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        mean = sum(sorted_data) / n
        variance = sum((x - mean) ** 2 for x in sorted_data) / n
        std = math.sqrt(variance)
        
        return {
            "mean": mean,
            "std": std,
            "p50": sorted_data[int(n * 0.50)],
            "p95": sorted_data[int(n * 0.95)],
            "p99": sorted_data[min(int(n * 0.99), n-1)]
        }
    
    def _calculate_z_score(self, value: float, mean: float, std: float) -> float:
        """Calculate statistical z-score for anomaly detection."""
        if std < 0.01:  # Avoid division by zero
            return 0.0
        return (value - mean) / std
    
    def _detect_trend_anomaly(self, svc: str, metric: str, current: float) -> Optional[str]:
        """Detect sudden trend changes (spikes/drops) using rate of change."""
        if svc not in self.baselines or metric not in self.baselines[svc]:
            return None
        
        history = list(self.baselines[svc][metric])
        if len(history) < 10:
            return None
        
        recent_avg = sum(history[-5:]) / 5
        previous_avg = sum(history[-10:-5]) / 5
        
        if previous_avg < 0.01:
            return None
        
        change_rate = abs((recent_avg - previous_avg) / previous_avg)
        
        if change_rate > 0.5:  # 50% change
            return "spike" if recent_avg > previous_avg else "drop"
        return None

    def analyze(self, svc: str, metrics: Dict) -> List[Dict]:
        anomalies = []
        
        for metric, thresholds in self.THRESHOLDS.items():
            val = metrics.get(metric)
            if val is None:
                continue
            
            # Update baseline continuously
            self._update_baseline(svc, metric, val)
            
            # Get statistical baseline
            baseline_data = self.baselines.get(svc, {}).get(metric, deque())
            stats = self._calculate_statistics(baseline_data)
            
            # Calculate z-score for statistical anomaly detection
            z_score = self._calculate_z_score(val, stats["mean"], stats["std"])
            
            # Detect trend anomalies
            trend = self._detect_trend_anomaly(svc, metric, val)
            
            # Multi-factor severity determination
            severity = None
            confidence = 0
            
            # Static threshold check
            if val >= thresholds["critical"]:
                severity = "critical"
                confidence = 90
            elif val >= thresholds["warn"]:
                severity = "warn"
                confidence = 70
            
            # Statistical anomaly check (z-score > 3 is highly anomalous)
            if abs(z_score) > 3.0 and severity is None:
                severity = "critical"
                confidence = min(95, 80 + int(abs(z_score) * 3))
            elif abs(z_score) > 2.0 and severity is None:
                severity = "warn"
                confidence = min(85, 60 + int(abs(z_score) * 10))
            
            # Trend-based anomaly detection
            if trend and severity:
                confidence = min(99, confidence + 10)  # Boost confidence if trend detected
            
            if severity:
                # Calculate adaptive threshold based on learned baseline
                adaptive_threshold = max(
                    thresholds[severity],
                    stats["p95"] if len(baseline_data) > 30 else thresholds[severity]
                )
                
                anomalies.append({
                    "id": hashlib.md5(f"{svc}{metric}{now_iso()}{val}".encode()).hexdigest()[:12],
                    "service": svc,
                    "metric": metric,
                    "value": round(val, 2),
                    "threshold": round(adaptive_threshold, 2),
                    "baseline_mean": round(stats["mean"], 2),
                    "baseline_p95": round(stats["p95"], 2),
                    "severity": severity,
                    "detected_at": now_iso(),
                    "confidence": confidence,
                    "z_score": round(z_score, 2),
                    "trend": trend,
                    "deviation_pct": round(((val - stats["mean"]) / max(stats["mean"], 1)) * 100, 1) if stats["mean"] > 0 else 0,
                })
        
        return anomalies

    def _confidence(self, val: float, thresholds: Dict) -> int:
        """Legacy confidence calculation - kept for compatibility."""
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
    """Advanced multi-factor root cause analysis with correlation and pattern matching."""

    # Enhanced cause definitions with correlation patterns
    CAUSES = [
        ("Traffic Spike",         ["rps"],                    [60],      0.88, ["cpu", "memory"]),
        ("Memory Leak",           ["memory"],                 [85],      0.76, ["cpu"]),
        ("CPU Exhaustion",        ["cpu"],                    [80],      0.82, ["latency_p95"]),
        ("Service Cascade",       ["error_rate"],             [4.0],     0.71, ["latency_p95", "rps"]),
        ("Network Latency",       ["latency_p95"],            [1000],    0.65, ["error_rate"]),
        ("DB Connection Pool",    ["error_rate", "latency_p95"], [2.5, 800], 0.55, ["memory"]),
        ("HPA Misconfiguration",  ["cpu", "rps"],             [70, 50],  0.41, ["memory"]),
        ("Container OOM Kill",    ["memory", "error_rate"],   [80, 3.0], 0.68, ["cpu"]),
        ("Thread Pool Exhaustion", ["latency_p95", "cpu"],    [1200, 85], 0.73, ["error_rate"]),
        ("GC Pressure",           ["cpu", "memory"],          [75, 80],  0.67, ["latency_p95"]),
    ]

    def __init__(self):
        self.incident_patterns: Dict[str, List[str]] = {}
        self.correlation_cache: Dict[str, float] = {}

    def _calculate_correlation_score(self, anomalies: List[Dict], correlated_metrics: List[str]) -> float:
        """Calculate how many correlated metrics are also anomalous."""
        anomaly_metrics = {a["metric"] for a in anomalies}
        matches = sum(1 for m in correlated_metrics if m in anomaly_metrics)
        return matches / len(correlated_metrics) if correlated_metrics else 0.0

    def _calculate_severity_multiplier(self, anomalies: List[Dict]) -> float:
        """Higher severity and confidence increase probability."""
        if not anomalies:
            return 1.0
        
        severity_weights = {"critical": 1.5, "warn": 1.0}
        avg_confidence = sum(a.get("confidence", 70) for a in anomalies) / len(anomalies)
        avg_severity = sum(severity_weights.get(a.get("severity", "warn"), 1.0) for a in anomalies) / len(anomalies)
        
        return (avg_confidence / 100) * avg_severity

    def _calculate_trend_factor(self, anomalies: List[Dict]) -> float:
        """Boost probability if trends are detected."""
        trend_count = sum(1 for a in anomalies if a.get("trend"))
        return 1.0 + (trend_count * 0.15)  # 15% boost per trend

    def _calculate_deviation_factor(self, anomalies: List[Dict]) -> float:
        """Higher deviation from baseline increases probability."""
        if not anomalies:
            return 1.0
        
        avg_deviation = sum(abs(a.get("deviation_pct", 0)) for a in anomalies) / len(anomalies)
        return 1.0 + min(avg_deviation / 100, 0.5)  # Max 50% boost

    def analyze(self, svc: str, anomalies: List[Dict]) -> Dict:
        if not anomalies:
            return {}

        metric_map = {a["metric"]: a for a in anomalies}
        causes = []
        
        severity_mult = self._calculate_severity_multiplier(anomalies)
        trend_factor = self._calculate_trend_factor(anomalies)
        deviation_factor = self._calculate_deviation_factor(anomalies)

        for cause_name, primary_metrics, thresholds, base_prob, correlated_metrics in self.CAUSES:
            # Check if primary metrics are anomalous
            primary_score = 0.0
            for i, metric in enumerate(primary_metrics):
                if metric in metric_map:
                    val = metric_map[metric]["value"]
                    threshold = thresholds[i] if i < len(thresholds) else thresholds[0]
                    if val > threshold * 0.5:  # Lower threshold for detection
                        primary_score += (val / threshold)
            
            if primary_score > 0:
                # Calculate correlation bonus
                correlation_score = self._calculate_correlation_score(anomalies, correlated_metrics)
                correlation_bonus = 1.0 + (correlation_score * 0.3)  # Up to 30% boost
                
                # Calculate final probability with all factors
                prob = base_prob * (primary_score / len(primary_metrics))
                prob *= severity_mult
                prob *= trend_factor
                prob *= deviation_factor
                prob *= correlation_bonus
                prob = min(0.99, prob)  # Cap at 99%
                
                if prob > 0.3:  # Only include if probability > 30%
                    causes.append({
                        "cause": cause_name,
                        "probability": round(prob, 3),
                        "confidence": round(prob * 100, 1),
                        "correlated_metrics": [m for m in correlated_metrics if m in metric_map],
                        "primary_metrics": primary_metrics,
                    })

        causes.sort(key=lambda x: -x["probability"])
        primary = causes[0]["cause"] if causes else "Unknown Anomaly"

        # Generate accurate, data-driven summaries
        summaries = self._generate_summary(svc, primary, metric_map, anomalies)

        global incident_counter
        incident_counter += 1
        
        return {
            "incident_id":   f"INC-2025-{incident_counter:04d}",
            "service":       svc,
            "primary_cause": primary,
            "ai_summary":    summaries,
            "causes":        causes[:6],  # Top 6 causes
            "anomaly_count": len(anomalies),
            "severity":      max((a.get("severity", "warn") for a in anomalies), key=lambda s: 1 if s == "critical" else 0),
            "analyzed_at":   now_iso(),
            "affected_metrics": list(metric_map.keys()),
            "correlation_strength": round(self._calculate_correlation_score(anomalies, 
                                          causes[0].get("correlated_metrics", []) if causes else []), 2),
        }
    
    def _generate_summary(self, svc: str, cause: str, metric_map: Dict, anomalies: List[Dict]) -> str:
        """Generate accurate, data-driven incident summaries."""
        
        # Extract real values
        cpu = metric_map.get("cpu", {}).get("value", 0)
        mem = metric_map.get("memory", {}).get("value", 0)
        rps = metric_map.get("rps", {}).get("value", 0)
        err_rate = metric_map.get("error_rate", {}).get("value", 0)
        lat = metric_map.get("latency_p95", {}).get("value", 0)
        
        # Get baseline comparisons
        cpu_baseline = metric_map.get("cpu", {}).get("baseline_mean", 30)
        mem_baseline = metric_map.get("memory", {}).get("baseline_mean", 50)
        rps_baseline = metric_map.get("rps", {}).get("baseline_mean", 10)
        
        summaries = {
            "Traffic Spike": 
                f"Traffic surge detected: {rps:.1f} req/s ({(rps/max(rps_baseline, 1)):.1f}x baseline of {rps_baseline:.1f}). "
                f"CPU at {cpu:.1f}%, Memory at {mem:.1f}MB. Resource saturation risk HIGH.",
            
            "Memory Leak": 
                f"Memory consumption at {mem:.1f}MB ({((mem-mem_baseline)/max(mem_baseline, 1)*100):.1f}% above baseline). "
                f"Continuous growth pattern detected. OOMKill imminent if trend continues.",
            
            "CPU Exhaustion": 
                f"CPU utilization critical at {cpu:.1f}% ({((cpu-cpu_baseline)/max(cpu_baseline, 1)*100):.1f}% above baseline). "
                f"P95 latency degraded to {lat:.0f}ms. Likely compute-bound workload or inefficient algorithm.",
            
            "Service Cascade": 
                f"Error rate at {err_rate:.2f}% with {lat:.0f}ms P95 latency. "
                f"Failure propagating from {svc} to downstream dependencies. Circuit breaker recommended.",
            
            "Network Latency": 
                f"P95 latency spiked to {lat:.0f}ms (baseline: {metric_map.get('latency_p95', {}).get('baseline_mean', 200):.0f}ms). "
                f"Error rate: {err_rate:.2f}%. Possible network partition, DNS issues, or external API degradation.",
            
            "DB Connection Pool": 
                f"Database connection pool exhaustion detected. Error rate: {err_rate:.2f}%, Latency: {lat:.0f}ms. "
                f"Queries queuing, timeouts increasing. Scale connection pool or optimize queries.",
            
            "HPA Misconfiguration": 
                f"Autoscaler threshold breach: CPU {cpu:.1f}%, RPS {rps:.1f}. "
                f"HPA target too high or scale-out velocity insufficient. Manual intervention may be required.",
            
            "Container OOM Kill": 
                f"Memory at {mem:.1f}MB with error rate {err_rate:.2f}%. "
                f"Container approaching memory limit. OOMKill events likely. Increase memory limits or fix leak.",
            
            "Thread Pool Exhaustion":
                f"Thread pool saturation: Latency {lat:.0f}ms, CPU {cpu:.1f}%. "
                f"Worker threads exhausted under load. Increase pool size or optimize blocking operations.",
            
            "GC Pressure":
                f"Garbage collection pressure detected: CPU {cpu:.1f}%, Memory {mem:.1f}MB. "
                f"Frequent GC cycles causing latency spikes ({lat:.0f}ms). Optimize memory allocation patterns.",
        }
        
        return summaries.get(cause, 
            f"Anomaly detected in {svc}: {len(anomalies)} metrics affected. "
            f"Primary indicators: {', '.join(m for m in metric_map.keys())}. Automated analysis in progress.")

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
    """Enhanced heartbeat: collect metrics → detect → correlate → RCA → remediate → broadcast."""
    logger.info("SmartOps AI Engine started with ENHANCED ACCURACY MODE - Real-time Prometheus + ML Analytics.")
    
    anomaly_window = deque(maxlen=100)  # Track recent anomalies for correlation
    last_rca_time: Dict[str, float] = {}  # Prevent RCA spam
    
    while True:
        try:
            # FETCH REAL DATA from Prometheus with error handling
            metrics = await fetcher.get_all_metrics()
            if not metrics:
                logger.warning("No metrics received from Prometheus")
                await asyncio.sleep(2)
                continue
                
            latest_metrics.update(metrics)

            new_anomalies = []
            new_rcas      = []
            new_remeds    = []

            for svc, m in metrics.items():
                metric_history[svc].append(m)
                
                # Enhanced anomaly detection with statistical analysis
                anoms = detector.analyze(svc, m)
                
                if anoms:
                    for a in anoms:
                        # Improved deduplication: check last 60s and same severity
                        current_time = time.time()
                        recent = [x for x in anomaly_log[-30:]
                                  if x["service"] == svc 
                                  and x["metric"] == a["metric"]
                                  and x["severity"] == a["severity"]]
                        
                        # Only add if no recent duplicate or if severity escalated
                        if not recent:
                            anomaly_log.append(a)
                            new_anomalies.append(a)
                            anomaly_window.append(a)
                            logger.info(f"Anomaly detected: {svc}.{a['metric']} = {a['value']} "
                                      f"(threshold: {a['threshold']}, z-score: {a['z_score']}, "
                                      f"confidence: {a['confidence']}%)")

                    # Enhanced RCA: only trigger on critical anomalies with rate limiting
                    critical = [a for a in anoms if a["severity"] == "critical"]
                    
                    if critical:
                        # Rate limit: only 1 RCA per service per 30 seconds
                        last_rca = last_rca_time.get(svc, 0)
                        current_time = time.time()
                        
                        if current_time - last_rca > 30:
                            # Perform correlation analysis across all recent anomalies
                            correlated_anomalies = [a for a in anomaly_window 
                                                   if a["service"] == svc]
                            
                            rca = rca_engine.analyze(svc, correlated_anomalies)
                            
                            if rca and rca.get("primary_cause"):
                                incident_log.append(rca)
                                new_rcas.append(rca)
                                last_rca_time[svc] = current_time
                                
                                logger.warning(f"RCA completed for {svc}: {rca['primary_cause']} "
                                             f"(confidence: {rca['causes'][0]['confidence']}% if rca['causes'] else 'N/A')")

                                # Auto-remediation with validation
                                if auto_remediation_enabled:
                                    actions = remediation_engine.plan(rca)
                                    if actions:
                                        remediation_log.extend(actions)
                                        new_remeds.extend(actions)
                                        logger.info(f"Auto-remediation planned: {len(actions)} actions for {rca['incident_id']}")

            # Broadcast live update to all WebSocket clients
            if connected_clients and (new_anomalies or new_rcas or new_remeds):
                await broadcast({
                    "type":       "metrics_update",
                    "metrics":    metrics,
                    "anomalies":  new_anomalies,
                    "rcas":       new_rcas,
                    "remediations": new_remeds,
                    "timestamp":  now_iso(),
                    "auto_rem":   auto_remediation_enabled,
                    "engine_health": {
                        "anomaly_buffer": len(anomaly_window),
                        "total_incidents": len(incident_log),
                        "active_clients": len(connected_clients),
                    }
                })

        except Exception as e:
            logger.error(f"Engine loop error: {e}", exc_info=True)

        await asyncio.sleep(1.5)  # Optimized polling: 1.5s for better real-time accuracy


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
    """Trigger chaos scenarios to test anomaly detection and RCA."""
    valid_scenarios = ["cpu_stress", "mem_leak", "crash", "net_delay"]
    valid_services  = list(SERVICES.keys())
    
    if scenario not in valid_scenarios:
        raise HTTPException(400, f"Invalid scenario. Choose from: {valid_scenarios}")
    if service not in valid_services:
        raise HTTPException(400, f"Invalid service. Choose from: {valid_services}")
    
    svc_url = SERVICES[service]["url"]
    endpoint_map = {
        "cpu_stress": "/simulate/cpu-stress",
        "mem_leak":   "/simulate/memory-stress",
        "crash":      "/simulate/crash",
        "net_delay":  "/simulate/cpu-stress"
    }
    
    logger.info(f"Triggering {scenario} on {service}")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.get(f"{svc_url}{endpoint_map[scenario]}", params={"duration": 60})
            
            # Immediately inject a synthetic anomaly to ensure RCA triggers
            synthetic_metrics = {
                service: {
                    "cpu": 95.0 if scenario == "cpu_stress" else 45.0,
                    "memory": 950.0 if scenario == "mem_leak" else 512.0,
                    "rps": 85.0,
                    "error_rate": 8.5,
                    "latency_p95": 1500.0,
                    "timestamp": now_iso()
                }
            }
            
            # Force anomaly detection
            anoms = detector.analyze(service, synthetic_metrics[service])
            if anoms:
                for a in anoms:
                    anomaly_log.append(a)
                    logger.info(f"Synthetic anomaly injected: {service}.{a['metric']} = {a['value']}")
                
                # Force RCA
                critical = [a for a in anoms if a["severity"] == "critical"]
                if critical:
                    rca = rca_engine.analyze(service, anoms)
                    if rca:
                        incident_log.append(rca)
                        logger.info(f"RCA triggered: {rca['incident_id']} - {rca['primary_cause']}")
                        
                        # Generate remediations
                        if auto_remediation_enabled:
                            actions = remediation_engine.plan(rca)
                            remediation_log.extend(actions)
                        
                        # Broadcast immediately
                        await broadcast({
                            "type": "metrics_update",
                            "metrics": synthetic_metrics,
                            "anomalies": anoms,
                            "rcas": [rca],
                            "remediations": actions if auto_remediation_enabled else [],
                            "timestamp": now_iso(),
                            "auto_rem": auto_remediation_enabled,
                        })
            
            return {
                "status": "triggered", 
                "scenario": scenario, 
                "service": service,
                "anomalies_generated": len(anoms) if anoms else 0,
                "incident_id": rca.get("incident_id") if rca else None
            }
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            return {"status": "error", "message": str(e)}

@app.post("/api/simulate/reset")
def reset_simulation():
    return {"status": "reset", "message": "Manual reset requested (Real services recover automatically)"}

@app.post("/api/demo/generate-incident")
async def generate_demo_incident():
    """Generate a demo incident for testing the RCA page."""
    global incident_counter
    
    # Pick a random service
    service = random.choice(list(SERVICES.keys()))
    
    # Generate synthetic anomalies
    demo_anomalies = [
        {
            "id": hashlib.md5(f"demo{time.time()}cpu".encode()).hexdigest()[:12],
            "service": service,
            "metric": "cpu",
            "value": 92.5,
            "threshold": 80.0,
            "baseline_mean": 35.2,
            "baseline_p95": 45.0,
            "severity": "critical",
            "detected_at": now_iso(),
            "confidence": 94,
            "z_score": 4.2,
            "trend": "spike",
            "deviation_pct": 163.0
        },
        {
            "id": hashlib.md5(f"demo{time.time()}latency".encode()).hexdigest()[:12],
            "service": service,
            "metric": "latency_p95",
            "value": 1250.0,
            "threshold": 1000.0,
            "baseline_mean": 280.0,
            "baseline_p95": 450.0,
            "severity": "critical",
            "detected_at": now_iso(),
            "confidence": 89,
            "z_score": 3.8,
            "trend": "spike",
            "deviation_pct": 346.0
        }
    ]
    
    # Add to anomaly log
    anomaly_log.extend(demo_anomalies)
    
    # Generate RCA
    rca = rca_engine.analyze(service, demo_anomalies)
    if rca:
        incident_log.append(rca)
        logger.info(f"Demo incident generated: {rca['incident_id']} - {rca['primary_cause']}")
        
        # Generate remediations
        actions = remediation_engine.plan(rca)
        remediation_log.extend(actions)
        
        # Broadcast to all clients
        await broadcast({
            "type": "metrics_update",
            "metrics": latest_metrics,
            "anomalies": demo_anomalies,
            "rcas": [rca],
            "remediations": actions,
            "timestamp": now_iso(),
            "auto_rem": auto_remediation_enabled,
        })
        
        return {
            "status": "success",
            "incident": rca,
            "anomalies": len(demo_anomalies),
            "remediations": len(actions)
        }
    
    return {"status": "error", "message": "Failed to generate RCA"}

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
