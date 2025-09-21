"""
Issue #26: Enhanced RBAC API Router
====================================

Router implementing the RBAC endpoints defined in contracts/api/openapi/main.yaml
Supports role hierarchy, dynamic assignment, and endpoint access control.

Contract compliance:
- GET/POST /v1/rbac/roles
- GET/PUT/DELETE /v1/rbac/roles/{roleName}
- GET/POST/PUT/DELETE /v1/rbac/bindings
- GET /v1/rbac/hierarchy/{roleName}
"""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

# Import enhanced RBAC components
from policy.rbac import Binding, RbacEngine, RBACError, RoleDef

# Security for control plane
security = HTTPBearer()

# Router with RBAC tag matching OpenAPI contract
router = APIRouter(prefix="/v1/rbac", tags=["RBAC"])

# Default RBAC engine path (can be made configurable)
RBAC_PATH = "data/rbac.json"


def get_rbac_engine() -> RbacEngine:
    """Dependency to get RBAC engine instance"""
    return RbacEngine(RBAC_PATH)


# Pydantic models for API contracts


class RoleDefinition(BaseModel):
    """Role definition matching contract schema"""

    name: str = Field(..., description="Role name")
    capabilities: List[str] = Field(..., description="Role capabilities")
    inherits: List[str] = Field(default_factory=list, description="Inherited roles")
    description: str = Field("", description="Role description")


class RoleResponse(BaseModel):
    """Role response with hierarchy information"""

    name: str
    capabilities: List[str]
    inherits: List[str]
    description: str
    created_at: str
    hierarchy: Dict[str, List[str]]


class RoleBinding(BaseModel):
    """Role binding definition"""

    principal_id: str = Field(..., description="Principal (user) ID")
    role: str = Field(..., description="Role name")
    space_id: str = Field(..., description="Space ID for scoped binding")


class BindingResponse(BaseModel):
    """Binding response with metadata"""

    principal_id: str
    role: str
    space_id: str
    created_at: str


class CapabilitiesResponse(BaseModel):
    """Capabilities response for a principal"""

    principal_id: str
    space_id: str
    capabilities: List[str]
    effective_roles: List[str]


# Issue #26.1: Role management with hierarchy support


@router.get("/roles", response_model=List[str])
async def list_roles(rbac: RbacEngine = Depends(get_rbac_engine)):
    """List all defined roles"""
    try:
        data = rbac._read()
        return list(data.get("roles", {}).keys())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list roles: {str(e)}")


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    role: RoleDefinition, rbac: RbacEngine = Depends(get_rbac_engine)
):
    """Create a new role with inheritance support - Issue #26.1"""
    try:
        role_def = RoleDef(
            name=role.name,
            caps=role.capabilities,
            inherits=role.inherits,
            description=role.description,
        )
        rbac.define_role(role_def)
        return {"message": f"Role '{role.name}' created successfully"}
    except RBACError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create role: {str(e)}")


@router.get("/roles/{role_name}", response_model=RoleResponse)
async def get_role(role_name: str, rbac: RbacEngine = Depends(get_rbac_engine)):
    """Get role details with hierarchy information - Issue #26.1"""
    try:
        data = rbac._read()
        role_data = data.get("roles", {}).get(role_name)

        if not role_data:
            raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found")

        # Handle both legacy and new formats
        if isinstance(role_data, list):
            # Legacy format
            capabilities = role_data
            inherits = []
            description = ""
            created_at = datetime.now().isoformat()
        else:
            # New format with inheritance
            capabilities = role_data.get("caps", [])
            inherits = role_data.get("inherits", [])
            description = role_data.get("description", "")
            created_at = role_data.get("created_at", datetime.now().isoformat())

        # Get hierarchy information
        hierarchy = rbac.get_role_hierarchy(role_name)

        return RoleResponse(
            name=role_name,
            capabilities=capabilities,
            inherits=inherits,
            description=description,
            created_at=created_at,
            hierarchy=hierarchy,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get role: {str(e)}")


@router.delete("/roles/{role_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_name: str, rbac: RbacEngine = Depends(get_rbac_engine)):
    """Delete a role and all its bindings"""
    try:
        rbac.remove_role(role_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete role: {str(e)}")


# Issue #26.2: Role bindings management


@router.get("/bindings", response_model=List[BindingResponse])
async def list_bindings(
    principal_id: Optional[str] = None,
    space_id: Optional[str] = None,
    role: Optional[str] = None,
    rbac: RbacEngine = Depends(get_rbac_engine),
):
    """List role bindings with optional filtering"""
    try:
        bindings = rbac.get_bindings(
            principal_id=principal_id, space_id=space_id, role=role
        )
        return [
            BindingResponse(
                principal_id=b["principal_id"],
                role=b["role"],
                space_id=b["space_id"],
                created_at=b["created_at"],
            )
            for b in bindings
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list bindings: {str(e)}"
        )


@router.post("/bindings", status_code=status.HTTP_201_CREATED)
async def create_binding(
    binding: RoleBinding, rbac: RbacEngine = Depends(get_rbac_engine)
):
    """Create a new role binding - Issue #26.2"""
    try:
        binding_obj = Binding(
            principal_id=binding.principal_id,
            role=binding.role,
            space_id=binding.space_id,
        )
        rbac.bind(binding_obj)
        return {"message": f"Binding created for principal '{binding.principal_id}'"}
    except RBACError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create binding: {str(e)}"
        )


@router.delete("/bindings")
async def delete_binding(
    principal_id: str,
    role: str,
    space_id: str,
    rbac: RbacEngine = Depends(get_rbac_engine),
):
    """Delete a specific role binding"""
    try:
        rbac.unbind(principal_id, role, space_id)
        return {"message": f"Binding removed for principal '{principal_id}'"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete binding: {str(e)}"
        )


# Issue #26.1: Hierarchy inspection endpoints


@router.get("/hierarchy/{role_name}")
async def get_role_hierarchy(
    role_name: str, rbac: RbacEngine = Depends(get_rbac_engine)
):
    """Get complete hierarchy information for a role - Issue #26.1"""
    try:
        hierarchy = rbac.get_role_hierarchy(role_name)
        return {
            "role": role_name,
            "hierarchy": hierarchy,
            "effective_capabilities": list(
                rbac._resolve_role_capabilities(role_name, rbac._read())
            ),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get hierarchy: {str(e)}"
        )


# Capability resolution endpoints


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities(
    principal_id: str, space_id: str, rbac: RbacEngine = Depends(get_rbac_engine)
):
    """Get effective capabilities for a principal in a space"""
    try:
        capabilities = rbac.list_caps(principal_id, space_id)

        # Get roles for context
        bindings = rbac.get_bindings(principal_id=principal_id, space_id=space_id)
        roles = [b["role"] for b in bindings]

        return CapabilitiesResponse(
            principal_id=principal_id,
            space_id=space_id,
            capabilities=sorted(list(capabilities)),
            effective_roles=roles,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get capabilities: {str(e)}"
        )


@router.get("/check-capability")
async def check_capability(
    principal_id: str,
    space_id: str,
    capability: str,
    rbac: RbacEngine = Depends(get_rbac_engine),
):
    """Check if a principal has a specific capability in a space"""
    try:
        has_capability = rbac.has_cap(principal_id, space_id, capability)
        return {
            "principal_id": principal_id,
            "space_id": space_id,
            "capability": capability,
            "granted": has_capability,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to check capability: {str(e)}"
        )
