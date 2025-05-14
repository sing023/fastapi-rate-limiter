from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from typing import Optional
import redis
import time

app = FastAPI()

def create_redis():
    return redis.Redis(host="redis", port=6379, db=0, socket_timeout=5, socket_connect_timeout=5)

r = create_redis()

user_plans = {
    "user_free": {"window_size": 60, "max_requests": 5},
    "user_pro": {"window_size": 60, "max_requests": 50},
    "user_enterprise": {"window_size": 60, "max_requests": 200}
}

def get_user_plan(user_id: str):
    return user_plans.get(user_id, {"window_size": 60, "max_requests": 5})

def is_allowed(user_id: str) -> bool:
    plan = get_user_plan(user_id)
    window_size_sec = plan["window_size"]
    max_requests = plan["max_requests"]
    
    key = f"rate_limit:{user_id}"
    now = int(time.time())
    pipeline = r.pipeline()

    try:
        pipeline.zremrangebyscore(key, 0, now - window_size_sec)
        pipeline.zcard(key)
        _, current_count = pipeline.execute()

        if current_count < max_requests:
            pipeline.zadd(key, {now: now})
            pipeline.expire(key, window_size_sec)
            pipeline.execute()
            return True
        else:
            return False
    except redis.RedisError as e:
        print(f"Redis error: {e}")
        return False

@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    user_id = request.query_params.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")

    start_time = time.time()
    allowed = is_allowed(user_id)
    latency = time.time() - start_time
    r.incr(f"metrics:fastapi_latency_total")
    r.incrbyfloat(f"metrics:fastapi_latency_sum", latency)

    if not allowed:
        r.incr("metrics:requests_blocked")
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    r.incr("metrics:requests_allowed")
    return await call_next(request)

@app.get("/metrics")
def metrics():
    allowed = int(r.get("metrics:requests_allowed") or 0)
    blocked = int(r.get("metrics:requests_blocked") or 0)
    total_latency = float(r.get("metrics:fastapi_latency_sum") or 0)
    total_requests = float(r.get("metrics:fastapi_latency_total") or 1)
    avg_latency = total_latency / total_requests

    response = f"""
# HELP requests_allowed Total allowed requests
# TYPE requests_allowed counter
requests_allowed {allowed}

# HELP requests_blocked Total blocked requests
# TYPE requests_blocked counter
requests_blocked {blocked}

# HELP fastapi_latency_avg_seconds Average FastAPI latency
# TYPE fastapi_latency_avg_seconds gauge
fastapi_latency_avg_seconds {avg_latency}
"""
    return PlainTextResponse(response.strip())

