from sqlalchemy import Column, DateTime, Integer, String

from app.database.database import Base


class AvailabilityEvent(Base):
    __tablename__ = "availability_events"

    id = Column(Integer, primary_key=True)
    checked_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(16), nullable=False)
