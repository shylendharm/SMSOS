from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.orders import router as orders_router
from app.api.v1.reservations import router as reservations_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.customers import router as customers_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.webhooks import router as webhooks_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, tags=["Auth"])
api_router.include_router(orders_router, tags=["Orders"])
api_router.include_router(reservations_router, tags=["Reservations"])
api_router.include_router(inventory_router, tags=["Inventory"])
api_router.include_router(catalog_router, tags=["Catalog"])
api_router.include_router(customers_router, tags=["Customers"])
api_router.include_router(analytics_router, tags=["Analytics"])
api_router.include_router(conversations_router, tags=["Conversations"])
api_router.include_router(webhooks_router, tags=["Webhooks"])