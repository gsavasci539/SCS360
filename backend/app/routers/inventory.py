"""
Demirbaş & Envanter Yönetimi Module API
Handles inventory items, locations, assignments, and maintenance requests
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.responses import success_response
from app.core.security import PermissionChecker, TenantContext
from app.domain.entities import User, Branch

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


# ==================== Schemas ====================

class InventoryItemCreate(BaseModel):
    branch_id: UUID
    item_code: str = Field(..., max_length=50)
    item_name: str = Field(..., max_length=255)
    category: Optional[str] = None
    description: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    current_value: Optional[Decimal] = Field(None, ge=0)
    location_id: Optional[UUID] = None
    condition: Optional[str] = None
    qr_code: Optional[str] = None
    barcode: Optional[str] = None
    warranty_expiry: Optional[date] = None

class InventoryLocationCreate(BaseModel):
    branch_id: UUID
    location_name: str = Field(..., max_length=255)
    location_type: Optional[str] = None
    description: Optional[str] = None

class AssetAssignmentCreate(BaseModel):
    item_id: UUID
    assigned_to: UUID
    return_date: Optional[date] = None
    notes: Optional[str] = None

class MaintenanceRequestCreate(BaseModel):
    item_id: UUID
    issue_description: str = Field(..., description="Issue description")
    priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, URGENT")
    assigned_to: Optional[UUID] = None


# ==================== Inventory Items Endpoints ====================

@router.get("/items")
async def get_inventory_items(
    branch_id: Optional[UUID] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    location_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
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
    
    query = query.order_by(InventoryItem.item_code).limit(limit).offset(offset)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    enriched_items = []
    for item in items:
        # Get branch name
        branch_name = None
        if item.branch_id:
            branch_result = await db.execute(
                select(Branch).where(Branch.id == item.branch_id)
            )
            branch = branch_result.scalar_one_or_none()
            if branch:
                branch_name = branch.name
        
        # Get location name
        location_name = None
        if item.location_id:
            from app.domain.entities.inventory import InventoryLocation
            location_result = await db.execute(
                select(InventoryLocation).where(InventoryLocation.id == item.location_id)
            )
            location = location_result.scalar_one_or_none()
            if location:
                location_name = location.location_name
        
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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    """Create a new inventory item"""
    from app.domain.entities.inventory import InventoryItem
    
    new_item = InventoryItem(
        branch_id=item.branch_id,
        item_code=item.item_code,
        item_name=item.item_name,
        category=item.category,
        description=item.description,
        purchase_date=item.purchase_date,
        purchase_price=item.purchase_price,
        current_value=item.current_value,
        location_id=item.location_id,
        condition=item.condition,
        qr_code=item.qr_code,
        barcode=item.barcode,
        warranty_expiry=item.warranty_expiry,
        status="ACTIVE"
    )
    db.add(new_item)
    await db.commit()
    await db.refresh(new_item)
    
    return success_response({
        "id": str(new_item.id),
        "item_code": new_item.item_code,
        "item_name": new_item.item_name,
        "status": new_item.status,
        "created_at": new_item.created_at.isoformat()
    })


@router.put("/items/{item_id}")
async def update_inventory_item(
    item_id: UUID,
    item: InventoryItemCreate,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    """Update an inventory item"""
    from app.domain.entities.inventory import InventoryItem
    
    result = await db.execute(
        select(InventoryItem).where(InventoryItem.id == item_id)
    )
    existing_item = result.scalar_one_or_none()
    
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    existing_item.branch_id = item.branch_id
    existing_item.item_code = item.item_code
    existing_item.item_name = item.item_name
    existing_item.category = item.category
    existing_item.description = item.description
    existing_item.purchase_date = item.purchase_date
    existing_item.purchase_price = item.purchase_price
    existing_item.current_value = item.current_value
    existing_item.location_id = item.location_id
    existing_item.condition = item.condition
    existing_item.qr_code = item.qr_code
    existing_item.barcode = item.barcode
    existing_item.warranty_expiry = item.warranty_expiry
    
    await db.commit()
    
    return success_response({
        "id": str(existing_item.id),
        "updated_at": existing_item.updated_at.isoformat()
    })


# ==================== Inventory Locations Endpoints ====================

@router.get("/locations")
async def get_inventory_locations(
    branch_id: Optional[UUID] = Query(None),
    location_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    
    query = query.order_by(AssetAssignment.assigned_date.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    enriched_assignments = []
    for assignment in assignments:
        # Get item name
        item_name = None
        item_code = None
        if assignment.item_id:
            item_result = await db.execute(
                select(InventoryItem).where(InventoryItem.id == assignment.item_id)
            )
            item = item_result.scalar_one_or_none()
            if item:
                item_name = item.item_name
                item_code = item.item_code
        
        # Get assigned to name
        assigned_to_name = None
        if assignment.assigned_to:
            user_result = await db.execute(
                select(User).where(User.id == assignment.assigned_to)
            )
            user = user_result.scalar_one_or_none()
            if user:
                assigned_to_name = f"{user.first_name} {user.last_name}"
        
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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    """Create a new asset assignment"""
    from app.domain.entities.inventory import AssetAssignment
    
    new_assignment = AssetAssignment(
        item_id=assignment.item_id,
        assigned_to=assignment.assigned_to,
        assigned_date=date.today(),
        return_date=assignment.return_date,
        notes=assignment.notes,
        status="ASSIGNED"
    )
    db.add(new_assignment)
    await db.commit()
    await db.refresh(new_assignment)
    
    return success_response({
        "id": str(new_assignment.id),
        "assigned_date": new_assignment.assigned_date.isoformat(),
        "status": new_assignment.status,
        "created_at": new_assignment.created_at.isoformat()
    })


@router.post("/assignments/{assignment_id}/return")
async def return_asset_assignment(
    assignment_id: UUID,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    """Return an assigned asset"""
    from app.domain.entities.inventory import AssetAssignment
    
    result = await db.execute(
        select(AssetAssignment).where(AssetAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    assignment.status = "RETURNED"
    assignment.return_date = date.today()
    assignment.notes = notes
    
    await db.commit()
    
    return success_response({
        "id": str(assignment.id),
        "status": "RETURNED",
        "return_date": assignment.return_date.isoformat()
    })


# ==================== Maintenance Requests Endpoints ====================

@router.get("/maintenance-requests")
async def get_maintenance_requests(
    item_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
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
    
    query = query.order_by(MaintenanceRequest.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    requests = result.scalars().all()
    
    enriched_requests = []
    for req in requests:
        # Get item name
        item_name = None
        item_code = None
        if req.item_id:
            item_result = await db.execute(
                select(InventoryItem).where(InventoryItem.id == req.item_id)
            )
            item = item_result.scalar_one_or_none()
            if item:
                item_name = item.item_name
                item_code = item.item_code
        
        # Get reported by name
        reported_by_name = None
        if req.reported_by:
            user_result = await db.execute(
                select(User).where(User.id == req.reported_by)
            )
            user = user_result.scalar_one_or_none()
            if user:
                reported_by_name = f"{user.first_name} {user.last_name}"
        
        # Get assigned to name
        assigned_to_name = None
        if req.assigned_to:
            user_result = await db.execute(
                select(User).where(User.id == req.assigned_to)
            )
            user = user_result.scalar_one_or_none()
            if user:
                assigned_to_name = f"{user.first_name} {user.last_name}"
        
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
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    """Create a new maintenance request"""
    from app.domain.entities.inventory import MaintenanceRequest
    
    new_request = MaintenanceRequest(
        item_id=request.item_id,
        reported_by=None,  # Will be set from current user context
        issue_description=request.issue_description,
        priority=request.priority.upper(),
        status="PENDING",
        assigned_to=request.assigned_to
    )
    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)
    
    return success_response({
        "id": str(new_request.id),
        "priority": new_request.priority,
        "status": new_request.status,
        "created_at": new_request.created_at.isoformat()
    })


@router.post("/maintenance-requests/{request_id}/resolve")
async def resolve_maintenance_request(
    request_id: UUID,
    resolution_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(PermissionChecker("inventory.write"))
):
    """Resolve a maintenance request"""
    from app.domain.entities.inventory import MaintenanceRequest
    
    result = await db.execute(
        select(MaintenanceRequest).where(MaintenanceRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    
    if not req:
        raise HTTPException(status_code=404, detail="Maintenance request not found")
    
    req.status = "RESOLVED"
    req.resolved_at = datetime.utcnow()
    req.resolution_notes = resolution_notes
    
    await db.commit()
    
    return success_response({
        "id": str(req.id),
        "status": "RESOLVED",
        "resolved_at": req.resolved_at.isoformat()
    })
