from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogBase(BaseModel):
    user_id: int = Field(..., gt=0)
    action: str = Field(..., min_length=1)
    entity: str = Field(..., min_length=1)
    entity_id: int = Field(..., gt=0)


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
