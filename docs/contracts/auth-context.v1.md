# Authentication Context Contract v1

## Modes

```text
local_jwt
oidc
api_key
oauth2_client_credentials
trusted_reverse_proxy
```

## Roles

```text
viewer
operator
senior_operator
catalog_manager
administrator
auditor
integration_client
```

## Context

```json
{
  "schema_version": "1.0",
  "subject": "user-123",
  "display_name": "Operator",
  "roles": ["operator"],
  "scopes": ["review:read", "review:write"],
  "auth_mode": "oidc"
}
```

## Rules

- Authorization is enforced in backend services, not only in UI.
- Machine-to-machine integrations use separate credentials and scopes.
- The domain layer receives authenticated actor context, not provider-specific tokens.

## Local Adapter

Local development uses the `local_jwt` mode name for the default local identity adapter, with API keys supplied through the `X-API-Key` header. The `LOCAL_API_KEYS` setting is a semicolon-separated list:

```text
token:role,role;token:role
```

Default development credentials:

```text
dev-admin       administrator,catalog_manager,senior_operator,operator,auditor,viewer,integration_client
dev-operator    operator,viewer
dev-integration integration_client
```

These keys are only local defaults. Production deployments must configure a company-approved identity adapter or explicitly rotate local keys before use.

## Route Policy

```text
POST /api/v1/ingestion-batches              operator, senior_operator, administrator
POST /api/v1/service-catalog/imports        catalog_manager, administrator
POST /api/v1/partners/imports               catalog_manager, administrator
GET  /api/v1/review-tasks                   operator, senior_operator, administrator, auditor
POST /api/v1/review-tasks/*                 operator, senior_operator, administrator
GET  /api/v1/price-versions                 viewer, operator, administrator, auditor, integration_client
GET  /api/v1/services/*/offers              integration_client, administrator, viewer
GET  /api/v1/partners/*/prices              integration_client, administrator, viewer
GET  /api/v1/price-changes                  integration_client, administrator, viewer
GET  /api/v1/exports/price-versions         integration_client, administrator, auditor
```

Health and readiness endpoints remain unauthenticated so orchestrators can check liveness without application credentials.

## Integrated Modes

- `local_jwt` and `api_key` use `X-API-Key` and the `LOCAL_API_KEYS` role map.
- `oidc` and `oauth2_client_credentials` use `Authorization: Bearer <token>` and the configured `BEARER_TOKENS` role map in local/integration deployments. Production deployments replace this adapter with company token validation or introspection without changing route policy.
- `trusted_reverse_proxy` accepts `X-Forwarded-User` and `X-Forwarded-Roles` only from the trusted ingress layer configured by deployment.
