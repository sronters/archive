# Integration Contracts

These contracts are versioned from the beginning so MedArchive can integrate with existing company systems without embedding company-specific API logic in the domain layer.

Contract versioning rules:

- Use explicit schema version fields in payloads.
- Preserve backward compatibility within a major version.
- Additive fields are allowed.
- Breaking changes require a new major contract version.
- Payloads must include both MedArchive internal IDs and company external IDs when available.

## Contracts

- [Partner Synchronization](partner-sync.v1.md)
- [Service Catalog Synchronization](service-catalog-sync.v1.md)
- [Document Ingestion](document-ingestion.v1.md)
- [Verified Price Publication](price-publication.v1.md)
- [Webhook Events](webhook-events.v1.md)
- [Exports](exports.v1.md)
- [Authentication Context](auth-context.v1.md)
- [Processing Outbox](processing-outbox.v1.md)
- [Review Tasks](review-tasks.v1.md)

## Required Identifiers

```text
partner_id              Internal MedArchive UUID
external_partner_id     Partner ID in the company system

service_id              Internal MedArchive UUID
external_service_id     Service ID in the company catalog

source_document_id      Internal MedArchive UUID
external_source_id      Optional identifier from the source system
```
