from fastapi import APIRouter, Depends

from core.auth import AuthContext, get_auth_context

router = APIRouter(prefix="/auth", tags=["Orbital Mail Auth"])


@router.get("/context")
async def current_context(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return {
        "user_id": auth.user_id,
        "tenant_code": auth.tenant_code,
        "is_admin": auth.is_admin,
        "is_dev": auth.is_dev,
        "permissions": [
            {"page_alias": page_alias, "action_code": action_code}
            for page_alias, action_code in sorted(auth.permissions)
        ],
    }
