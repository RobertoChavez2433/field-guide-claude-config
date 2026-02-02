#!/usr/bin/env python3
"""Convert PDF pages to images for visual analysis."""

import os
import sys

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False

# Fallback using pypdf and PIL for basic rendering
from pypdf import PdfReader
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def convert_with_pdf2image(pdf_path: str, output_dir: str, dpi: int = 200) -> list:
    """
    Convert PDF to images using pdf2image (requires Poppler).

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save images
        dpi: Resolution in dots per inch

    Returns:
        List of saved image paths
    """
    os.makedirs(output_dir, exist_ok=True)

    images = convert_from_path(pdf_path, dpi=dpi)
    saved_paths = []

    for i, image in enumerate(images, 1):
        output_path = os.path.join(output_dir, f"page_{i}.png")
        image.save(output_path, "PNG")
        saved_paths.append(output_path)
        print(f"Saved: {output_path}")

    return saved_paths


def convert_basic(pdf_path: str, output_dir: str) -> list:
    """
    Basic PDF info extraction when pdf2image isn't available.
    Creates a text file with page info instead of images.

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save info

    Returns:
        List of saved file paths
    """
    os.makedirs(output_dir, exist_ok=True)

    reader = PdfReader(pdf_path)
    saved_paths = []

    for i, page in enumerate(reader.pages, 1):
        output_path = os.path.join(output_dir, f"page_{i}_info.txt")

        with open(output_path, 'w') as f:
            f.write(f"Page {i}\n")
            f.write("=" * 40 + "\n\n")

            # Get page dimensions
            mediabox = page.mediabox
            f.write(f"Dimensions: {float(mediabox.width)} x {float(mediabox.height)} points\n")
            f.write(f"            {float(mediabox.width) / 72:.2f} x {float(mediabox.height) / 72:.2f} inches\n\n")

            # Extract text
            text = page.extract_text()
            f.write("Text Content:\n")
            f.write("-" * 40 + "\n")
            f.write(text if text else "(No text extracted)")

        saved_paths.append(output_path)
        print(f"Saved: {output_path}")

    return saved_paths


def main():
    if len(sys.argv) not in [3, 4]:
        print("Usage: convert_pdf_to_images.py <pdf_path> <output_dir> [dpi]")
        print("\nConvert PDF pages to PNG images for visual analysis.")
        print("\nOptional: dpi (default: 200)")
        print("\nNote: Requires Poppler for full image conversion.")
        print("      Install on Windows: https://github.com/oschwartz10612/poppler-windows/releases")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_dir = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) == 4 else 200

    try:
        if HAS_PDF2IMAGE:
            saved = convert_with_pdf2image(pdf_path, output_dir, dpi)
            print(f"\nConverted {len(saved)} pages to images")
        else:
            print("Warning: pdf2image not available, extracting text info instead", file=sys.stderr)
            print("Install pdf2image and Poppler for full image conversion", file=sys.stderr)
            saved = convert_basic(pdf_path, output_dir)
            print(f"\nExtracted info for {len(saved)} pages")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if "poppler" in str(e).lower():
            print("\nPoppler is required for PDF to image conversion.", file=sys.stderr)
            print("Install on Windows: https://github.com/oschwartz10612/poppler-windows/releases", file=sys.stderr)
            print("Then add to PATH: C:\\Program Files\\poppler\\bin", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
