# OCR Layout Review PDF Corpus

Created: 2026-04-15

This folder keeps the PDFs reviewed during the Google-assisted OCR source
research loop in one durable Claude asset location. The files are grouped by
layout family so OCR/table experiments can target the correct geometry instead
of assuming all pay-item PDFs are boxed grids.

## Layout Types

- `municipal_bid_forms/`: boxed municipal bid-form tables with visible row and
  column rules.
- `mdot_schedule_of_items/`: AASHTOWare Schedule of Items tables with stable
  columns and zebra/gray row bands, but no full vertical grid.
- `mdot_bid_tabs/`: AASHTOWare bid-tab pages with bidder price groups, gray row
  bands, some vertical separators, and two-line item records.

## Files

- `municipal_bid_forms/berrien_127449_pay_items.pdf`
- `municipal_bid_forms/springfield_864130_pay_items.pdf`
- `municipal_bid_forms/huron_valley_917245_pay_items.pdf`
- `municipal_bid_forms/grand_blanc_938710_pay_items.pdf`
- `municipal_bid_forms/external_indot_r45446a_request_schedule_pay_items.pdf`
- `mdot_schedule_of_items/mdot_2026-04-03_estqua_schedule_sample_pages_001_025.pdf`
- `mdot_schedule_of_items/external_mdot_2025-02-07_estqua.pdf`
- `mdot_schedule_of_items/external_mdot_2025-02-07_estqua_pages_001_010.pdf`
- `mdot_bid_tabs/mdot_2026-03-06_26-03002_bid_tab_by_item.pdf`
- `mdot_bid_tabs/mdot_2026-04-03_26-04001_bid_tab_by_item.pdf`
- `mdot_bid_tabs/external_mdot_2025-02-07_25-02001_bid_tab_by_item.pdf`
- `mdot_bid_tabs/external_mdot_2025-02-07_25-02001_bid_tab_pages_002_010.pdf`

## External Validation Candidates

Added 2026-04-15 for the post-100% generalization check:

- INDOT R-45446-A request schedule/pay-items PDF:
  `https://www.in.gov/idoa/mwbe/files/R-45446-A%2C-Request.pdf`
- MDOT 2025-02-07 AASHTOWare Schedule of Pay Items:
  `https://mdotjboss.state.mi.us/BidLetting/getFileByName.htm?fileName=2025-02-07%2Festqua.pdf`
- MDOT 2025-02-07 25-02001 AASHTOWare bid-tab-by-item PDF:
  `https://mdotjboss.state.mi.us/BidLetting/getFileByName.htm?fileName=2025-02-07%2F25-02001.pdf`

The `external_*_pages_*` files are page-window derivatives used to keep
pipeline validation focused and fast. The matching full source PDFs are kept in
the same layout-family folders when the source document is larger than the
validation window.
