import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=200)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not _EMAIL_REGEX.match(value):
            raise ValueError("Invalid email address")
        return value


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=200)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not _EMAIL_REGEX.match(value):
            raise ValueError("Invalid email address")
        return value


class SupplierResponse(SupplierBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
