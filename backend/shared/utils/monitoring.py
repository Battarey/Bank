from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

def instrument_app(app: FastAPI) -> None:
    """Инструментирует FastAPI приложение для сбора метрик Prometheus.
    
    Args:
        app: Экземпляр приложения FastAPI.
    """
    Instrumentator().instrument(app).expose(app)
