"""
Base model with common fields for all models
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from app.database import Base as SQLAlchemyBase


class Base(SQLAlchemyBase):
    """
    Abstract base class with common fields
    All models should inherit from this
    """

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """Auto-generate table name from class name"""
        return cls.__name__.lower() + "s"

    def dict(self) -> dict:
        """Convert model to dictionary"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Alias for backward compatibility
BaseModel = Base
