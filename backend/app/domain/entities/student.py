from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# Student model is defined in app.infrastructure.models.models.py
# This file is kept for backwards compatibility but the model should be imported from models
from app.infrastructure.models.models import Student as _Student

# Re-export for backwards compatibility
Student = _Student
