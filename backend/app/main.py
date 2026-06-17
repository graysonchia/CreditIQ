from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import analytics, customers, predictions


app = FastAPI(title="CreditIQ API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(customers.router)
app.include_router(predictions.router)
app.include_router(analytics.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "CreditIQ API is running"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
