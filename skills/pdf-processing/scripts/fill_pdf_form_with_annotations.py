#!/usr/bin/env python3
"""Fill PDF forms using annotations (for non-fillable PDFs)."""

import json
import sys
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)


def create_text_annotation(text: str, rect: list, font_size: int = 10) -> DictionaryObject:
    """
    Create a FreeText annotation for adding text to a PDF.

    Args:
        text: Text to display
        rect: [x1, y1, x2, y2] position
        font_size: Font size in points

    Returns:
        Annotation dictionary object
    """
    return DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/FreeText"),
        NameObject("/Rect"): ArrayObject([
            FloatObject(rect[0]),
            FloatObject(rect[1]),
            FloatObject(rect[2]),
            FloatObject(rect[3]),
        ]),
        NameObject("/Contents"): TextStringObject(text),
        NameObject("/DA"): TextStringObject(f"/Helv {font_size} Tf 0 0 0 rg"),
        NameObject("/F"): NumberObject(4),  # Print flag
        NameObject("/Q"): NumberObject(0),  # Left align
    })


def fill_with_annotations(
    input_path: str,
    output_path: str,
    positions: dict,
    data: dict,
    font_size: int = 10
) -> int:
    """
    Fill a PDF using FreeText annotations.

    Args:
        input_path: Path to input PDF
        output_path: Path for output PDF
        positions: Dict mapping field names to position info
        data: Dict mapping field names to values
        font_size: Default font size

    Returns:
        Number of annotations added
    """
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Copy all pages
    for page in reader.pages:
        writer.add_page(page)

    annotations_added = 0

    for field_name, value in data.items():
        if field_name not in positions:
            print(f"Warning: No position defined for '{field_name}'", file=sys.stderr)
            continue

        pos = positions[field_name]
        page_num = pos.get("page", 1) - 1  # Convert to 0-indexed

        if page_num < 0 or page_num >= len(writer.pages):
            print(f"Warning: Invalid page {page_num + 1} for '{field_name}'", file=sys.stderr)
            continue

        # Get position
        x = pos.get("x", 0)
        y = pos.get("y", 0)
        width = pos.get("width", 200)
        height = pos.get("height", 20)
        field_font_size = pos.get("font_size", font_size)

        # Create rect [x1, y1, x2, y2]
        rect = [x, y, x + width, y + height]

        # Create annotation
        annotation = create_text_annotation(str(value), rect, field_font_size)

        # Add to page
        page = writer.pages[page_num]
        if "/Annots" not in page:
            page[NameObject("/Annots")] = ArrayObject()

        page["/Annots"].append(annotation)
        annotations_added += 1

    # Write output
    with open(output_path, 'wb') as f:
        writer.write(f)

    return annotations_added


def main():
    if len(sys.argv) not in [5, 6]:
        print("Usage: fill_pdf_form_with_annotations.py <input.pdf> <output.pdf> <positions.json> <data.json> [font_size]")
        print("\nFill a PDF using FreeText annotations (for non-fillable PDFs).")
        print("\npositions.json format:")
        print('''{
  "field_name": {
    "page": 1,
    "x": 150,
    "y": 200,
    "width": 300,
    "height": 20,
    "font_size": 10  // optional
  }
}''')
        print("\ndata.json format:")
        print('  {"field_name": "value", ...}')
        print("\nOptional: font_size (default: 10)")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    positions_path = sys.argv[3]
    data_path = sys.argv[4]
    font_size = int(sys.argv[5]) if len(sys.argv) == 6 else 10

    try:
        with open(positions_path, 'r') as f:
            positions = json.load(f)

        with open(data_path, 'r') as f:
            data = json.load(f)

        if not isinstance(positions, dict) or not isinstance(data, dict):
            print("Error: Both JSON files must contain objects", file=sys.stderr)
            sys.exit(1)

        added = fill_with_annotations(input_path, output_path, positions, data, font_size)
        print(f"Added {added} annotations, saved to {output_path}")

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
