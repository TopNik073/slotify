from fastapi import APIRouter

from src.handlers.api.v1.admin import admin_router
from src.handlers.api.v1.auth import auth_router
from src.handlers.api.v1.bookings import bookings_router
from src.handlers.api.v1.equipment import equipment_router
from src.handlers.api.v1.health import health_router
from src.handlers.api.v1.offices import offices_router
from src.handlers.api.v1.rooms import rooms_router
from src.handlers.api.v1.users import users_router

v1_router = APIRouter(prefix='/v1')

v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(offices_router)
v1_router.include_router(rooms_router)
v1_router.include_router(equipment_router)
v1_router.include_router(bookings_router)
v1_router.include_router(admin_router)
