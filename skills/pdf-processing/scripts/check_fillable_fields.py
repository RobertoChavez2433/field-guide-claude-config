#!/usr/bin/env python3
"""Check if a PDF has fillable form fields."""

import sys
from pypdf import PdfReader


def check_fillable_fields(pdf_path: str) -> bool:
    """
    Check if a PDF has fillable form fields.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        True if PDF has fillable fields, False otherwise
    """
    try:
        reader = PdfReader(pdf_path)

        # Check for AcroForm (interactive form fields)
        if reader.get_fields():
            return True

        # Also check for form fields in pages
        for page in reader.pages:
            if "/Annots" in page:
                annotations = page["/Annots"]
                for annot in annotations:
                    annot_obj = annot.get_object()
                    if annot_obj.get("/Subtype") == "/Widget":
                        return True

        return False

    except Exception as e:
        print(f"Error reading PDF: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) != 2:
        print("Usage: check_fillable_fields.py <pdf_path>")
        print("\nCheck if a PDF has fillable form fields.")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if check_fillable_fields(pdf_path):
        print("This PDF has fillable form fields")

        # Print field count
        try:
            reader = PdfReader(pdf_path)
            fields = reader.get_fields()
            if fields:
                print(f"Total fields: {len(fields)}")
        except:
            pass
    else:
        print("This PDF does NOT have fillable form fields")


if __name__ == "__main__":
    main()
