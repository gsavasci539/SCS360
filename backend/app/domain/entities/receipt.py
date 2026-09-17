from datetime import datetime
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import String, Numeric, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# Receipt model is defined in app.infrastructure.models.models.py
# This file is kept for backwards compatibility but the model should be imported from models
from app.infrastructure.models.models import Receipt as _Receipt

# Re-export for backwards compatibility
Receipt = _Receipt
