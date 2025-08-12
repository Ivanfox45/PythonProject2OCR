"""Utility for performing OCR using Yandex Cloud Vision API.

The script accepts an input image, PDF or a directory containing such
files, sends each page to the Yandex Cloud Vision API and saves the
recognised text into separate DOCX files.

Usage:
    python yandex_ocr.py [INPUT_PATH] [--output-dir DIR]

The IAM token and folder ID are read from the environment variables
`YANDEX_IAM_TOKEN` and `YANDEX_FOLDER_ID` respectively. If any of these
values or the input path are missing, the script will ask for them
interactively when run.
"""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
from typing import List

import requests
from docx import Document
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance


def preprocess_image(path: Path, tmp_dir: Path) -> Path:
    """Improve image quality for OCR and save into *tmp_dir*.

    The image is upscaled, converted to grayscale and sharpened. The
    processed image is saved as JPEG in the temporary directory and its
    path is returned.
    """
    img = Image.open(path)

    # upscale ×2 for better quality
    new_size = (img.width * 2, img.height * 2)
    img = img.resize(new_size, Image.LANCZOS)

    # convert to 8‑bit grayscale
    img = img.convert("L")

    # increase contrast and sharpness
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    # light binarisation (keep as grayscale)
    img = img.point(lambda x: 0 if x < 140 else 255, "L")

    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{path.stem}.jpg"
    img.save(tmp_path, "JPEG", quality=90)
    return tmp_path


def ocr_image(path: Path, iam_token: str, folder_id: str) -> str:
    """Send an image to the Yandex Vision API and return extracted text."""
    if path.stat().st_size > 4_000_000:  # compress large images
        img = Image.open(path)
        img.save(path, "JPEG", quality=80)

    with open(path, "rb") as fh:
        img_base64 = base64.b64encode(fh.read()).decode("utf-8")

    url = "https://vision.api.cloud.yandex.net/vision/v1/batchAnalyze"
    headers = {"Authorization": f"Bearer {iam_token}", "Content-Type": "application/json"}
    payload = {
        "folderId": folder_id,
        "analyze_specs": [
            {
                "content": img_base64,
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }
        ],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        return f"[error {resp.status_code}]"

    try:
        result = resp.json()
        pages = result["results"][0]["results"][0]["textDetection"]["pages"]
        text = []
        for page in pages:
            for block in page.get("blocks", []):
                for line in block.get("lines", []):
                    words = [word.get("text", "") for word in line.get("words", [])]
                    text.append(" ".join(words))
        return "\n".join(text).strip()
    except Exception:
        return "[text extraction error]"


def resolve_input(path: Path) -> Path:
    """Return an existing *Path* for ``path``.

    If *path* does not exist, the current working directory is searched
    recursively for a file or directory with the same name.
    """

    if path.exists():
        return path
    matches = list(Path.cwd().rglob(path.name))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"Input path '{path}' not found")


def find_input_files(path: Path) -> List[Path]:
    """Return a list of image/PDF files found under *path*.

    *path* may point directly to a file or to a directory. Supported file
    extensions are PDF and common image formats.
    """

    path = resolve_input(path)
    if path.is_file():
        return [path]

    exts = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    return [p for p in path.rglob("*") if p.suffix.lower() in exts]


def process_file(input_file: Path, output_docx: Path, tmp_dir: Path, iam_token: str, folder_id: str) -> None:
    """Process *input_file* and save the recognised text to *output_docx*."""
    images: List[Path] = []

    if input_file.suffix.lower() == ".pdf":
        for i, page in enumerate(convert_from_path(str(input_file), dpi=300), start=1):
            img_path = tmp_dir / f"page_{i}.png"
            page.save(img_path, "PNG")
            images.append(preprocess_image(img_path, tmp_dir))
    else:
        images.append(preprocess_image(input_file, tmp_dir))

    document = Document()
    for i, img in enumerate(images, start=1):
        text = ocr_image(img, iam_token, folder_id)
        document.add_heading(f"Page {i}", level=2)
        document.add_paragraph(text or "[no text]")

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_docx)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OCR using Yandex Cloud Vision API")
    parser.add_argument(
        "input_path",
        nargs="?",
        type=Path,
        help="Path to image/PDF or directory with files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("result"),
        help="Directory to save result DOCX files",
    )
    parser.add_argument(
        "--tmp-dir",
        type=Path,
        default=Path("result") / "tmp",
        help="Temporary directory base",
    )
    parser.add_argument(
        "--iam-token",
        default=os.getenv("YANDEX_IAM_TOKEN"),
        help="Yandex IAM token",
    )
    parser.add_argument(
        "--folder-id",
        default=os.getenv("YANDEX_FOLDER_ID"),
        help="Yandex Cloud folder ID",
    )
    return parser.parse_args()


def prompt_missing(value: str | None, prompt: str, secret: bool = False) -> str:
    """Return *value* or interactively ask the user for it."""
    if value:
        return value
    if secret:
        import getpass

        return getpass.getpass(prompt)
    return input(prompt).strip()


def main() -> None:
    args = parse_args()

    if args.input_path is None:
        path_str = prompt_missing(None, "Enter path to image/PDF or directory: ")
        args.input_path = Path(path_str or ".")

    args.iam_token = prompt_missing(args.iam_token, "Enter Yandex IAM token: ", secret=True)
    args.folder_id = prompt_missing(args.folder_id, "Enter Yandex folder ID: ")

    files = find_input_files(args.input_path)
    if not files:
        raise SystemExit("No input files found")

    for file in files:
        tmp_dir = args.tmp_dir / file.stem
        output_docx = args.output_dir / file.stem / f"{file.stem}.docx"
        process_file(file, output_docx, tmp_dir, args.iam_token, args.folder_id)
        print(f"Saved OCR result for {file} to {output_docx}")


if __name__ == "__main__":
    main()
