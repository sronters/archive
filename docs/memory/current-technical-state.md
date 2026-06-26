# Current Technical State

## Status

MedArchive now has a connected production-oriented XLSX vertical slice and a rebuildable graph read model.

The graph must not be expanded further before the core processing pipeline is stronger. Its current purpose is to show explainable value from real processed price data, not to become a second source of truth.

## Completed Connected Slice

The tested path is:

```text
real multi-sheet XLSX
-> ingestion service
-> immutable storage key and SHA-256 identity
-> duplicate upload protection at recorder boundary
-> document processing service
-> XLSX parser with all sheets, hidden rows/columns, merged cells
-> extracted rows with sheet and Excel row-number provenance
-> deterministic catalog matching
-> uncertain row routed to review
-> operator correction
-> immutable PriceVersion
-> price_version.published outbox event
-> GraphProjector
-> GraphRepository
-> service neighborhood with Partner, Service, PriceVersion, PriceDocument
```

Covered by:

```text
tests/test_real_xlsx_graph_vertical_slice.py
```

## Graph Read Model Rule

Relational PostgreSQL remains authoritative.

Graph state is derived and rebuildable:

```bash
uv run medarchive graph rebuild
```

Graph backends:

```text
postgres_edges
apache_age
noop
```

Projection state is stored in outbox events:

```text
pending
processing
completed
retrying
dead_letter
```

Do not silently switch from `apache_age` to `postgres_edges` in production. Fallback is selected explicitly by configuration.

## Current Graph Value

The UI/API can display this chain from a processed and published price:

```text
Partner
-> OFFERS
-> Service
-> HAS_PRICE
-> PriceVersion
-> EXTRACTED_FROM
-> PriceDocument
```

Raw service confirmation is also linked:

```text
RawServiceName
-> CONFIRMED_AS
-> Service
```

## Next Priority

The next work should improve real document coverage and persistence depth:

- run the same connected slice against a company-provided XLSX sample;
- persist partner/date resolution from real source metadata;
- broaden parser golden fixtures with RU/KZ headers and messy clinic layouts;
- add PostgreSQL-backed integration tests in CI when a test database is available;
- keep the graph read model stable unless real user workflows require another relation.
