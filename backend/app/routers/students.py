from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.application.schemas import StudentCreate, StudentUpdate, StudentResponse
from app.repositories import StudentRepository
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_tenant_context
from app.core.permissions import require_permission, PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/students", tags=["Students"])


@router.post("", response_model=StudentResponse)
@require_permission("students.create")
async def create_student(
    student: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo = StudentRepository()
    student_data = student.model_dump(exclude={"parent_ids"})
    student_data["created_by"] = current_user.id
    student_data["organization_id"] = current_user.organization_id
    
    db_student = await repo.create(db, student_data)
    await db.commit()
    
    # TODO: Handle parent relationships
    
    return success_response(db_student, "Öğrenci oluşturuldu")


@router.get("", response_model=list[StudentResponse])
async def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    branch_id: Optional[UUID] = None,
    class_id: Optional[UUID] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("students.read"))
):
    repo = StudentRepository()
    
    filters = {"organization_id": tenant.organization_id}
    if branch_id:
        filters["branch_id"] = branch_id
    if class_id:
        filters["class_id"] = class_id
    
    if search:
        students = await repo.search_students(
            db, tenant.organization_id, search, skip, limit
        )
    else:
        students = await repo.get_multi(db, skip, limit, filters)
    
    return success_response(students)


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("students.read"))
):
    repo = StudentRepository()
    student = await repo.get(db, student_id)
    
    if not student or student.organization_id != tenant.organization_id:
        return success_response(None, "Öğrenci bulunamadı", success=False)
    
    return success_response(student)


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: UUID,
    student: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("students.write"))
):
    repo = StudentRepository()
    db_student = await repo.get(db, student_id)
    
    if not db_student or db_student.organization_id != tenant.organization_id:
        return success_response(None, "Öğrenci bulunamadı", success=False)
    
    student_data = student.model_dump(exclude_unset=True, exclude={"parent_ids"})
    student_data["updated_by"] = tenant.user_id
    
    updated_student = await repo.update(db, db_student, student_data)
    
    # TODO: Handle parent relationships if provided
    
    return success_response(updated_student, "Öğrenci güncellendi")


@router.delete("/{student_id}")
async def delete_student(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("students.write"))
):
    repo = StudentRepository()
    db_student = await repo.get(db, student_id)
    
    if not db_student or db_student.organization_id != tenant.organization_id:
        return success_response(None, "Öğrenci bulunamadı", success=False)
    
    await repo.soft_delete(db, student_id)
    
    return success_response(message="Öğrenci silindi")


# ==================== Excel Import/Export Endpoints ====================

@router.post("/import-excel")
@require_permission("students.import")
async def import_students_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import students from Excel file"""
    import pandas as pd
    import io
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Sadece Excel dosyaları (.xlsx, .xls) yüklenebilir")
    
    try:
        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Validate required columns
        required_columns = ['student_number', 'first_name', 'last_name', 'class_id']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Eksik sütunlar: {', '.join(missing_columns)}"
            )
        
        # Process students
        from app.infrastructure.models.models import Student
        imported_students = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                new_student = Student(
                    student_number=str(row['student_number']),
                    first_name=str(row['first_name']),
                    last_name=str(row['last_name']),
                    class_id=UUID(str(row['class_id'])) if pd.notna(row['class_id']) else None,
                    organization_id=current_user.organization_id,
                    branch_id=UUID(str(row['branch_id'])) if 'branch_id' in row and pd.notna(row['branch_id']) else None,
                    birth_date=pd.to_datetime(row['birth_date']) if 'birth_date' in row and pd.notna(row['birth_date']) else None,
                    blood_group=str(row['blood_group']) if 'blood_group' in row and pd.notna(row['blood_group']) else None,
                    allergies=str(row['allergies']) if 'allergies' in row and pd.notna(row['allergies']) else None,
                    gender=str(row['gender']) if 'gender' in row and pd.notna(row['gender']) else None,
                    status="ACTIVE",
                    created_by=current_user.id
                )
                db.add(new_student)
                await db.flush()
                imported_students.append({
                    "row": index + 2,  # Excel row number (1-indexed + header)
                    "student_id": str(new_student.id),
                    "student_number": new_student.student_number,
                    "name": f"{new_student.first_name} {new_student.last_name}",
                    "status": "SUCCESS"
                })
            except Exception as e:
                errors.append({
                    "row": index + 2,
                    "student_number": str(row['student_number']) if 'student_number' in row else "N/A",
                    "error": str(e)
                })
        
        await db.commit()
        
        return success_response({
            "total_rows": len(df),
            "imported": len(imported_students),
            "failed": len(errors),
            "students": imported_students,
            "errors": errors
        }, f"{len(imported_students)} öğrenci başarıyla içe aktarıldı")
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Excel işleme hatası: {str(e)}")


@router.get("/export-excel")
@require_permission("students.export")
async def export_students_excel(
    branch_id: Optional[UUID] = None,
    class_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export students to Excel file"""
    import pandas as pd
    from fastapi.responses import StreamingResponse
    import io
    
    repo = StudentRepository()
    
    filters = {"organization_id": current_user.organization_id}
    if branch_id:
        filters["branch_id"] = branch_id
    if class_id:
        filters["class_id"] = class_id
    
    students = await repo.get_multi(db, 0, 10000, filters)
    
    # Prepare data for export
    export_data = []
    for student in students:
        export_data.append({
            "student_number": student.student_number,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "class_id": str(student.class_id) if student.class_id else "",
            "branch_id": str(student.branch_id) if student.branch_id else "",
            "birth_date": student.birth_date.isoformat() if student.birth_date else "",
            "blood_group": student.blood_group or "",
            "allergies": student.allergies or "",
            "gender": student.gender or "",
            "status": student.status,
            "created_at": student.created_at.isoformat() if student.created_at else ""
        })
    
    # Create DataFrame
    df = pd.DataFrame(export_data)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Öğrenciler')
    
    output.seek(0)
    
    # Generate filename
    filename = f"students_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
