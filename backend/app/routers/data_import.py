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
        contents = await file.read()
        
        # Try to read as Excel
        try:
            df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
        except:
            # Fallback to CSV if Excel fails
            df = pd.read_csv(io.BytesIO(contents))
        
        # Convert to list of dictionaries
        data = df.to_dict("records")
        
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dosya okuma hatası: {str(e)}")


@router.post("/students")
async def import_students(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("student.write"))
):
    """Import students from Excel file"""
    data = await parse_excel_file(file)
    
    # Expected columns: first_name, last_name, student_number, date_of_birth, gender, address, phone, email
    imported = []
    errors = []
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("first_name") or not row.get("last_name"):
                errors.append(f"Satır {idx}: Ad ve soyad zorunludur")
                continue
            
            # Create student record (in-memory for now)
            student = {
                "first_name": row.get("first_name"),
                "last_name": row.get("last_name"),
                "student_number": row.get("student_number"),
                "date_of_birth": row.get("date_of_birth"),
                "gender": row.get("gender"),
                "address": row.get("address"),
                "phone": row.get("phone"),
                "email": row.get("email"),
                "status": "ACTIVE"
            }
            imported.append(student)
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} öğrenci içe aktarıldı")


@router.post("/parents")
async def import_parents(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("student.write"))
):
    """Import parents from Excel file"""
    data = await parse_excel_file(file)
    
    # Expected columns: first_name, last_name, relationship, phone, email, address
    imported = []
    errors = []
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("first_name") or not row.get("last_name") or not row.get("relationship") or not row.get("phone"):
                errors.append(f"Satır {idx}: Ad, soyad, yakınlık ve telefon zorunludur")
                continue
            
            # Create parent record (in-memory for now)
            parent = {
                "first_name": row.get("first_name"),
                "last_name": row.get("last_name"),
                "relationship": row.get("relationship"),
                "phone": row.get("phone"),
                "email": row.get("email"),
                "address": row.get("address"),
                "status": "ACTIVE"
            }
            imported.append(parent)
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} veli içe aktarıldı")


@router.post("/classes")
async def import_classes(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("class.write"))
):
    """Import classes from Excel file"""
    data = await parse_excel_file(file)
    
    # Expected columns: name, code, capacity, academic_year
    imported = []
    errors = []
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("name") or not row.get("code") or not row.get("capacity"):
                errors.append(f"Satır {idx}: Sınıf adı, kod ve kapasite zorunludur")
                continue
            
            # Create class record (in-memory for now)
            class_record = {
                "name": row.get("name"),
                "code": row.get("code"),
                "capacity": int(row.get("capacity", 0)),
                "academic_year": row.get("academic_year"),
                "status": "ACTIVE"
            }
            imported.append(class_record)
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} sınıf içe aktarıldı")


@router.post("/organizations")
async def import_organizations(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("org.write"))
):
    """Import organizations from Excel file"""
    data = await parse_excel_file(file)
    
    # Expected columns: name, legal_name, tax_number, phone, email, city, address
    imported = []
    errors = []
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("name"):
                errors.append(f"Satır {idx}: Kurum adı zorunludur")
                continue
            
            # Create organization record (in-memory for now)
            org = {
                "name": row.get("name"),
                "legal_name": row.get("legal_name"),
                "tax_number": row.get("tax_number"),
                "phone": row.get("phone"),
                "email": row.get("email"),
                "city": row.get("city"),
                "address": row.get("address"),
                "is_active": True
            }
            imported.append(org)
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} kurum içe aktarıldı")


@router.post("/branches")
async def import_branches(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("branch.write"))
):
    """Import branches from Excel file"""
    data = await parse_excel_file(file)
    
    # Expected columns: name, code, capacity, phone, email, city, address
    imported = []
    errors = []
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("name") or not row.get("code") or not row.get("capacity"):
                errors.append(f"Satır {idx}: Şube adı, kod ve kapasite zorunludur")
                continue
            
            # Create branch record (in-memory for now)
            branch = {
                "name": row.get("name"),
                "code": row.get("code"),
                "capacity": int(row.get("capacity", 0)),
                "phone": row.get("phone"),
                "email": row.get("email"),
                "city": row.get("city"),
                "address": row.get("address"),
                "is_active": True
            }
            imported.append(branch)
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} şube içe aktarıldı")


@router.post("/library")
async def import_library(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("resource.write"))
):
    """Import library books from Excel file"""
    data = await parse_excel_file(file)
    
    # Expected columns: title, author, isbn, category, total_count
    imported = []
    errors = []
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("title") or not row.get("author"):
                errors.append(f"Satır {idx}: Kitap adı ve yazar zorunludur")
                continue
            
            # Create book record (in-memory for now)
            book = {
                "title": row.get("title"),
                "author": row.get("author"),
                "isbn": row.get("isbn"),
                "category": row.get("category"),
                "total_count": int(row.get("total_count", 1)),
                "available_count": int(row.get("total_count", 1)),
                "status": "ACTIVE"
            }
            imported.append(book)
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} kitap içe aktarıldı")


@router.post("/canteen")
async def import_canteen(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("resource.write"))
):
    """Import canteen products from Excel file"""
    data = await parse_excel_file(file)
    
    # Expected columns: name, category, price, calories, is_available
    imported = []
    errors = []
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("name") or not row.get("category") or not row.get("price"):
                errors.append(f"Satır {idx}: Ürün adı, kategori ve fiyat zorunludur")
                continue
            
            # Create product record (in-memory for now)
            product = {
                "name": row.get("name"),
                "category": row.get("category"),
                "price": float(row.get("price", 0)),
                "calories": int(row.get("calories", 0)),
                "is_available": row.get("is_available", True) if isinstance(row.get("is_available"), bool) else str(row.get("is_available", "true")).lower() == "true",
                "status": "ACTIVE"
            }
            imported.append(product)
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} kantin ürünü içe aktarıldı")


@router.post("/rfid-cards")
async def import_rfid_cards(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
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
                issue_date=datetime.now().date(),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: TenantContext = Depends(PermissionChecker("finance.write"))
):
    """Import debts from Excel file"""
    data = await parse_excel_file(file)
    
    # Expected columns: student_number, debt_type, amount, due_date, academic_year, description
    imported = []
    errors = []
    
    for idx, row in enumerate(data, start=1):
        try:
            # Validate required fields
            if not row.get("student_number") or not row.get("debt_type") or not row.get("amount") or not row.get("due_date"):
                errors.append(f"Satır {idx}: Öğrenci no, borç türü, tutar ve vade tarihi zorunludur")
                continue
            
            # Create debt record (in-memory for now)
            debt = {
                "student_number": row.get("student_number"),
                "debt_type": row.get("debt_type"),
                "amount": float(row.get("amount", 0)),
                "remaining_amount": float(row.get("amount", 0)),
                "due_date": row.get("due_date"),
                "academic_year": row.get("academic_year"),
                "description": row.get("description"),
                "status": "PENDING"
            }
            imported.append(debt)
        except Exception as e:
            errors.append(f"Satır {idx}: {str(e)}")
    
    return success_response({
        "imported": len(imported),
        "errors": errors,
        "data": imported
    }, f"{len(imported)} borç içe aktarıldı")
