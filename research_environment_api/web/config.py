import os


def build_config() -> dict:
    return {"CACHE_TYPE": os.environ["CACHE_TYPE"]}
