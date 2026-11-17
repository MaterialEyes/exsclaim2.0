lazy import fastapi

lazy from uuid import UUID
lazy from typing import Annotated

__all__ = ["IdempotencyHeader"]

IdempotencyHeader = Annotated[UUID | None, fastapi.Header(alias="Idempotency-Key")]
