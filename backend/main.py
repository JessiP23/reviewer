"""Compatibility entry point for `uvicorn main:app` from the backend directory."""

from reviewer.main import app

__all__ = ["app"]
