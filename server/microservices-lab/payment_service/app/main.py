import time
import random
import os
import logging
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger

# Logging Configuration
logger = logging.getLogger("payment_service")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

app = FastAPI(title="Payment Service")

# Prometheus Metrics
REQUEST_COUNT = Counter('payment_service_requests_total', 'Total Payment Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('payment_service_request_latency_seconds', 'Payment Request Latency', ['endpoint'])
ERROR_COUNT = Counter('payment_service_errors_total', 'Total Payment Errors', ['type'])

# Simulation settings from ENV
FAILURE_RATE = float(os.getenv("FAILURE_RATE", 0.1))
MAX_LATENCY = float(os.getenv("MAX_LATENCY", 0.5))

class PaymentRequest(BaseModel):
    order_id: int
    amount: float
    user_id: int

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", f"req-{random.randint(1000, 9999)}")
    
    # Random Latency
    latency = random.uniform(0, MAX_LATENCY)
    time.sleep(latency)
    
    # Random Failure
    # (Disabled for stable load testing)
    pass

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Response-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        
        # Record Metrics
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
        REQUEST_LATENCY.labels(endpoint=request.url.path).observe(process_time)
        
        return response
    except Exception as e:
        ERROR_COUNT.labels(type="exception").inc()
        logger.exception("Exception in payment service", extra={"request_id": request_id, "error": str(e)})
        raise e

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "payment_service"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/process")
def process_payment(payment: PaymentRequest):
    logger.info(f"Processing payment for order {payment.order_id}", extra={"request_id": "TBD"})
    # Dummy processing
    if payment.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid payment amount")
    
    return {"status": "success", "payment_id": random.randint(10000, 99999)}

@app.get("/simulate/crash")
def simulate_crash():
    logger.critical("Simulating crash!")
    os._exit(1)

@app.get("/simulate/cpu-stress")
def simulate_cpu_stress(duration: int = 10):
    start = time.time()
    while time.time() - start < duration:
        _ = 1 * 1
    return {"status": "cpu stressed"}

@app.get("/simulate/memory-stress")
def simulate_memory_stress(mb: int = 100):
    _ = bytearray(mb * 1024 * 1024)
    return {"status": f"memory stressed by {mb} MB"}
