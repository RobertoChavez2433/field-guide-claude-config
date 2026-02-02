#!/usr/bin/env python3
"""Check and visualize form field bounding boxes in a PDF."""

import os
import sys
import json
from pypdf import PdfReader

try:
    from pdf2image import convert_from_path
    from PIL import Image, ImageDraw, ImageFont
    HAS_IMAGING = True
except ImportError:
    HAS_IMAGING = False


def get_field_boxes(pdf_path: str) -> dict:
    """
    Extract bounding boxes for all form fields.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary mapping page numbers to lists of field info
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()

    if not fields:
        return {}

    page_fields = {}

    for field_name, field_obj in fields.items():
        if "/Rect" not in field_obj:
            continue

        rect = field_obj["/Rect"]
        if hasattr(rect, "get_object"):
            rect = rect.get_object()
        rect = [float(x) for x in rect]

        # Determine page number
        page_num = 1
        if "/P" in field_obj:
            page_ref = field_obj["/P"]
            for i, page in enumerate(reader.pages):
                if page.indirect_reference == page_ref:
                    page_num = i + 1
                    break

        if page_num not in page_fields:
            page_fields[page_num] = []

        page_fields[page_num].append({
            "name": field_name,
            "rect": rect,  # [x1, y1, x2, y2] in PDF coordinates (bottom-left origin)
        })

    return page_fields


def visualize_boxes(pdf_path: str, output_dir: str, dpi: int = 150) -> list:
    """
    Create images with field bounding boxes drawn.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save images
        dpi: Resolution for PDF conversion

    Returns:
        List of saved image paths
    """
    if not HAS_IMAGING:
        raise ImportError("pdf2image and Pillow required for visualization")

    os.makedirs(output_dir, exist_ok=True)

    # Get field bounding boxes
    page_fields = get_field_boxes(pdf_path)

    if not page_fields:
        print("No form fields with bounding boxes found")
        return []

    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=dpi)

    # Get PDF page dimensions for coordinate conversion
    reader = PdfReader(pdf_path)
    saved_paths = []

    for i, (image, page) in enumerate(zip(images, reader.pages), 1):
        draw = ImageDraw.Draw(image)

        # Get page dimensions for coordinate conversion
        mediabox = page.mediabox
        pdf_width = float(mediabox.width)
        pdf_height = float(mediabox.height)
        img_width, img_height = image.size

        # Scale factors
        scale_x = img_width / pdf_width
        scale_y = img_height / pdf_height

        if i in page_fields:
            for field in page_fields[i]:
                # Convert PDF coordinates (bottom-left origin) to image coordinates (top-left origin)
                x1, y1, x2, y2 = field["rect"]

                # Transform coordinates
                img_x1 = x1 * scale_x
                img_y1 = (pdf_height - y2) * scale_y  # Flip Y
                img_x2 = x2 * scale_x
                img_y2 = (pdf_height - y1) * scale_y  # Flip Y

                # Draw rectangle
                draw.rectangle([img_x1, img_y1, img_x2, img_y2], outline="red", width=2)

                # Draw field name (truncated if too long)
                name = field["name"][:20] + "..." if len(field["name"]) > 20 else field["name"]
                draw.text((img_x1, img_y1 - 15), name, fill="red")

        output_path = os.path.join(output_dir, f"page_{i}_boxes.png")
        image.save(output_path, "PNG")
        saved_paths.append(output_path)
        print(f"Saved: {output_path}")

    return saved_paths


def main():
    if len(sys.argv) not in [2, 3, 4]:
        print("Usage: check_bounding_boxes.py <pdf_path> [output_dir] [dpi]")
        print("\nVisualize form field bounding boxes in a PDF.")
        print("\nWithout output_dir: prints field info as JSON")
        print("With output_dir: creates annotated images")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) >= 3 else None
    dpi = int(sys.argv[3]) if len(sys.argv) == 4 else 150

    try:
        if output_dir:
            if not HAS_IMAGING:
                print("Error: pdf2image and Pillow required for visualization", file=sys.stderr)
                print("Install with: pip install pdf2image Pillow", file=sys.stderr)
                print("\nFalling back to JSON output...\n", file=sys.stderr)
                page_fields = get_field_boxes(pdf_path)
                print(json.dumps(page_fields, indent=2))
            else:
                saved = visualize_boxes(pdf_path, output_dir, dpi)
                print(f"\nCreated {len(saved)} annotated images")
        else:
            page_fields = get_field_boxes(pdf_path)
            print(json.dumps(page_fields, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
