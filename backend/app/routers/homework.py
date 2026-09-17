from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import PermissionChecker
from app.core.responses import success_response, paginate
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/homework", tags=["Homework"])


class HomeworkCreate(BaseModel):
    title: str
    subject: Optional[str] = None
    class_id: Optional[str] = None
    due_date: Optional[datetime] = None
    description: Optional[str] = None


class HomeworkUpdate(BaseModel):
    title: Optional[str] = None
    subject: Optional[str] = None
    class_id: Optional[str] = None
    due_date: Optional[datetime] = None
    description: Optional[str] = None
    status: Optional[str] = None


# In-memory storage for homework (temporary solution)
homework_storage = [
    {
        "id": "hw-001",
        "title": "Matematik Ödevi",
        "subject": "Matematik",
        "class_id": "class-1",
        "class_name": "5-A Sınıfı",
        "due_date": "2024-09-15",
        "description": "Sayfa 45-48 arası problemleri çözün",
        "status": "ACTIVE",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "id": "hw-002",
        "title": "Türçe Kompozisyon",
        "subject": "Türkçe",
        "class_id": "class-1",
        "class_name": "5-A Sınıfı",
        "due_date": "2024-09-18",
        "description": "Okul tatili hakkında 200 kelimelik kompozisyon yazın",
        "status": "ACTIVE",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    },
    {
        "id": "hw-003",
        "title": "Fen Bilimleri Projesi",
        "subject": "Fen Bilimleri",
        "class_id": "class-2",
        "class_name": "5-B Sınıfı",
        "due_date": "2024-09-20",
        "description": "Basit bir elektrik devresi yapın ve rapor hazırlayın",
        "status": "ACTIVE",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
]


def homework_to_dict(homework: dict) -> dict:
    return {
        "id": homework.get("id"),
        "title": homework.get("title"),
        "subject": homework.get("subject"),
        "class_id": homework.get("class_id"),
        "class_name": homework.get("class_name"),
        "due_date": homework.get("due_date"),
        "description": homework.get("description"),
        "status": homework.get("status", "ACTIVE"),
        "created_at": homework.get("created_at"),
        "updated_at": homework.get("updated_at")
    }


@router.get("/")
async def list_homework(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("homework.read"))
):
    """List homework with pagination"""
    filtered_homework = homework_storage
    
    if search:
        search_lower = search.lower()
        filtered_homework = [
            h for h in homework_storage
            if search_lower in h.get("title", "").lower()
            or search_lower in h.get("subject", "").lower()
            or search_lower in h.get("description", "").lower()
        ]
    
    total = len(filtered_homework)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_homework = filtered_homework[start:end]
    
    return paginate(
        [homework_to_dict(h) for h in paginated_homework],
        total,
        page,
        page_size
    )


@router.get("/{homework_id}")
async def get_homework(
    homework_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("homework.read"))
):
    """Get a specific homework"""
    homework = next((h for h in homework_storage if str(h.get("id")) == homework_id), None)
    if not homework:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Homework not found")
    
    return success_response(homework_to_dict(homework))


@router.post("/")
async def create_homework(
    homework: HomeworkCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("homework.write"))
):
    """Create a new homework"""
    new_homework = {
        "id": UUID(str(UUID.uuid4())),
        "title": homework.title,
        "subject": homework.subject,
        "class_id": homework.class_id,
        "class_name": "Sınıf",  # Placeholder - would normally fetch from database
        "due_date": homework.due_date,
        "description": homework.description,
        "status": "ACTIVE",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    homework_storage.append(new_homework)
    return success_response(homework_to_dict(new_homework))


@router.put("/{homework_id}")
async def update_homework(
    homework_id: str,
    homework_update: HomeworkUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("homework.write"))
):
    """Update a homework"""
    homework = next((h for h in homework_storage if str(h.get("id")) == homework_id), None)
    if not homework:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Homework not found")
    
    if homework_update.title is not None:
        homework["title"] = homework_update.title
    if homework_update.subject is not None:
        homework["subject"] = homework_update.subject
    if homework_update.class_id is not None:
        homework["class_id"] = homework_update.class_id
    if homework_update.due_date is not None:
        homework["due_date"] = homework_update.due_date
    if homework_update.description is not None:
        homework["description"] = homework_update.description
    if homework_update.status is not None:
        homework["status"] = homework_update.status
    
    homework["updated_at"] = datetime.now()
    
    return success_response(homework_to_dict(homework))


@router.delete("/{homework_id}")
async def delete_homework(
    homework_id: str,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("homework.write"))
):
    """Delete a homework"""
    global homework_storage
    homework = next((h for h in homework_storage if str(h.get("id")) == homework_id), None)
    if not homework:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Homework not found")
    
    homework_storage = [h for h in homework_storage if str(h.get("id")) != homework_id]
    return success_response({"message": "Homework deleted successfully"})
