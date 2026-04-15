# AASHTOWare Pay-Item Alignment Notes - 2026-04-13

## Why This Is Separate From OCR

The AASHTOWare lane is worth tracking, but it should not block the immediate
Google Assisted OCR extraction gate.

For OCR, the PDF remains the source of truth. A known pay-item repository can
help after OCR as a validation, normalization, ranking, and confidence-review
signal. It should not invent missing rows or silently override document values.

## Naming

The product family is AASHTOWare, not "Astaware" or "Astro Air". In our own
notes, use `aashtoware` for code/search terms and `AASHTOWare` for prose.

## Sources Checked

- AASHTOWare OpenAPI overview:
  https://www.aashtoware.org/story/what-is-aashtoware-openapi/
- AASHTOWare OpenAPI architecture:
  https://developer.aashtoware.org/content/html_widgets/nzq08.html
- AASHTOWare OpenAPI developer portal FAQ:
  https://developer.aashtoware.org/content/html_widgets/t2qya.html
- MDOT AASHTOWare Contract Administration wiki:
  https://mdotwiki.state.mi.us/aashtoware/index.php/Contract_Administration
- MDOT AASHTOWare Daily Work Reports wiki:
  https://mdotwiki.state.mi.us/aashtoware/index.php/Daily_Work_Reports
- MDOT Bid Letting public page:
  https://www.michigan.gov/en/mdot/Business/Contractors/bid-letting

## Findings

- AASHTOWare OpenAPI is an integration gateway/API management layer for
  AASHTOWare applications. It is not a public anonymous data source.
- The OpenAPI architecture documentation says the OpenAPI layer routes requests
  but does not host API implementations or store AASHTOWare application data.
  A live integration will require an agency-hosted endpoint, credentials, and
  permission.
- The developer portal FAQ indicates developers need an active license, portal
  access, authentication credentials, and network access to the relevant agency
  endpoint.
- MDOT's AASHTOWare Contract Administration workflow treats contract items as
  known project/contract entities, including awarded vendor bid prices.
- MDOT's Daily Work Reports workflow uses item postings selected from contract
  project items. After a contract line item is selected, units and other item
  fields self-populate before the inspector enters installed quantity and field
  location details.
- MDOT public bid letting pages are useful for finding public bid-item schedules
  and AASHTOWare-like table layouts. They do not guarantee a matching
  Measurement & Payment/spec section for our paired OCR acceptance corpus.

## Data Shape To Align Toward

When we get OpenAPI access, investigate whether endpoints expose these concepts:

- agency item catalog/reference item,
- project item,
- contract project item,
- contract line item,
- awarded bid price,
- DWR item posting,
- item-material association,
- item unit and quantity fields,
- item attention/status flags,
- item source/spec book/version.

Field Guide should keep an internal known-pay-item repository shaped roughly as:

- `source_system`: `aashtoware`, `mdot`, or another agency source.
- `agency`: for example `MDOT`.
- `item_code` or `item_number`.
- `description`.
- `unit`.
- `spec_book` and `spec_year` when available.
- `effective_start` / `effective_end` or active status.
- `aliases` and historical descriptions.
- `material_set` or material association summary when available.
- `last_synced_at` and source revision metadata.

For imported project bid items, keep the document-derived fields separate from
repository-derived fields:

- `document_item_number`
- `document_description`
- `document_unit`
- `document_quantity`
- `document_unit_price`
- `document_bid_amount`
- `known_item_id` when matched
- `known_item_match_confidence`
- `known_item_match_reason`
- `requires_review` when the repository conflicts with the PDF

## How It Could Help Extraction

Use the repository after OCR/table extraction to:

- validate item-number and unit combinations,
- normalize known descriptions for search,
- rank candidate descriptions when OCR splits or merges text,
- flag impossible item-code/unit combinations,
- explain confidence issues to the user,
- improve M&P enrichment matching,
- prepare future AASHTOWare export/API mapping.

Do not use it to:

- create a row that was not present in OCR/table evidence,
- silently change quantities, unit prices, or bid amounts,
- make filename- or project-specific parser rules,
- couple the Custom Pipeline to Google or AASHTOWare-only services.

## Open Questions

- Which AASHTOWare OpenAPI product/module is available to us: Project,
  Project Civil Rights & Labor, Project Data Analytics, or an MDOT-specific
  endpoint?
- Does the accessible API expose a reference item catalog, contract project
  items, bid history, or only project-specific contract data?
- Can MDOT provide read-only credentials and test contract/project IDs?
- What source of truth should Field Guide use when the PDF and AASHTOWare item
  repository disagree?
- Should known-pay-item matching be stored as a confidence annotation, an import
  review issue, or both?
