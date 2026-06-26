# Graph Read Model Contract v1

## Purpose

The graph is a read model for explainable matching, partner memory, impact analysis, and compact UI visualization. Relational PostgreSQL tables remain the source of truth.

## Backends

```text
postgres_edges  Default local and fallback implementation using graph_nodes and graph_edges.
apache_age      Production graph backend using Apache AGE over PostgreSQL.
noop            Disabled graph projection for restricted deployments.
```

## Source Of Truth

The following tables remain authoritative:

```text
partners
services
price_documents
extracted_price_items
service_matches
price_versions
review_tasks
audit_events
```

The graph stores only minimal traversal properties:

```json
{
  "entity_id": "PostgreSQL UUID",
  "external_id": "company identifier",
  "label": "short display label",
  "status": "active"
}
```

Large values, raw text, bbox, audit history, detailed scores, and document payloads stay in relational tables.

## Nodes

```text
Partner
Service
RawServiceName
ServiceCategory
PriceDocument
PriceVersion
ReviewDecision
```

## Edges

```text
Partner        -[OFFERS]->          Service
Partner        -[SUBMITTED]->       PriceDocument
PriceDocument  -[CONTAINS]->        RawServiceName
RawServiceName -[MATCHED_TO]->      Service
RawServiceName -[CONFIRMED_AS]->    Service
Service        -[BELONGS_TO]->      ServiceCategory
Service        -[HAS_PRICE]->       PriceVersion
PriceVersion   -[EXTRACTED_FROM]->  PriceDocument
PriceVersion   -[SUPERSEDED_BY]->    PriceVersion
Service        -[POSSIBLE_DUPLICATE]-> Service
Service        -[RELATED_TO]->      Service
```

## Projection

Graph updates are outbox-driven:

```text
PriceVersion transaction
  -> OutboxEvent price_version.published
  -> worker OutboxPublisher
  -> GraphProjector
  -> GraphRepository
```

Business use cases must not call Apache AGE directly.

Projection state is tracked on outbox events:

```text
pending
processing
completed
retrying
dead_letter
```

Projection metadata:

```text
attempts
last_error
next_retry_at
processing_started_at
processed_at
published_at
```

If Apache AGE is unavailable, publication of the relational price version must remain complete.
The graph event stays retryable or dead-lettered depending on attempts. Production must not
silently switch from `apache_age` to `postgres_edges`; fallback is selected explicitly by config.

## Replay

The graph is fully rebuildable from relational PostgreSQL:

```bash
uv run medarchive graph rebuild
```

Replay must:

```text
clear graph read model
read published price_versions
project Partner, Service, PriceDocument, PriceVersion, RawServiceName links
restore SUPERSEDED_BY history
report projected price-version count
```

## API

```text
GET /api/v1/graph/services/{service_id}/neighborhood?depth=2
```

The response is Cytoscape-ready:

```json
{
  "nodes": [
    {"id": "Service:<uuid>", "type": "Service", "label": "MRI brain"}
  ],
  "edges": [
    {"source": "Partner:<uuid>", "target": "Service:<uuid>", "type": "OFFERS"}
  ]
}
```

UI must show at most two levels by default and expand on user action.

Hard API limits:

```text
depth <= 2
nodes <= 200
edges <= 500
allowed edge types only
```

The response includes `truncated=true` when the server cuts the neighborhood.
