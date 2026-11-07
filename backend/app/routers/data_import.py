from app.core.dates import school_today
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import pandas as pd
import io

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/import", tags=["Import"])


async def parse_excel_file(file: UploadFile) -> list[dict]:
    """Parse Excel file and return data as list of dictionaries"""
    try:
        from app.core.config import get_settings
        limit = get_settings().max_upload_size_bytes
        contents = await file.read(limit + 1)
        if len(contents) > limit:
            raise HTTPException(status_code=413, detail="İçe aktarma dosyası boyut sınırını aşıyor")
        
        # Try to read as Excel
        try:
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl", dtype=str)
        except Exception:
            # Fallback to CSV if Excel fails
            df = pd.read_csv(io.BytesIO(contents), dtype=str)
        
        # Convert to list of dictionaries
        data = df.to_dict("records")
        if len(data) > 5000:
            raise HTTPException(status_code=413, detail="Bir dosyada en fazla 5000 satır içe aktarılabilir")
        
        # Clean up None values
        cleaned_data = []
        for row in data:
            cleaned_row = {}
            for key, value in row.items():
                if pd.notna(value):
                    cleaned_row[str(key)] = value
            if cleaned_row:
                cleaned_data.append(cleaned_row)
        
        return cleaned_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dosya okuma hatası: {str(e)}")


@router.post("/students")
async def import_students(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("student.write"))
):
    from app.application.services.import_service import import_rows
    data = await parse_excel_file(file)
    result = await import_rows(db, tenant, "students", data)
    return success_response(result, f"{result['imported']} kayıt içe aktarıldı")


@router.post("/parents")
async def import_parents(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("student.write"))
):
    from app.application.services.import_service import import_rows
    data = await parse_excel_file(file)
    result = await import_rows(db, tenant, "parents", data)
    return success_response(result, f"{result['imported']} kayıt içe aktarıldı")


@router.post("/classes")
async def import_classes(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("class.write"))
):
    from app.application.services.import_service import import_rows
    data = await parse_excel_file(file)
    result = await import_rows(db, tenant, "classes", data)
    return success_response(result, f"{result['imported']} kayıt içe aktarıldı")


@router.post("/organizations")
async def import_organizations(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("org.write"))
):
    from app.application.services.import_service import import_rows
    data = await parse_excel_file(file)
    result = await import_rows(db, tenant, "organizations", data)
    return success_response(result, f"{result['imported']} kayıt içe aktarıldı")


@router.post("/branches")
async def import_branches(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("branch.write"))
):
    from app.application.services.import_service import import_rows
    data = await parse_excel_file(file)
    result = await import_rows(db, tenant, "branches", data)
    return success_response(result, f"{result['imported']} kayıt içe aktarıldı")


@router.post("/library")
async def import_library(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("resource.write"))
):
    from app.application.services.import_service import import_rows
    data = await parse_excel_file(file)
    result = await import_rows(db, tenant, "library", data)
    return success_response(result, f"{result['imported']} kayıt içe aktarıldı")


@router.post("/canteen")
async def import_canteen(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("resource.write"))
):
    from app.application.services.import_service import import_rows
    data = await parse_excel_file(file)
    result = await import_rows(db, tenant, "canteen", data)
    return success_response(result, f"{result['imported']} kayıt içe aktarıldı")


