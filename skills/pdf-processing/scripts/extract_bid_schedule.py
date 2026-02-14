#!/usr/bin/env python3
"""
Extract bid schedule data from Springfield PDF.
Outputs JSON with all bid items.
"""

import sys
import json
import re
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


def parse_currency(value):
    """Parse currency string to float."""
    if not value or value.strip() == '':
        return None
    # Remove $, commas, and spaces
    cleaned = re.sub(r'[$,\s]', '', str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_quantity(value):
    """Parse quantity string to float."""
    if not value or value.strip() == '':
        return None
    # Remove commas and spaces
    cleaned = re.sub(r'[,\s]', '', str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_bid_items(pdf_path):
    """Extract all bid items from the PDF."""
    items = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue

            lines = text.split('\n')

            for line in lines:
                # Skip header lines and empty lines
                if not line.strip() or 'Item #' in line or 'Description' in line:
                    continue

                # Try to parse as a bid item line
                # Pattern: Item# Description Unit Quantity UnitPrice Amount
                parts = line.split()

                if len(parts) >= 6:
                    # Check if first part looks like an item number
                    item_num = parts[0].strip()
                    if item_num.replace('.', '').isdigit() or item_num.isdigit():
                        # Last 3 parts should be quantity, unit_price, bid_amount
                        raw_amount = parts[-1]
                        raw_unit_price = parts[-2]
                        raw_quantity = parts[-3]

                        # Unit is before quantity
                        unit_idx = len(parts) - 4
                        raw_unit = parts[unit_idx] if unit_idx >= 1 else ''

                        # Description is everything between item number and unit
                        raw_description = ' '.join(parts[1:unit_idx]).strip()

                        # Parse numeric values
                        quantity = parse_quantity(raw_quantity)
                        unit_price = parse_currency(raw_unit_price)
                        bid_amount = parse_currency(raw_amount)

                        # Count fields present
                        fields_present = sum([
                            bool(item_num),
                            bool(raw_description),
                            bool(raw_unit),
                            quantity is not None,
                            unit_price is not None,
                            bid_amount is not None
                        ])

                        item = {
                            "item_number": item_num,
                            "description": raw_description,
                            "unit": raw_unit,
                            "quantity": quantity,
                            "unit_price": unit_price,
                            "bid_amount": bid_amount,
                            "confidence": 0.95,
                            "fields_present": fields_present,
                            "raw_item_number": item_num,
                            "raw_description": raw_description,
                            "raw_unit": raw_unit,
                            "raw_quantity": raw_quantity,
                            "raw_unit_price": raw_unit_price,
                            "raw_bid_amount": raw_amount
                        }

                        items.append(item)

    return items


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_bid_schedule.py <pdf_path> [output_json]", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    items = extract_bid_items(pdf_path)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2)
        print(f"Extracted {len(items)} items to {output_path}")
    else:
        print(json.dumps(items, indent=2))

    return 0


if __name__ == '__main__':
    sys.exit(main())
