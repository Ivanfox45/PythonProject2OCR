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
import io
import shutil
from pathlib import Path
from typing import List

import requests
from docx import Document
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance
import logging
import sys


def preprocess_image(path: Path, tmp_dir: Path) -> Path:
    """Improve image quality for OCR and save into *tmp_dir*.

    The image is upscaled, converted to grayscale and sharpened. The
    processed image is saved as JPEG in the temporary directory and its
    path is returned.
    """
    logging.info("Preprocessing %s", path)
    img = Image.open(path)

    if max(img.size) < 1000:
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
    logging.debug("Preprocessed image stored at %s", tmp_path)
    return tmp_path


def ocr_image(path: Path, iam_token: str, folder_id: str) -> str:
    """Send an image to the Yandex Vision API and return extracted text."""
    logging.info("Requesting OCR for %s", path)
    if path.stat().st_size > 1_000_000:
        logging.debug("Reducing size of %s before upload", path)
        img = Image.open(path)
        quality = 85
        while True:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=quality)
            if buf.tell() <= 1_000_000 or quality <= 30:
                break
            quality -= 5
        with open(path, "wb") as fh:
            fh.write(buf.getvalue())

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

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception:
        logging.exception("HTTP request failed for %s", path)
        return "[request error]"
    if resp.status_code != 200:
        logging.error(
            "Yandex API returned %s for %s: %s",
            resp.status_code,
            path,
            resp.text.strip(),
        )
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
        logging.exception("Failed to extract text for %s", path)
        return "[text extraction error]"


def resolve_input(path: Path) -> Path:
    """Return an existing *Path* for ``path``.

    If *path* does not exist and refers only to a file or directory name
    (without any parent components), the current working directory is
    searched recursively for a matching entry. This avoids an expensive
    recursive search when a full path is provided but does not exist.
    """

    if path.exists():
        return path

    # Only search the current directory tree when the user supplied just a
    # name (no parent directories). This prevents a long scan when an
    # absolute or relative path is wrong or contains drive letters/quotes.
    if len(path.parts) == 1:
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
        logging.info("Input is a single file: %s", path)
        return [path]

    logging.info("Searching for files under %s", path)
    exts = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
    files = [p for p in path.rglob("*") if p.suffix.lower() in exts]
    logging.info("Found %d files", len(files))
    return files


def process_file(input_file: Path, output_docx: Path, tmp_dir: Path, iam_token: str, folder_id: str) -> None:
    """Process *input_file* and save the recognised text to *output_docx*."""
    logging.info("Processing file %s", input_file)
    images: List[Path] = []

    if input_file.suffix.lower() == ".pdf":
        logging.info("Splitting PDF %s", input_file)
        for i, page in enumerate(convert_from_path(str(input_file), dpi=300), start=1):
            img_path = tmp_dir / f"page_{i}.png"
            page.save(img_path, "PNG")
            images.append(preprocess_image(img_path, tmp_dir))
    else:
        images.append(preprocess_image(input_file, tmp_dir))

    document = Document()
    total = len(images)
    for i, img in enumerate(images, start=1):
        logging.info("OCR %s page %d/%d", input_file.name, i, total)
        text = ocr_image(img, iam_token, folder_id)
        document.add_heading(f"Page {i}", level=2)
        document.add_paragraph(text or "[no text]")
        print(f"\r{input_file.name}: {i}/{total} pages processed", end="", flush=True)

    print()
    output_docx.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_docx)
    logging.info("Saved DOCX to %s", output_docx)
    shutil.rmtree(tmp_dir, ignore_errors=True)


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


def collect_gui_args(args: argparse.Namespace) -> argparse.Namespace:
    """Collect missing arguments using a simple Tk based GUI."""
    import tkinter as tk
    from tkinter import filedialog, simpledialog

    root = tk.Tk()
    root.withdraw()

    if args.input_path is None:
        path_str = filedialog.askdirectory(title="Select directory with files")
        if not path_str:
            path_str = filedialog.askopenfilename(title="Select image or PDF")
        if not path_str:
            raise SystemExit("No input selected")
        args.input_path = Path(path_str)

    if args.output_dir == Path("result"):
        out_dir = filedialog.askdirectory(title="Select output directory")
        if out_dir:
            args.output_dir = Path(out_dir)

    if not args.iam_token:
        args.iam_token = simpledialog.askstring(
            "IAM token", "Enter Yandex IAM token", show="*"
        ) or ""

    if not args.folder_id:
        args.folder_id = simpledialog.askstring(
            "Folder ID", "Enter Yandex folder ID"
        ) or ""

    root.destroy()
    return args


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)
    args = parse_args()

    # When any of the required parameters are missing, request them via GUI
    if (
        args.input_path is None
        or not args.iam_token
        or not args.folder_id
    ):
        args = collect_gui_args(args)

    try:
        files = find_input_files(args.input_path)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc))
    if not files:
        raise SystemExit("No input files found")

    for idx, file in enumerate(files, start=1):
        logging.info("Processing file %d/%d", idx, len(files))
        tmp_dir = args.tmp_dir / file.stem
        output_docx = args.output_dir / file.stem / f"{file.stem}.docx"
        try:
            process_file(file, output_docx, tmp_dir, args.iam_token, args.folder_id)
            logging.info("Saved OCR result for %s to %s", file, output_docx)
        except Exception:
            logging.exception("Failed to process %s", file)


if __name__ == "__main__":
    main()
