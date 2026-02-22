from __future__ import annotations

from fastapi import FastAPI

# TODO: Добавить роутеры для open_account и close_account когда будут реализованы
# from .open_account.router import router as open_account_router
# from .close_account.router import router as close_account_router

app = FastAPI(title="Account Service", version="0.1.0")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
	return {"status": "ok"}


# app.include_router(open_account_router)
# app.include_router(close_account_router)
