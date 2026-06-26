from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import Depends, Header, HTTPException, status

from medarchive_api.config import Settings, get_settings

Role = Literal[
    "viewer",
    "operator",
    "senior_operator",
    "catalog_manager",
    "administrator",
    "auditor",
    "integration_client",
]


@dataclass(frozen=True)
class Principal:
    subject: str
    actor_id: UUID
    roles: frozenset[Role]
    auth_mode: str

    def has_any_role(self, required_roles: frozenset[Role]) -> bool:
        return bool(self.roles.intersection(required_roles))


def get_current_principal(
    settings: Annotated[Settings, Depends(get_settings)],
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    proxy_subject: Annotated[str | None, Header(alias="X-Forwarded-User")] = None,
    proxy_roles: Annotated[str | None, Header(alias="X-Forwarded-Roles")] = None,
) -> Principal:
    if settings.auth_mode in {"local_jwt", "api_key"}:
        return _api_key_principal(settings=settings, api_key=api_key)
    if settings.auth_mode in {"oidc", "oauth2_client_credentials"}:
        return _bearer_principal(settings=settings, authorization=authorization)
    if settings.auth_mode == "trusted_reverse_proxy":
        return _trusted_proxy_principal(subject=proxy_subject, roles_header=proxy_roles)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            f"Authentication mode '{settings.auth_mode}' is configured "
            "but no adapter is installed."
        ),
    )


def _api_key_principal(*, settings: Settings, api_key: str | None) -> Principal:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    principals = _parse_local_api_keys(settings.local_api_keys)
    principal = principals.get(api_key)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return principal


def _bearer_principal(*, settings: Settings, authorization: str | None) -> Principal:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    principals = _parse_token_roles(settings.bearer_tokens, subject_prefix="bearer-token")
    principal = principals.get(token)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(
        subject=principal.subject,
        actor_id=principal.actor_id,
        roles=principal.roles,
        auth_mode=settings.auth_mode,
    )


def _trusted_proxy_principal(*, subject: str | None, roles_header: str | None) -> Principal:
    if subject is None or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing trusted proxy subject header.",
        )
    parsed_roles = [role.strip() for role in (roles_header or "").split(",") if role.strip()]
    roles = frozenset(cast(Role, role) for role in parsed_roles if _is_known_role(role))
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trusted proxy identity has no recognized roles.",
        )
    normalized_subject = subject.strip()
    return Principal(
        subject=f"trusted-proxy:{normalized_subject}",
        actor_id=uuid5(NAMESPACE_URL, f"medarchive:trusted-proxy:{normalized_subject}"),
        roles=roles,
        auth_mode="trusted_reverse_proxy",
    )


def require_roles(*roles: Role) -> Callable[[Principal], Principal]:
    required_roles = frozenset(roles)

    def dependency(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if principal.has_any_role(required_roles):
            return principal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Required one of roles: {', '.join(sorted(required_roles))}.",
        )

    return dependency


def _parse_local_api_keys(value: str) -> dict[str, Principal]:
    return _parse_token_roles(value, subject_prefix="local-api-key")


def _parse_token_roles(value: str, *, subject_prefix: str) -> dict[str, Principal]:
    principals: dict[str, Principal] = {}
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        token, separator, role_text = item.partition(":")
        if not separator:
            continue
        parsed_roles = (
            role.strip() for role in role_text.split(",") if role.strip()
        )
        roles = frozenset(cast(Role, role) for role in parsed_roles if _is_known_role(role))
        if not token or not roles:
            continue
        subject = f"{subject_prefix}:{token}"
        principals[token] = Principal(
            subject=subject,
            actor_id=uuid5(NAMESPACE_URL, f"medarchive:{subject}"),
            roles=roles,
            auth_mode=subject_prefix,
        )
    return principals


def _is_known_role(value: str) -> bool:
    return value in {
        "viewer",
        "operator",
        "senior_operator",
        "catalog_manager",
        "administrator",
        "auditor",
        "integration_client",
    }
