import os
import time
import random
import logging
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pythonjsonlogger import jsonlogger

# Logging configuration
logger = logging.getLogger("order_service")
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/orders_db")
engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=100)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    amount = Column(Float)
    status = Column(String, default="pending")
    paid = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Order Service")

# Prometheus Metrics
REQUEST_COUNT = Counter('order_service_requests_total', 'Total Order Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('order_service_request_latency_seconds', 'Order Request Latency', ['endpoint'])
ERROR_COUNT = Counter('order_service_errors_total', 'Total Order Errors', ['type'])

# External Services configuration
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment_service:8000")

class OrderCreate(BaseModel):
    user_id: int
    amount: float

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", f"req-{random.randint(2000, 9999)}")
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
    return {"status": "healthy", "service": "order_service"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/create")
async def create_order(order_data: OrderCreate):
    db = SessionLocal()
    try:
        order = Order(user_id=order_data.user_id, amount=order_data.amount)
        db.add(order)
        db.commit()
        db.refresh(order)
        
        # Call Payment Service with Retries and Timeout
        request_id = f"ord-{order.id}-{random.randint(100, 999)}"
        logger.info(f"Creating payment for order {order.id}", extra={"request_id": request_id})
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            retries = 3
            payment_status = False
            for attempt in range(retries):
                try:
                    response = await client.post(
                        f"{PAYMENT_SERVICE_URL}/process",
                        json={"order_id": order.id, "amount": order.amount, "user_id": order.user_id},
                        headers={"X-Request-ID": request_id}
                    )
                    if response.status_code == 200:
                        payment_status = True
                        break
                    else:
                        logger.warning(f"Payment attempt {attempt+1} failed with status {response.status_code}", extra={"request_id": request_id})
                except Exception as e:
                    logger.error(f"Payment attempt {attempt+1} failed with error {str(e)}", extra={"request_id": request_id})
                time.sleep(random.uniform(0.1, 0.5))

        if payment_status:
            order.status = "completed"
            order.paid = True
            db.commit()
            return {"id": order.id, "status": "paid", "amount": order.amount}
        else:
            order.status = "failed"
            db.commit()
            raise HTTPException(status_code=500, detail="Payment processing failed after retries")
    finally:
        db.close()

@app.get("/simulate/cpu-stress")
def simulate_cpu_stress(duration: int = 10):
    start = time.time()
    while time.time() - start < duration:
        _ = 1 * 1
    return {"status": "cpu stressed"}
