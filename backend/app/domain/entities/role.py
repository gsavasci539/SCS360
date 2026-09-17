from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# Role model is defined in app.infrastructure.models.models.py
# This file is kept for backwards compatibility but the model should be imported from models
from app.infrastructure.models.models import Role as _Role

# Re-export for backwards compatibility
Role = _Role
