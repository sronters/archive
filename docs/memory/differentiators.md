# MedArchive Differentiators

MedArchive must be positioned and built as a trusted price-update layer, not as another OCR/table/search demo.

## Four Core Differences

1. Evidence-first extraction.
   Every extracted price must be traceable to the original file, page or sheet, row, bbox or cell, parser, parser version, confidence, processing run, and operator decision.

2. Self-improving partner profiles.
   The system may store partner-specific layouts, column mappings, abbreviations, and normalization rules only after manual confirmation. Profiles improve extraction for repeated clinic formats, with fallback to universal parsers when the structure changes.

3. Confidence-aware verification.
   Low-confidence or conflicting values are not automatically published. Price cells are more critical than service-name text and must be routed to review when confidence, second-pass verification, or anomaly checks disagree.

4. Integration-ready publication.
   Verified prices preserve `external_partner_id`, `external_service_id`, and `external_source_id`, then publish through REST, webhooks, JSON, CSV, and XLSX without replacing the company CRM, catalog, SSO, or public apps.

## Demo Flow

1. Upload a ZIP with mixed formats.
2. Show parser routing per file and per page.
3. Show direct XLSX extraction for large workbooks.
4. Show mixed PDF handling: text layer first, OCR fallback for weak pages.
5. Open an extracted price and show exact evidence.
6. Approve or correct a review task.
7. Upload a newer price list for the same partner.
8. Show price diff, new/removed services, and anomaly routing.
9. Publish verified prices.
10. Show API/webhook/export payloads with external IDs.
