import re
from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value or any(ord(c) < 32 for c in value):
        raise ValueError(f"Invalid {field_name}")
    return value


class SupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str | None = Field(None, max_length=254)
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return validate_text(value, "name")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if value is None or value == "":
            return None
        value = value.strip()
        if len(value) > 254 or not _EMAIL_REGEX.fullmatch(value):
            raise ValueError("Invalid email")
        return value

    @field_validator("phone", "address")
    @classmethod
    def validate_optional_text(cls, value):
        if value is None:
            return None
        return validate_text(value, "field")


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, max_length=254)
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=200)

    @field_validator("name", "phone", "address")
    @classmethod
    def validate_optional_text(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return validate_text(value, "field")

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if value is None:
            raise ValueError("Email cannot be null")
        if value == "":
            return None
        value = value.strip()
        if len(value) > 254 or not _EMAIL_REGEX.fullmatch(value):
            raise ValueError("Invalid email")
        return value


class SupplierResponse(SupplierBase):
    id: int
    model_config = ConfigDict(from_attributes=True)