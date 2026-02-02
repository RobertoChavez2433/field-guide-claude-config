#!/usr/bin/env python3
"""Create validation images showing filled field values in a PDF."""

import os
import sys
from pypdf import PdfReader

try:
    from pdf2image import convert_from_path
    from PIL import Image, ImageDraw
    HAS_IMAGING = True
except ImportError:
    HAS_IMAGING = False


def create_validation_images(pdf_path: str, output_dir: str, dpi: int = 150) -> list:
    """
    Create images with filled field values highlighted.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save images
        dpi: Resolution for PDF conversion

    Returns:
        List of saved image paths
    """
    if not HAS_IMAGING:
        raise ImportError("pdf2image and Pillow required for validation images")

    os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    fields = reader.get_fields() or {}

    # Find fields with values
    filled_fields = {}
    for field_name, field_obj in fields.items():
        value = None
        if "/V" in field_obj:
            v = field_obj["/V"]
            if hasattr(v, "get_object"):
                v = v.get_object()
            value = str(v) if v else None

        if value and "/Rect" in field_obj:
            rect = field_obj["/Rect"]
            if hasattr(rect, "get_object"):
                rect = rect.get_object()

            page_num = 1
            if "/P" in field_obj:
                page_ref = field_obj["/P"]
                for i, page in enumerate(reader.pages):
                    if page.indirect_reference == page_ref:
                        page_num = i + 1
                        break

            if page_num not in filled_fields:
                filled_fields[page_num] = []

            filled_fields[page_num].append({
                "name": field_name,
                "value": value,
                "rect": [float(x) for x in rect]
            })

    if not filled_fields:
        print("No filled fields found in PDF")
        return []

    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=dpi)
    saved_paths = []

    for i, (image, page) in enumerate(zip(images, reader.pages), 1):
        draw = ImageDraw.Draw(image)

        mediabox = page.mediabox
        pdf_width = float(mediabox.width)
        pdf_height = float(mediabox.height)
        img_width, img_height = image.size

        scale_x = img_width / pdf_width
        scale_y = img_height / pdf_height

        if i in filled_fields:
            for field in filled_fields[i]:
                x1, y1, x2, y2 = field["rect"]

                # Transform coordinates (PDF bottom-left to image top-left)
                img_x1 = x1 * scale_x
                img_y1 = (pdf_height - y2) * scale_y
                img_x2 = x2 * scale_x
                img_y2 = (pdf_height - y1) * scale_y

                # Draw green box for filled fields
                draw.rectangle([img_x1, img_y1, img_x2, img_y2], outline="green", width=3)

                # Show field name and value
                label = f"{field['name']}: {field['value'][:30]}"
                draw.text((img_x1, img_y1 - 20), label, fill="green")

        output_path = os.path.join(output_dir, f"page_{i}_validation.png")
        image.save(output_path, "PNG")
        saved_paths.append(output_path)
        print(f"Saved: {output_path}")

    # Create summary
    summary_path = os.path.join(output_dir, "validation_summary.txt")
    with open(summary_path, 'w') as f:
        f.write("Validation Summary\n")
        f.write("=" * 50 + "\n\n")

        total_filled = sum(len(fields) for fields in filled_fields.values())
        f.write(f"Total filled fields: {total_filled}\n\n")

        for page_num in sorted(filled_fields.keys()):
            f.write(f"Page {page_num}:\n")
            for field in filled_fields[page_num]:
                f.write(f"  - {field['name']}: {field['value']}\n")
            f.write("\n")

    print(f"Saved: {summary_path}")
    saved_paths.append(summary_path)

    return saved_paths


def main():
    if len(sys.argv) not in [3, 4]:
        print("Usage: create_validation_image.py <pdf_path> <output_dir> [dpi]")
        print("\nCreate images highlighting filled form fields for validation.")
        print("\nOptional: dpi (default: 150)")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) == 4 else 150

    try:
        if not HAS_IMAGING:
            print("Error: pdf2image and Pillow required", file=sys.stderr)
            print("Install with: pip install pdf2image Pillow", file=sys.stderr)
            sys.exit(1)

        saved = create_validation_images(pdf_path, output_dir, dpi)
        print(f"\nCreated {len(saved)} validation files")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
