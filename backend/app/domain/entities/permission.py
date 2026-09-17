from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# Permission model is defined in app.infrastructure.models.models.py
# This file is kept for backwards compatibility but the model should be imported from models
from app.infrastructure.models.models import Permission as _Permission

# Re-export for backwards compatibility
Permission = _Permission
