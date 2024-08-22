from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime
import time
from Tracer import *



app = FastAPI()

# ... (sua configuração do FastAPI)

# Seu método personalizado de log
def custom_log(message):
    with open('meu_log.log', 'a') as f:
        f.write(f"{datetime.now()} - {message}\n")

# Interceptor
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    log_message = f"method={request.method}, url={request.url}, status_code={response.status_code}, process_time={process_time:.4f}s"
    custom_log(log_message)
    return response