#!/usr/bin/env python3
"""Fill fillable form fields in a PDF."""

import json
import sys
from pypdf import PdfReader, PdfWriter


def fill_fillable_fields(input_path: str, output_path: str, data: dict) -> int:
    """
    Fill fillable form fields in a PDF.

    Args:
        input_path: Path to input PDF
        output_path: Path for output PDF
        data: Dictionary mapping field names to values

    Returns:
        Number of fields filled
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Copy all pages
    for page in reader.pages:
        writer.add_page(page)

    # Copy metadata if present
    if reader.metadata:
        writer.add_metadata(reader.metadata)

    # Fill form fields
    fields_filled = 0

    for field_name, value in data.items():
        try:
            writer.update_page_form_field_values(
                writer.pages[0],  # Will update across all pages
                {field_name: value}
            )
            fields_filled += 1
        except Exception as e:
            print(f"Warning: Could not fill field '{field_name}': {e}", file=sys.stderr)

    # Write output
    with open(output_path, 'wb') as f:
        writer.write(f)

    return fields_filled


def main():
    if len(sys.argv) != 4:
        print("Usage: fill_fillable_fields.py <input.pdf> <output.pdf> <data.json>")
        print("\nFill fillable form fields in a PDF.")
        print("\ndata.json format:")
        print('  {"field_name": "value", ...}')
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    data_path = sys.argv[3]

    try:
        with open(data_path, 'r') as f:
            data = json.load(f)

        if not isinstance(data, dict):
            print("Error: data.json must contain a JSON object", file=sys.stderr)
            sys.exit(1)

        fields_filled = fill_fillable_fields(input_path, output_path, data)
        print(f"Filled {fields_filled} fields, saved to {output_path}")

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
