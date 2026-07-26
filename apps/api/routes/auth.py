import secrets
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from core.auth import AuthContext, get_auth_context
from core.auth_session import create_auth_session
from core.settings import get_settings

router = APIRouter(prefix="/auth", tags=["Orbital Mail Auth"])
STATE_COOKIE = "orbital_mail_auth_state"
RETURN_COOKIE = "orbital_mail_auth_return"


def _safe_return_path(value: str | None) -> str:
    raw = str(value or "/").strip()
    if not raw.startswith("/") or raw.startswith("//"):
        return "/"
    parsed = urlparse(raw)
    if parsed.scheme or parsed.netloc:
        return "/"
    return raw


def _cookie_options(settings) -> dict:
    return {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": "lax",
        "path": "/",
    }


def _web_destination(settings, return_to: str) -> str:
    base = str(settings.auth_web_url or "/")
    return urljoin(base if base.endswith("/") else f"{base}/", return_to.lstrip("/"))


@router.get("/start", include_in_schema=False)
def start_authentication(return_to: str = Query(default="/")):
    settings = get_settings()
    safe_return = _safe_return_path(return_to)
    if settings.auth_mode == "disabled":
        return RedirectResponse(url=_web_destination(settings, safe_return))

    state = secrets.token_urlsafe(32)
    parameters = urlencode({
        "client_id": settings.auth_client_id,
        "redirect_uri": settings.auth_redirect_uri,
        "response_type": "code",
        "state": state,
    })
    separator = "&" if "?" in str(settings.auth_authorize_url) else "?"
    response = RedirectResponse(
        url=f"{settings.auth_authorize_url}{separator}{parameters}",
        status_code=status.HTTP_302_FOUND,
    )
    response.set_cookie(STATE_COOKIE, state, max_age=300, **_cookie_options(settings))
    response.set_cookie(RETURN_COOKIE, safe_return, max_age=300, **_cookie_options(settings))
    return response


@router.get("/callback", include_in_schema=False)
async def authentication_callback(request: Request, code: str, state: str):
    settings = get_settings()
    if settings.auth_mode != "remote":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO desativado no modo standalone.")
    expected_state = request.cookies.get(STATE_COOKIE)
    if not expected_state or not secrets.compare_digest(expected_state, state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado SSO inválido ou expirado.")

    try:
        async with httpx.AsyncClient(timeout=settings.auth_timeout_seconds) as client:
            token_response = await client.post(
                str(settings.auth_token_url),
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.auth_client_id,
                    "client_secret": settings.auth_client_secret,
                    "redirect_uri": settings.auth_redirect_uri,
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orbital indisponível para concluir o SSO.",
        ) from exc

    if token_response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não foi possível concluir o SSO do Orbital.")

    try:
        identity = token_response.json()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Resposta SSO inválida.") from exc

    tenant_code = str(identity.get("tenant_code") or "").strip().lower()
    member_id = identity.get("member_id")
    if not tenant_code or member_id is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Identidade SSO incompleta.")

    session_payload = {
        "member_id": int(member_id),
        "person_id": identity.get("person_id"),
        "tenant_code": tenant_code,
        "etype_code": identity.get("etype_code"),
        "is_admin": bool(identity.get("is_admin")),
        "is_dev": bool(identity.get("is_dev")),
    }
    session_token = create_auth_session(
        session_payload,
        settings.auth_session_secret,
        settings.auth_session_ttl_seconds,
    )

    return_to = _safe_return_path(request.cookies.get(RETURN_COOKIE))
    response = RedirectResponse(url=_web_destination(settings, return_to), status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        settings.auth_cookie_name,
        session_token,
        max_age=settings.auth_session_ttl_seconds,
        **_cookie_options(settings),
    )
    response.delete_cookie(STATE_COOKIE, path="/")
    response.delete_cookie(RETURN_COOKIE, path="/")
    return response


@router.get("/context")
async def current_context(auth: AuthContext = Depends(get_auth_context)) -> dict:
    return {
        "user_id": auth.user_id,
        "tenant_code": auth.tenant_code,
        "is_admin": auth.is_admin,
    }


@router.post("/logout", include_in_schema=False)
def logout():
    settings = get_settings()
    response = RedirectResponse(url=str(settings.auth_web_url or "/"), status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return response
