from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException, Request, status

from core.auth_session import AuthSessionError, read_auth_session
from core.settings import get_settings


@dataclass(frozen=True)
class AuthContext:
    user_id: int
    tenant_code: str
    is_admin: bool
    permissions: frozenset[str]

    def require(self, permission: str) -> None:
        if self.is_admin or permission in self.permissions:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para executar esta ação.")


def _extract_bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def _context_from_payload(payload: dict) -> AuthContext:
    tenant_code = str(payload.get("tenant_code") or "").strip().lower()
    user_id = payload.get("user_id") or payload.get("member_id") or payload.get("sub") or payload.get("id")
    if not tenant_code or user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sua sessão é inválida. Entre novamente.")

    raw_permissions = payload.get("permissions") or []
    if isinstance(raw_permissions, str):
        raw_permissions = [item.strip() for item in raw_permissions.split(",") if item.strip()]

    return AuthContext(
        user_id=int(user_id),
        tenant_code=tenant_code,
        is_admin=bool(payload.get("is_admin") or payload.get("is_dev")),
        permissions=frozenset(str(item) for item in raw_permissions),
    )


def _context_from_mail_session(request: Request) -> AuthContext | None:
    settings = get_settings()
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        return None
    try:
        payload = read_auth_session(token, settings.auth_session_secret)
    except AuthSessionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _context_from_payload(payload)


async def _context_from_legacy_remote(
    request: Request,
    bearer_token: str,
) -> AuthContext:
    settings = get_settings()
    if not settings.auth_context_url:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sua sessão não foi encontrada. Entre novamente.")

    try:
        async with httpx.AsyncClient(timeout=settings.auth_timeout_seconds) as client:
            response = await client.get(
                settings.auth_context_url,
                headers={"Authorization": f"Bearer {bearer_token}"},
                cookies=request.cookies,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível validar sua sessão porque o Orbital está indisponível.",
        ) from exc

    if response.status_code in {401, 403}:
        raise HTTPException(status_code=response.status_code, detail="Sua sessão expirou ou não possui acesso ao Mail.")
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Não foi possível validar sua sessão. Tente novamente.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O Orbital retornou uma resposta de autenticação inválida.",
        ) from exc
    return _context_from_payload(payload)


async def get_auth_context(
    request: Request,
    authorization: str | None = Header(default=None),
) -> AuthContext:
    settings = get_settings()

    if settings.auth_mode == "disabled":
        # Standalone local: os três valores vêm exclusivamente do .env do orbital-mail.
        tenant_code = str(settings.dev_tenant_code or "").strip().lower()
        if not tenant_code:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AUTH_DEV_TENANT_CODE não configurado para AUTH_MODE=disabled.",
            )
        return AuthContext(
            user_id=settings.dev_user_id,
            tenant_code=tenant_code,
            is_admin=settings.dev_is_admin,
            permissions=frozenset({"mail.view", "mail.manage", "mail.send"}),
        )

    session_context = _context_from_mail_session(request)
    if session_context is not None:
        return session_context

    # Compatibilidade opcional com um proxy/context endpoint já existente.
    bearer_token = _extract_bearer(authorization)
    if bearer_token:
        return await _context_from_legacy_remote(request, bearer_token)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sua sessão não foi encontrada. Entre novamente.")
