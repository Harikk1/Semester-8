import os
import time
import random
import logging
import httpx
import redis
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from pythonjsonlogger import jsonlogger

# Logging configuration
logger = logging.getLogger("user_service")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

app = FastAPI(title="User Service")

# Prometheus Metrics
REQUEST_COUNT = Counter('user_service_requests_total', 'Total User Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('user_service_request_latency_seconds', 'User Request Latency', ['endpoint'])
ERROR_COUNT = Counter('user_service_errors_total', 'Total User Errors', ['type'])

# External Services
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order_service:8001")

class UserOrder(BaseModel):
    user_id: int
    amount: float

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", f"user-{random.randint(3000, 9999)}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Response-Time"] = str(process_time)
        response.headers["X-Request-ID"] = request_id
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
        REQUEST_LATENCY.labels(endpoint=request.url.path).observe(process_time)
        return response
    except Exception as e:
        ERROR_COUNT.labels(type="exception").inc()
        raise e

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "user_service"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/register_order")
async def register_order(user_order: UserOrder):
    request_id = f"usr-{user_order.user_id}-{random.randint(100, 999)}"
    logger.info(f"User {user_order.user_id} registering order for amount {user_order.amount}", extra={"request_id": request_id})
    
    # Check cache for any session/metadata (dummy cache check)
    user_cache = cache.get(f"user_session_{user_order.user_id}")
    if not user_cache:
        cache.setex(f"user_session_{user_order.user_id}", 3600, "active")
        logger.info(f"Created new session cache for user {user_order.user_id}", extra={"request_id": request_id})
    
    # Forward to Order Service
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                f"{ORDER_SERVICE_URL}/create",
                json={"user_id": user_order.user_id, "amount": user_order.amount},
                headers={"X-Request-ID": request_id}
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Order created successfully for user {user_order.user_id}", extra={"request_id": request_id})
                return result
            else:
                logger.error(f"Order creation failed: {response.text}", extra={"request_id": request_id})
                raise HTTPException(status_code=500, detail="Order creation failed")
        except Exception as e:
            logger.exception("Exception calling Order Service", extra={"request_id": request_id, "error": str(e)})
            raise HTTPException(status_code=500, detail="Error communicating with order service")

@app.get("/simulate/memory-stress")
def simulate_memory_stress(mb: int = 100):
    _ = bytearray(mb * 1024 * 1024)
    return {"status": f"memory stressed by {mb} MB"}
