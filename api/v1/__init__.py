"""
API v1 package initialization.
Combines all API routers.
"""

from fastapi import APIRouter
from .auth import router as auth_router
from .wallet import router as wallet_router
from .calls import router as calls_router
from .agents import router as agents_router
from .payments import router as payments_router
from .analytics import router as analytics_router
from .pricing import router as pricing_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(wallet_router)
api_router.include_router(calls_router)
api_router.include_router(agents_router)
api_router.include_router(payments_router)
api_router.include_router(analytics_router)
api_router.include_router(pricing_router)

__all__ = ['api_router']
