"""路由聚合。"""
from __future__ import annotations

from fastapi import APIRouter

from src.routes import audit, auth, benchmarks, health, ingest, postings, quality, raw, rules, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(sources.router)
api_router.include_router(ingest.router)
api_router.include_router(raw.router)
api_router.include_router(postings.router)
api_router.include_router(rules.router)
api_router.include_router(benchmarks.router)
api_router.include_router(quality.router)
api_router.include_router(audit.router)
