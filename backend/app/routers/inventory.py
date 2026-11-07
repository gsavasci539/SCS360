"""
Demirbaş & Envanter Yönetimi Module API
Handles inventory items, locations, assignments, and maintenance requests
"""
from __future__ import annotations
from app.core.dates import school_today
from datetime import datetime, date
from typing import Optional, List, Literal
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.application.services import inventory_service
from app.core.responses import success_response
from app.core.permissions import PermissionChecker
from app.core.tenant import TenantContext
from app.domain.entities import User, Branch

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


# ==================== Schemas ====================

class InventoryItemCreate(BaseModel):
    branch_id: UUID
    item_code: str = Field(..., min_length=1, max_length=50)
    item_name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = Field(None, ge=0, max_digits=15, decimal_places=2)
    current_value: Optional[Decimal] = Field(None, ge=0, max_digits=15, decimal_places=2)
    location_id: Optional[UUID] = None
    condition: Optional[str] = Field(None, max_length=50)
    qr_code: Optional[str] = Field(None, max_length=255)
    barcode: Optional[str] = Field(None, max_length=255)
    warranty_expiry: Optional[date] = None

class InventoryLocationCreate(BaseModel):
    branch_id: UUID
    location_name: str = Field(..., min_length=1, max_length=255)
    location_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None

class AssetAssignmentCreate(BaseModel):
    item_id: UUID
    assigned_to: UUID
    return_date: Optional[date] = Field(None, description="Planlanan iade; iade işleminde gerçekleşen tarihle güncellenir")
    notes: Optional[str] = None

class MaintenanceRequestCreate(BaseModel):
    item_id: UUID
    issue_description: str = Field(..., description="Issue description")
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] = "MEDIUM"
    assigned_to: Optional[UUID] = None

    @field_validator("priority", mode="before")
    @classmethod
    def normalized_priority(cls, value):
        return value.upper() if isinstance(value, str) else value


# ==================== Inventory Items Endpoints ====================

@router.get("/options")
async def inventory_options(branch_id: Optional[UUID] = None, item_search: str = Query("", max_length=100),
    user_search: str = Query("", max_length=100), db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))):
    return success_response(await inventory_service.options(db, tenant, branch_id, item_search, user_search))

