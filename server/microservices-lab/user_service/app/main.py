import os
import time
import random
import logging
import asyncio
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
    
    # Enhanced validation
    if user_order.user_id <= 0:
        logger.error(f"Invalid user_id: {user_order.user_id}", extra={"request_id": request_id})
        ERROR_COUNT.labels(type="validation_error").inc()
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    if user_order.amount <= 0:
        logger.error(f"Invalid amount: {user_order.amount}", extra={"request_id": request_id})
        ERROR_COUNT.labels(type="validation_error").inc()
        raise HTTPException(status_code=400, detail="Invalid order amount")
    
    logger.info(f"User {user_order.user_id} registering order for amount ${user_order.amount}", 
               extra={"request_id": request_id})
    
    # Enhanced cache management with TTL
    try:
        user_cache = cache.get(f"user_session_{user_order.user_id}")
        if not user_cache:
            cache.setex(f"user_session_{user_order.user_id}", 3600, "active")
            logger.info(f"Created new session cache for user {user_order.user_id}", 
                       extra={"request_id": request_id})
        else:
            # Refresh TTL on activity
            cache.expire(f"user_session_{user_order.user_id}", 3600)
    except Exception as e:
        logger.warning(f"Cache operation failed: {str(e)}", extra={"request_id": request_id})
        # Continue without cache - non-critical
    
    # Forward to Order Service with retry logic
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Forwarding to Order Service (attempt {attempt + 1}/{max_retries})", 
                           extra={"request_id": request_id})
                
                response = await client.post(
                    f"{ORDER_SERVICE_URL}/create",
                    json={"user_id": user_order.user_id, "amount": user_order.amount},
                    headers={"X-Request-ID": request_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Order created successfully: order_id={result.get('id')}", 
                               extra={"request_id": request_id})
                    return {
                        **result,
                        "request_id": request_id,
                        "user_id": user_order.user_id
                    }
                elif response.status_code >= 500:
                    last_error = f"Order service error: {response.status_code}"
                    logger.warning(f"Order service returned {response.status_code}", 
                                 extra={"request_id": request_id})
                else:
                    # 4xx errors - don't retry
                    logger.error(f"Order rejected: {response.text}", 
                               extra={"request_id": request_id})
                    raise HTTPException(status_code=response.status_code, 
                                      detail=f"Order creation failed: {response.text}")
                    
            except httpx.TimeoutException as e:
                last_error = f"Order service timeout: {str(e)}"
                logger.error(f"Timeout calling Order Service (attempt {attempt + 1})", 
                           extra={"request_id": request_id, "error": str(e)})
                ERROR_COUNT.labels(type="timeout").inc()
                
            except httpx.ConnectError as e:
                last_error = f"Order service unreachable: {str(e)}"
                logger.error(f"Connection failed to Order Service (attempt {attempt + 1})", 
                           extra={"request_id": request_id, "error": str(e)})
                ERROR_COUNT.labels(type="connection_error").inc()
                
            except HTTPException:
                raise
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.exception("Unexpected error calling Order Service", 
                               extra={"request_id": request_id, "error": str(e)})
                ERROR_COUNT.labels(type="exception").inc()
            
            # Exponential backoff between retries
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5 * (2 ** attempt))
        
        # All retries failed
        logger.error(f"Order creation failed after {max_retries} attempts: {last_error}", 
                   extra={"request_id": request_id})
        ERROR_COUNT.labels(type="order_service_failure").inc()
        raise HTTPException(status_code=500, 
                          detail=f"Error communicating with order service: {last_error}")

@app.get("/simulate/memory-stress")
def simulate_memory_stress(mb: int = 100):
    _ = bytearray(mb * 1024 * 1024)
    return {"status": f"memory stressed by {mb} MB"}
