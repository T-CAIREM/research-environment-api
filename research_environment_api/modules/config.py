from functools import cache

from flask import current_app


@cache
def app_config():
    """Single dependence between modules and web."""
    return current_app.config
