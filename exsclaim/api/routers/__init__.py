from .general import router as general_router
from .query import router as query_router
from .users import router as users_router
from .v1 import router as v1_router
from .v2 import router as v2_router

__all__ = ["general_router", "query_router", "users_router", "v1_router", "v2_router"]