@router.get("/items")
async def get_inventory_items(
    branch_id: Optional[UUID] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.read"))
):
    """Get inventory items with filtering"""
    from app.domain.entities.inventory import InventoryItem
    
    query = select(InventoryItem)
    
    conditions = []
    if branch_id:
        conditions.append(InventoryItem.branch_id == branch_id)
    if category:
        conditions.append(InventoryItem.category == category)
    if status:
        conditions.append(InventoryItem.status == status.upper())
    if location_id:
        conditions.append(InventoryItem.location_id == location_id)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(InventoryItem.item_code, InventoryItem.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    enriched_items = []
    from app.domain.entities.inventory import InventoryLocation
    branches = await inventory_service.related_records(db, Branch, {row.branch_id for row in items})
    locations = await inventory_service.related_records(db, InventoryLocation, {row.location_id for row in items if row.location_id})
    for item in items:
        branch = branches.get(item.branch_id)
        location = locations.get(item.location_id)
        branch_name = branch.name if branch else None
        location_name = location.location_name if location else None
        enriched_items.append({
            "id": str(item.id),
            "branch_id": str(item.branch_id),
            "branch_name": branch_name,
            "item_code": item.item_code,
            "item_name": item.item_name,
            "category": item.category,
            "description": item.description,
            "purchase_date": item.purchase_date.isoformat() if item.purchase_date else None,
            "purchase_price": float(item.purchase_price) if item.purchase_price else None,
            "current_value": float(item.current_value) if item.current_value else None,
            "location_id": str(item.location_id) if item.location_id else None,
            "location_name": location_name,
            "status": item.status,
            "condition": item.condition,
            "qr_code": item.qr_code,
            "barcode": item.barcode,
            "warranty_expiry": item.warranty_expiry.isoformat() if item.warranty_expiry else None,
            "created_at": item.created_at.isoformat()
        })
    
    return success_response(enriched_items)


@router.post("/items")
async def create_inventory_item(
    item: InventoryItemCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    return success_response(await inventory_service.save_item(db, tenant, item))


@router.put("/items/{item_id}")
async def update_inventory_item(
    item_id: UUID,
    item: InventoryItemCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    return success_response(await inventory_service.save_item(db, tenant, item, item_id))


# ==================== Inventory Locations Endpoints ====================

@router.get("/locations")
async def get_inventory_locations(
    branch_id: Optional[UUID] = Query(None),
    location_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.read"))
):
    """Get inventory locations"""
    from app.domain.entities.inventory import InventoryLocation
    
    query = select(InventoryLocation)
    
    conditions = []
    if branch_id:
        conditions.append(InventoryLocation.branch_id == branch_id)
    if location_type:
        conditions.append(InventoryLocation.location_type == location_type)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(InventoryLocation.location_name)
    
    result = await db.execute(query)
    locations = result.scalars().all()
    
    enriched_locations = []
    for location in locations:
        # Get branch name
        branch_name = None
        if location.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == location.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        enriched_locations.append({
            "id": str(location.id),
            "branch_id": str(location.branch_id),
            "branch_name": branch_name,
            "location_name": location.location_name,
            "location_type": location.location_type,
            "description": location.description,
            "created_at": location.created_at.isoformat()
        })
    
    return success_response(enriched_locations)


@router.post("/locations")
async def create_inventory_location(
    location: InventoryLocationCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    """Create a new inventory location"""
    from app.domain.entities.inventory import InventoryLocation
    
    new_location = InventoryLocation(
        branch_id=location.branch_id,
        location_name=location.location_name,
        location_type=location.location_type,
        description=location.description
    )
    db.add(new_location)
    await db.commit()
    await db.refresh(new_location)
    
    return success_response({
        "id": str(new_location.id),
        "location_name": new_location.location_name,
        "created_at": new_location.created_at.isoformat()
    })


# ==================== Asset Assignments Endpoints ====================

@router.get("/assignments")
async def get_asset_assignments(
    item_id: Optional[UUID] = Query(None),
    assigned_to: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.read"))
):
    """Get asset assignments with filtering"""
    from app.domain.entities.inventory import AssetAssignment, InventoryItem
    
    query = select(AssetAssignment)
    
    conditions = []
    if item_id:
        conditions.append(AssetAssignment.item_id == item_id)
    if assigned_to:
        conditions.append(AssetAssignment.assigned_to == assigned_to)
    if status:
        conditions.append(AssetAssignment.status == status.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(AssetAssignment.assigned_date.desc(), AssetAssignment.created_at.desc(), AssetAssignment.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    enriched_assignments = []
    from app.domain.entities.inventory import InventoryItem
    item_names = await inventory_service.related_records(db, InventoryItem, {row.item_id for row in assignments})
    user_names = await inventory_service.related_records(db, User, {row.assigned_to for row in assignments if row.assigned_to})
    for assignment in assignments:
        item = item_names.get(assignment.item_id)
        user = user_names.get(assignment.assigned_to)
        item_name = item.item_name if item else None
        item_code = item.item_code if item else None
        assigned_to_name = f"{user.first_name} {user.last_name}" if user else None
        enriched_assignments.append({
            "id": str(assignment.id),
            "item_id": str(assignment.item_id),
            "item_name": item_name,
            "item_code": item_code,
            "assigned_to": str(assignment.assigned_to),
            "assigned_to_name": assigned_to_name,
            "assigned_date": assignment.assigned_date.isoformat(),
            "return_date": assignment.return_date.isoformat() if assignment.return_date else None,
            "status": assignment.status,
            "notes": assignment.notes,
            "created_at": assignment.created_at.isoformat()
        })
    
    return success_response(enriched_assignments)


@router.post("/assignments")
async def create_asset_assignment(
    assignment: AssetAssignmentCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    return success_response(await inventory_service.assign(db, tenant, assignment))


@router.post("/assignments/{assignment_id}/return")
async def return_asset_assignment(
    assignment_id: UUID,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    return success_response(await inventory_service.return_assignment(db, tenant, assignment_id, notes))


# ==================== Maintenance Requests Endpoints ====================

@router.get("/maintenance-requests")
async def get_maintenance_requests(
    item_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.read"))
):
    """Get maintenance requests with filtering"""
    from app.domain.entities.inventory import MaintenanceRequest, InventoryItem
    
    query = select(MaintenanceRequest)
    
    conditions = []
    if item_id:
        conditions.append(MaintenanceRequest.item_id == item_id)
    if status:
        conditions.append(MaintenanceRequest.status == status.upper())
    if priority:
        conditions.append(MaintenanceRequest.priority == priority.upper())
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(MaintenanceRequest.created_at.desc(), MaintenanceRequest.id).limit(limit).offset(offset)
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    enriched_requests = []
    item_names = await inventory_service.related_records(db, InventoryItem, {row.item_id for row in requests})
    user_names = await inventory_service.related_records(db, User, {value for row in requests for value in (row.reported_by, row.assigned_to) if value})
    for req in requests:
        item = item_names.get(req.item_id)
        reporter = user_names.get(req.reported_by)
        assignee = user_names.get(req.assigned_to)
        item_name = item.item_name if item else None
        item_code = item.item_code if item else None
        reported_by_name = f"{reporter.first_name} {reporter.last_name}" if reporter else None
        assigned_to_name = f"{assignee.first_name} {assignee.last_name}" if assignee else None
        enriched_requests.append({
            "id": str(req.id),
            "item_id": str(req.item_id),
            "item_name": item_name,
            "item_code": item_code,
            "reported_by": str(req.reported_by),
            "reported_by_name": reported_by_name,
            "issue_description": req.issue_description,
            "priority": req.priority,
            "status": req.status,
            "assigned_to": str(req.assigned_to) if req.assigned_to else None,
            "assigned_to_name": assigned_to_name,
            "resolved_at": req.resolved_at.isoformat() if req.resolved_at else None,
            "resolution_notes": req.resolution_notes,
            "created_at": req.created_at.isoformat()
        })
    
    return success_response(enriched_requests)


@router.post("/maintenance-requests")
async def create_maintenance_request(
    request: MaintenanceRequestCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    return success_response(await inventory_service.maintenance(db, tenant, request))


@router.post("/maintenance-requests/{request_id}/resolve")
async def resolve_maintenance_request(
    request_id: UUID,
    resolution_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    return success_response(await inventory_service.resolve(db, tenant, request_id, resolution_notes))
