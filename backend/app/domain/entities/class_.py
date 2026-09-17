from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# Class model is defined in app.infrastructure.models.models.py
# This file is kept for backwards compatibility but the model should be imported from models
from app.infrastructure.models.models import ClassRoom as _Class

# Re-export for backwards compatibility
Class = _Class
