#!/usr/bin/env python3
"""Extract form field information from a PDF."""

import json
import sys
from pypdf import PdfReader


def extract_form_field_info(pdf_path: str) -> dict:
    """
    Extract detailed information about all form fields in a PDF.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary mapping field names to their properties
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()

    if not fields:
        return {}

    field_info = {}

    for field_name, field_obj in fields.items():
        info = {
            "type": str(field_obj.get("/FT", "Unknown")),
            "value": None,
            "default_value": None,
            "rect": None,
            "page": None,
            "flags": None,
            "options": None,
        }

        # Get field type
        ft = field_obj.get("/FT")
        if ft:
            type_map = {
                "/Tx": "text",
                "/Btn": "button",  # checkbox or radio
                "/Ch": "choice",   # dropdown or listbox
                "/Sig": "signature"
            }
            info["type"] = type_map.get(str(ft), str(ft))

        # Get current value
        if "/V" in field_obj:
            v = field_obj["/V"]
            if hasattr(v, "get_object"):
                v = v.get_object()
            info["value"] = str(v) if v else None

        # Get default value
        if "/DV" in field_obj:
            dv = field_obj["/DV"]
            if hasattr(dv, "get_object"):
                dv = dv.get_object()
            info["default_value"] = str(dv) if dv else None

        # Get rectangle (position)
        if "/Rect" in field_obj:
            rect = field_obj["/Rect"]
            if hasattr(rect, "get_object"):
                rect = rect.get_object()
            info["rect"] = [float(x) for x in rect]

        # Get flags
        if "/Ff" in field_obj:
            info["flags"] = int(field_obj["/Ff"])

        # Get options for choice fields
        if "/Opt" in field_obj:
            opts = field_obj["/Opt"]
            if hasattr(opts, "get_object"):
                opts = opts.get_object()
            info["options"] = [str(o) for o in opts]

        # Try to determine page number
        if "/P" in field_obj:
            page_ref = field_obj["/P"]
            for i, page in enumerate(reader.pages):
                if page.indirect_reference == page_ref:
                    info["page"] = i + 1
                    break

        field_info[field_name] = info

    return field_info


def main():
    if len(sys.argv) not in [2, 3]:
        print("Usage: extract_form_field_info.py <pdf_path> [output.json]")
        print("\nExtract form field information from a PDF.")
        print("If output.json is not specified, prints to stdout.")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) == 3 else None

    try:
        field_info = extract_form_field_info(pdf_path)

        if not field_info:
            print("No form fields found in PDF.", file=sys.stderr)
            sys.exit(1)

        output = json.dumps(field_info, indent=2, default=str)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(output)
            print(f"Extracted {len(field_info)} fields to {output_path}")
        else:
            print(output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
