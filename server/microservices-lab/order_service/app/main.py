import os
import time
import random
import logging
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pythonjsonlogger import jsonlogger
from datetime import datetime

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
    user_id = Column(Integer, index=True)
    amount = Column(Float)
    status = Column(String, default="pending", index=True)
    paid = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    request_id = f"ord-{order_data.user_id}-{random.randint(100, 999)}"
    
    try:
        # Create order with validation
        if order_data.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid order amount")
        
        if order_data.amount > 10000:
            raise HTTPException(status_code=400, detail="Order amount exceeds maximum limit")
        
        order = Order(user_id=order_data.user_id, amount=order_data.amount)
        db.add(order)
        db.commit()
        db.refresh(order)
        
        logger.info(f"Order {order.id} created for user {order_data.user_id}, amount ${order.amount}", 
                   extra={"request_id": request_id})
        
        # Enhanced Payment Service call with circuit breaker pattern
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
            retries = 3
            payment_status = False
            last_error = None
            
            for attempt in range(retries):
                try:
                    logger.info(f"Payment attempt {attempt+1}/{retries} for order {order.id}", 
                              extra={"request_id": request_id})
                    
                    response = await client.post(
                        f"{PAYMENT_SERVICE_URL}/process",
                        json={
                            "order_id": order.id, 
                            "amount": order.amount, 
                            "user_id": order.user_id
                        },
                        headers={"X-Request-ID": request_id}
                    )
                    
                    if response.status_code == 200:
                        payment_result = response.json()
                        payment_status = True
                        logger.info(f"Payment successful for order {order.id}: {payment_result.get('payment_id')}", 
                                  extra={"request_id": request_id})
                        break
                    elif response.status_code >= 500:
                        last_error = f"Payment service error: {response.status_code}"
                        logger.warning(f"Payment attempt {attempt+1} failed with status {response.status_code}", 
                                     extra={"request_id": request_id})
                    else:
                        # 4xx errors - don't retry
                        last_error = f"Payment rejected: {response.text}"
                        logger.error(f"Payment rejected for order {order.id}: {response.text}", 
                                   extra={"request_id": request_id})
                        break
                        
                except httpx.TimeoutException as e:
                    last_error = f"Payment service timeout: {str(e)}"
                    logger.error(f"Payment attempt {attempt+1} timed out", 
                               extra={"request_id": request_id, "error": str(e)})
                    
                except httpx.ConnectError as e:
                    last_error = f"Payment service unreachable: {str(e)}"
                    logger.error(f"Payment attempt {attempt+1} connection failed", 
                               extra={"request_id": request_id, "error": str(e)})
                    
                except Exception as e:
                    last_error = f"Payment error: {str(e)}"
                    logger.exception(f"Payment attempt {attempt+1} unexpected error", 
                                   extra={"request_id": request_id, "error": str(e)})
                
                # Exponential backoff
                if attempt < retries - 1:
                    backoff = random.uniform(0.1, 0.3) * (2 ** attempt)
                    await asyncio.sleep(backoff)

        # Update order status based on payment result
        if payment_status:
            order.status = "completed"
            order.paid = True
            db.commit()
            logger.info(f"Order {order.id} completed successfully", extra={"request_id": request_id})
            return {
                "id": order.id, 
                "status": "paid", 
                "amount": order.amount,
                "user_id": order.user_id,
                "created_at": order.created_at.isoformat()
            }
        else:
            order.status = "failed"
            db.commit()
            logger.error(f"Order {order.id} failed after {retries} payment attempts: {last_error}", 
                       extra={"request_id": request_id})
            raise HTTPException(
                status_code=500, 
                detail=f"Payment processing failed: {last_error}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Order creation failed", extra={"request_id": request_id, "error": str(e)})
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Order creation error: {str(e)}")
    finally:
        db.close()

@app.get("/simulate/cpu-stress")
def simulate_cpu_stress(duration: int = 10):
    start = time.time()
    while time.time() - start < duration:
        _ = 1 * 1
    return {"status": "cpu stressed"}
