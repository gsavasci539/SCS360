from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# StudentParent model is defined in app.infrastructure.models.models.py
# This file is kept for backwards compatibility but the model should be imported from models
from app.infrastructure.models.models import StudentParent
