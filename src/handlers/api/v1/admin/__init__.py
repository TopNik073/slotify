from fastapi import APIRouter
from fastapi import Depends

from src.handlers.api.v1.admin.bookings import admin_bookings_router
from src.handlers.api.v1.admin.equipment import admin_equipment_router
from src.handlers.api.v1.admin.offices import admin_offices_router
from src.handlers.api.v1.admin.rooms import admin_rooms_router
from src.handlers.api.v1.admin.users import admin_users_router
from src.handlers.dependencies.auth import get_current_admin

# The guard sits on the parent router, so a new admin endpoint is protected by default
# instead of relying on whoever adds it to remember the dependency.
admin_router = APIRouter(prefix='/admin', dependencies=[Depends(get_current_admin)])

admin_router.include_router(admin_offices_router)
admin_router.include_router(admin_rooms_router)
admin_router.include_router(admin_equipment_router)
admin_router.include_router(admin_users_router)
admin_router.include_router(admin_bookings_router)

__all__ = [
    'admin_router',
]