@router.post("/rfid-cards")
async def import_rfid_cards(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Import RFID cards from Excel file"""
    from app.repositories.rfid_card_repository import RfidCardRepository
    
    def card_to_dict(card) -> dict:
        return {
            "id": card.id,
            "card_number": card.card_number,
            "card_type": card.card_type,
            "holder_id": card.holder_id,
            "holder_name": card.holder_name,
            "status": card.status,
            "issue_date": card.issue_date.isoformat() if card.issue_date else None,
            "expiry_date": card.expiry_date.isoformat() if card.expiry_date else None,
            "created_at": card.created_at.isoformat() if card.created_at else None,
            "updated_at": card.updated_at.isoformat() if card.updated_at else None,
        }
    
    data = await parse_excel_file(file)
    
    # Expected columns: card_number, holder_id, card_type
    imported = []
    errors = []
    
    repo = RfidCardRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("card_number") or not row.get("holder_id") or not row.get("card_type"):
                errors.append(f"Satır {idx}: Kart numarası, kart sahibi ID ve kart tipi zorunludur")
                continue
            
            card_number = row.get("card_number")
            
            # Check if card number already exists
            if await repo.card_number_exists(card_number, organization_id=org_id):
                errors.append(f"Satır {idx}: Kart numarası {card_number} zaten kullanımda")
                continue
            
            # Determine card type and holder name
            card_type_str = row.get("card_type", "").upper()
            if card_type_str not in ["STUDENT", "STAFF"]:
                errors.append(f"Satır {idx}: Kart tipi STUDENT veya STAFF olmalıdır")
                continue
            
            holder_name = "Öğrenci" if card_type_str == "STUDENT" else "Personel"
            
            # Create card in database
            card = await repo.create(
                card_number=card_number,
                card_type=card_type_str,
                holder_id=row.get("holder_id"),
                holder_name=holder_name,
                organization_id=org_id,
                branch_id=branch_id,
                issue_date=school_today(),
                status="ACTIVE"
            )
            
            imported.append(card_to_dict(card))
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    await db.commit()
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} RFID kartı içe aktarıldı")


@router.post("/card-numbers")
async def import_card_numbers(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("settings.write"))
):
    """Import card numbers from Excel file"""
    from app.repositories.card_number_repository import CardNumberRepository
    
    def card_number_to_dict(card) -> dict:
        return {
            "id": card.id,
            "card_number": card.card_number,
            "status": card.status,
            "notes": card.notes,
            "purchased_date": card.purchased_date.isoformat() if card.purchased_date else None,
            "supplier": card.supplier,
            "created_at": card.created_at.isoformat() if card.created_at else None,
            "updated_at": card.updated_at.isoformat() if card.updated_at else None,
        }
    
    data = await parse_excel_file(file)
    
    # Expected columns: card_number, notes (optional), purchased_date (optional), supplier (optional)
    imported = []
    errors = []
    
    repo = CardNumberRepository(db)
    
    # Get organization and branch IDs from tenant context
    org_id = str(tenant.organization_id) if tenant.organization_id else None
    branch_id = str(tenant.branch_ids[0]) if tenant.branch_ids else None
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("card_number"):
                errors.append(f"Satır {idx}: Kart numarası zorunludur")
                continue
            
            card_number = row.get("card_number")
            
            # Check if card number already exists
            if await repo.card_number_exists(card_number, organization_id=org_id):
                errors.append(f"Satır {idx}: Kart numarası {card_number} zaten kullanımda")
                continue
            
            # Parse purchased date if provided
            purchased_date = None
            if row.get("purchased_date"):
                try:
                    purchased_date = datetime.strptime(str(row.get("purchased_date")), "%Y-%m-%d").date()
                except:
                    errors.append(f"Satır {idx}: Satın alma tarihi formatı hatalı (YYYY-MM-DD olmalıdır)")
                    continue
            
            # Create card number in database
            card = await repo.create(
                card_number=card_number,
                organization_id=org_id,
                branch_id=branch_id,
                status="AVAILABLE",
                notes=row.get("notes"),
                purchased_date=purchased_date,
                supplier=row.get("supplier")
            )
            
            imported.append(card_number_to_dict(card))
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    await db.commit()
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} kart numarası içe aktarıldı")


@router.post("/debts")
async def import_debts(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("finance.write"))
):
    from app.application.services.import_service import import_rows
    data = await parse_excel_file(file)
    result = await import_rows(db, tenant, "debts", data)
    return success_response(result, f"{result['imported']} kayıt içe aktarıldı")
