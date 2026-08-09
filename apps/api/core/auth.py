from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException, Request, status

from core.settings import get_settings

MODULE_PAGE_ALIAS = "orbital-mail-home"
MODULE_ACTION_CODE = "access_page"


@dataclass(frozen=True)
class AuthContext:
    user_id: int
    tenant_code: str
    is_admin: bool
    is_dev: bool
    permissions: frozenset[tuple[str, str]]

    def require_module_access(self) -> None:
        if self.is_dev or (MODULE_PAGE_ALIAS, MODULE_ACTION_CODE) in self.permissions:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso ao módulo Orbital Mail.",
        )


def _extract_token(request: Request, authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None

    for cookie_name in ("orbital_token", "access_token", "session_token"):
        value = request.cookies.get(cookie_name)
        if value:
            return value
    return None


def _normalize_permissions(raw_permissions: object) -> frozenset[tuple[str, str]]:
    if isinstance(raw_permissions, str):
        raw_permissions = [item.strip() for item in raw_permissions.split(",") if item.strip()]
    if not isinstance(raw_permissions, (list, tuple, set)):
        return frozenset()

    normalized: set[tuple[str, str]] = set()
    for item in raw_permissions:
        page_alias = action_code = None
        if isinstance(item, dict):
            page_alias = item.get("page_alias")
            action_code = item.get("action_code")
        elif isinstance(item, str):
            value = item.strip().lower()
            for separator in (":", "/", "|"):
                if separator in value:
                    page_alias, action_code = value.split(separator, 1)
                    break

        if page_alias and action_code:
            normalized.add((str(page_alias).strip().lower(), str(action_code).strip().lower()))

    return frozenset(normalized)


def _context_from_payload(payload: dict) -> AuthContext:
    tenant_code = str(payload.get("tenant_code") or "").strip().lower()
    user_id = payload.get("user_id") or payload.get("member_id") or payload.get("sub") or payload.get("id")
    if not tenant_code or user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Contexto autenticado inválido.")

    return AuthContext(
        user_id=int(user_id),
        tenant_code=tenant_code,
        is_admin=bool(payload.get("is_admin")),
        is_dev=bool(payload.get("is_dev")),
        permissions=_normalize_permissions(payload.get("permissions") or []),
    )


async def get_auth_context(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AuthContext:
    settings = get_settings()

    token = _extract_token(request, authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão não informada.")
    if not settings.auth_context_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AUTH_CONTEXT_URL não configurada.")

    try:
        async with httpx.AsyncClient(timeout=settings.auth_timeout_seconds) as client:
            response = await client.get(
                settings.auth_context_url,
                headers={"Authorization": f"Bearer {token}"},
                cookies=request.cookies,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de autenticação indisponível.",
        ) from exc

    if response.status_code in {401, 403}:
        raise HTTPException(status_code=response.status_code, detail="Sessão inválida ou sem acesso ao Mail.")
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Falha ao validar a sessão.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Resposta de autenticação inválida.") from exc

    context = _context_from_payload(payload)
    context.require_module_access()
    return context
