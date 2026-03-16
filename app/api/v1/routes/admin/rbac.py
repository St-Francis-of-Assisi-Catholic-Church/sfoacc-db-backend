import logging
from typing import Any
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep, CurrentUser, require_permission
from app.models.rbac import Role, Permission
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleRead, PermissionRead, RolePermissionsUpdate
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_REQUIRE_ROLES = require_permission("admin:roles")


@router.get("/permissions", response_model=APIResponse, dependencies=[_REQUIRE_ROLES])
async def list_permissions(session: SessionDep, current_user: CurrentUser) -> Any:
    permissions = session.query(Permission).order_by(Permission.module, Permission.code).all()
    return APIResponse(message="Permissions retrieved", data=[PermissionRead.model_validate(p) for p in permissions])


@router.get("/roles", response_model=APIResponse, dependencies=[_REQUIRE_ROLES])
async def list_roles(session: SessionDep, current_user: CurrentUser) -> Any:
    roles = session.query(Role).all()
    return APIResponse(message="Roles retrieved", data=[RoleRead.model_validate(r) for r in roles])


@router.post("/roles", response_model=APIResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[_REQUIRE_ROLES])
async def create_role(*, session: SessionDep, current_user: CurrentUser, data: RoleCreate) -> Any:
    try:
        role = Role(**data.model_dump(), is_system=False)
        session.add(role)
        session.commit()
        session.refresh(role)
        return APIResponse(message="Role created", data=RoleRead.model_validate(role))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Role name already exists")


@router.get("/roles/{role_id}", response_model=APIResponse, dependencies=[_REQUIRE_ROLES])
async def get_role(role_id: int, session: SessionDep, current_user: CurrentUser) -> Any:
    role = session.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return APIResponse(message="Role retrieved", data=RoleRead.model_validate(role))


@router.put("/roles/{role_id}", response_model=APIResponse, dependencies=[_REQUIRE_ROLES])
async def update_role(role_id: int, *, session: SessionDep, current_user: CurrentUser, data: RoleUpdate) -> Any:
    role = session.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.name == "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The super_admin role cannot be modified")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    session.commit()
    session.refresh(role)
    return APIResponse(message="Role updated", data=RoleRead.model_validate(role))


@router.delete("/roles/{role_id}", response_model=APIResponse, dependencies=[_REQUIRE_ROLES])
async def delete_role(role_id: int, *, session: SessionDep, current_user: CurrentUser) -> Any:
    role = session.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete a system role")
    session.delete(role)
    session.commit()
    return APIResponse(message="Role deleted")


@router.put("/roles/{role_id}/permissions", response_model=APIResponse, dependencies=[_REQUIRE_ROLES])
async def set_role_permissions(role_id: int, *, session: SessionDep, current_user: CurrentUser, data: RolePermissionsUpdate) -> Any:
    role = session.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.name == "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The super_admin role's permissions cannot be modified")
    permissions = session.query(Permission).filter(Permission.id.in_(data.permission_ids)).all()
    role.permissions = permissions
    session.commit()
    session.refresh(role)
    return APIResponse(message="Permissions updated", data=RoleRead.model_validate(role))
