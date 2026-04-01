"""Пакет Bootstrapping для инициализации инфраструктуры сервиса."""

from .container import BootstrapContainer, bootstrap, get_container

__all__ = ["BootstrapContainer", "bootstrap", "get_container"]
