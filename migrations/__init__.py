"""Migrações aditivas executadas durante a inicialização da API."""

from .startup import initialize_database

__all__ = ["initialize_database"]
