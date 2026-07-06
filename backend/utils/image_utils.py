from pathlib import Path
from pdf2image import convert_from_path
import os

def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200) -> list[Path]:
    """Convert each page of a PDF to a PNG image.
    Returns a list of absolute paths to the generated PNG files.
    The function creates ``output_dir`` if it does not exist.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    # ``convert_from_path`` returns a list of PIL.Image objects.
    images = convert_from_path(str(pdf_path), dpi=dpi, fmt="png")
    image_paths: list[Path] = []
    for i, img in enumerate(images, start=1):
        img_path = output_dir / f"page_{i:03d}.png"
        img.save(img_path, "PNG")
        image_paths.append(img_path)
    return image_paths
