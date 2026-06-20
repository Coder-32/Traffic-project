from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from db_models import Resource, Allocation
from schemas import (
    ResourceListResponse,
    ResourceItem,
    AllocateRequest,
    AllocateResponse,
    ReleaseResponse,
    ReleasedResourceItem,
    ActiveAllocationItem,
    ResourceSummaryResponse,
    UpdateResourceTotalRequest,
    CreateResourceRequest,
    ActiveDeploymentItem,
)

router = APIRouter()

# ── GET /resources ────────────────────────────────────────────────────────────
@router.get("", response_model=ResourceListResponse, summary="Get all resources grouped by category")
def get_resources(db: Session = Depends(get_db)):
    resources = db.query(Resource).all()
    grouped = {
        "personnel": [],
        "vehicle": [],
        "equipment": []
    }
    for r in resources:
        item = ResourceItem(
            id=r.id,
            name=r.name,
            category=r.category,
            total_count=r.total_count,
            available_count=r.available_count,
            unit=r.unit,
            allocated_count=r.total_count - r.available_count
        )
        if r.category in grouped:
            grouped[r.category].append(item)
    return grouped


# ── POST /resources/allocate ──────────────────────────────────────────────────
@router.post("/allocate", response_model=AllocateResponse, summary="Allocate resources to an incident")
def allocate_resources(payload: AllocateRequest, db: Session = Depends(get_db)):
    allocations_to_process = []
    
    # 1. Validate all allocations before making any database updates
    for alloc_in in payload.allocations:
        resource = db.query(Resource).filter(Resource.id == alloc_in.resource_id).first()
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resource with ID {alloc_in.resource_id} not found"
            )
        if resource.available_count < alloc_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient {resource.name}: need {alloc_in.quantity}, have {resource.available_count}"
            )
        allocations_to_process.append((resource, alloc_in.quantity))
        
    # 2. Update resource availability and create allocation rows
    allocation_ids = []
    for resource, qty in allocations_to_process:
        resource.available_count -= qty
        new_alloc = Allocation(
            incident_id=payload.incident_id,
            incident_address=payload.incident_address,
            resource_id=resource.id,
            quantity_allocated=qty,
            status="active",
            notes=payload.notes
        )
        db.add(new_alloc)
        db.flush()  # Populates new_alloc.id
        allocation_ids.append(new_alloc.id)
        
    db.commit()
    
    # 3. Retrieve updated resource list to return
    resources = db.query(Resource).all()
    grouped = {
        "personnel": [],
        "vehicle": [],
        "equipment": []
    }
    for r in resources:
        item = ResourceItem(
            id=r.id,
            name=r.name,
            category=r.category,
            total_count=r.total_count,
            available_count=r.available_count,
            unit=r.unit,
            allocated_count=r.total_count - r.available_count
        )
        if r.category in grouped:
            grouped[r.category].append(item)
            
    return AllocateResponse(
        allocation_ids=allocation_ids,
        updated_resources=grouped
    )


# ── POST /resources/release/{incident_id} ──────────────────────────────────────
@router.post("/release/{incident_id}", response_model=ReleaseResponse, summary="Release allocations for an incident")
def release_resources(incident_id: str, db: Session = Depends(get_db)):
    active_allocations = db.query(Allocation).filter(
        Allocation.incident_id == incident_id,
        Allocation.status == "active"
    ).all()
    
    released_resources = []
    now = datetime.utcnow()
    
    for alloc in active_allocations:
        resource = db.query(Resource).filter(Resource.id == alloc.resource_id).first()
        if resource:
            resource.available_count += alloc.quantity_allocated
            released_resources.append(ReleasedResourceItem(
                resource_id=resource.id,
                name=resource.name,
                quantity_released=alloc.quantity_allocated
            ))
        alloc.status = "released"
        alloc.released_at = now
        
    db.commit()
    
    return ReleaseResponse(
        incident_id=incident_id,
        released_allocations_count=len(active_allocations),
        released_resources=released_resources
    )


# ── GET /resources/allocations ────────────────────────────────────────────────
@router.get("/allocations", response_model=list[ActiveDeploymentItem], summary="Get all active deployments/allocations")
def get_all_allocations(db: Session = Depends(get_db)):
    results = db.query(Allocation, Resource).join(
        Resource, Allocation.resource_id == Resource.id
    ).filter(
        Allocation.status == "active"
    ).order_by(Allocation.allocated_at.desc()).all()
    
    return [
        ActiveDeploymentItem(
            id=alloc.id,
            incident_id=alloc.incident_id,
            incident_address=alloc.incident_address,
            resource_name=resource.name,
            quantity=alloc.quantity_allocated,
            allocated_at=alloc.allocated_at
        )
        for alloc, resource in results
    ]


