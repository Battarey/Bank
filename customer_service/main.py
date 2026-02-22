from __future__ import annotations

from fastapi import FastAPI

from .create_account.router import (
	router as create_account_router,
	start_router as create_account_start_router,
)
from .delete_account.router import router as delete_account_router
from .update_user_data.router import router as update_user_data_router

app = FastAPI(title="Customer Service", version="0.1.0")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


app.include_router(create_account_start_router)
app.include_router(create_account_router)
app.include_router(delete_account_router)
app.include_router(update_user_data_router)
