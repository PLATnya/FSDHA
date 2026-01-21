import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

def get_allowed_origins() -> List[str]:
    default_origins = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    additional_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if not additional_origins_env:
        return default_origins
    additional_origins = [
        origin.strip()
        for origin in additional_origins_env.split(",")
        if origin.strip()
    ]
    all_origins = default_origins + additional_origins
    seen = set()
    unique_origins = []
    for origin in all_origins:
        if origin not in seen:
            seen.add(origin)
            unique_origins.append(origin)
    return unique_origins