# ── GET /resources/allocations/{incident_id} ──────────────────────────────────
@router.get("/allocations/{incident_id}", response_model=list[ActiveAllocationItem], summary="Get active allocations for an incident")
def get_incident_allocations(incident_id: str, db: Session = Depends(get_db)):
    results = db.query(Allocation, Resource).join(
        Resource, Allocation.resource_id == Resource.id
    ).filter(
        Allocation.incident_id == incident_id,
        Allocation.status == "active"
    ).all()
    
    return [
        ActiveAllocationItem(
            resource_name=resource.name,
            quantity=alloc.quantity_allocated,
            allocated_at=alloc.allocated_at
        )
        for alloc, resource in results
    ]


# ── GET /resources/summary ────────────────────────────────────────────────────
@router.get("/summary", response_model=ResourceSummaryResponse, summary="Get city-wide resources summary")
def get_resources_summary(db: Session = Depends(get_db)):
    # 1. Traffic Officers statistics
    officer = db.query(Resource).filter(Resource.name == "Traffic Officer").first()
    total_officers = officer.total_count if officer else 0
    available_officers = officer.available_count if officer else 0
    deployed_officers = total_officers - available_officers
    
    # 2. Equipment statistics
    total_equip = db.query(func.sum(Resource.total_count)).filter(
        Resource.category == "equipment"
    ).scalar() or 0
    
    avail_equip = db.query(func.sum(Resource.available_count)).filter(
        Resource.category == "equipment"
    ).scalar() or 0
    
    # 3. Active allocations count
    active_alloc_count = db.query(func.count(Allocation.id)).filter(
        Allocation.status == "active"
    ).scalar() or 0
    
    # 4. Incidents with resources (active allocations)
    incidents_query = db.query(Allocation.incident_id).filter(
        Allocation.status == "active"
    ).distinct().all()
    incidents_with_resources = [row.incident_id for row in incidents_query]
    
    return ResourceSummaryResponse(
        total_officers=total_officers,
        available_officers=available_officers,
        deployed_officers=deployed_officers,
        total_equipment_units=int(total_equip),
        available_equipment_units=int(avail_equip),
        active_allocations_count=active_alloc_count,
        incidents_with_resources=incidents_with_resources
    )


# ── PATCH /resources/{resource_id} ────────────────────────────────────────────
@router.patch("/{resource_id}", response_model=ResourceItem, summary="Update total count for a resource")
def update_resource_total(
    resource_id: int,
    payload: UpdateResourceTotalRequest,
    db: Session = Depends(get_db)
):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with ID {resource_id} not found"
        )
        
    delta = payload.total_count - resource.total_count
    
    # Validate that we don't reduce total count below what is currently allocated
    if resource.available_count + delta < 0:
        allocated = resource.total_count - resource.available_count
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reduce total count to {payload.total_count} as {allocated} units are currently allocated."
        )
        
    resource.total_count = payload.total_count
    resource.available_count += delta
    
    db.commit()
    db.refresh(resource)
    
    return ResourceItem(
        id=resource.id,
        name=resource.name,
        category=resource.category,
        total_count=resource.total_count,
        available_count=resource.available_count,
        unit=resource.unit,
        allocated_count=resource.total_count - resource.available_count
    )


# ── POST /resources ───────────────────────────────────────────────────────────
@router.post("", response_model=ResourceItem, status_code=status.HTTP_201_CREATED, summary="Create a new resource")
def create_resource(payload: CreateResourceRequest, db: Session = Depends(get_db)):
    existing = db.query(Resource).filter(Resource.name == payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Resource with name '{payload.name}' already exists."
        )
    
    new_res = Resource(
        name=payload.name,
        category=payload.category,
        total_count=payload.total_count,
        available_count=payload.total_count,
        unit=payload.unit,
        description=payload.description
    )
    db.add(new_res)
    db.commit()
    db.refresh(new_res)
    
    return ResourceItem(
        id=new_res.id,
        name=new_res.name,
        category=new_res.category,
        total_count=new_res.total_count,
        available_count=new_res.available_count,
        unit=new_res.unit,
        allocated_count=0
    )
