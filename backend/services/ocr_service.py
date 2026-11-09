"""Tesseract OCR adapter for medicine packaging images."""

import io
import os
import shutil
from collections import defaultdict

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def configure_tesseract():
    """Find the Tesseract executable on Windows or Linux."""

    configured_path = os.getenv("TESSERACT_CMD")

    if configured_path:
        pytesseract.pytesseract.tesseract_cmd = configured_path
        return

    executable = shutil.which("tesseract")

    if executable:
        pytesseract.pytesseract.tesseract_cmd = executable
        return

    # Common Windows installation locations
    windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for path in windows_paths:
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return


def preprocess_image(image):
    """Prepare a medicine image to improve text recognition."""

    image = ImageOps.exif_transpose(image).convert("RGB")

    # Enlarge small images to make printed text easier to recognise.
    if image.width < 1800:
        scale = min(3, 1800 / image.width)
        new_size = (
            int(image.width * scale),
            int(image.height * scale),
        )
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)
    image = ImageEnhance.Contrast(image).enhance(1.5)
    image = image.filter(ImageFilter.SHARPEN)

    return image


def read_with_tesseract(image, page_mode):
    """Extract text and confidence values using a Tesseract page mode."""

    data = pytesseract.image_to_data(
        image,
        lang="eng",
        config=f"--oem 3 --psm {page_mode}",
        output_type=pytesseract.Output.DICT,
    )

    grouped_lines = defaultdict(list)
    word_confidences = []

    for index, word in enumerate(data["text"]):
        word = str(word).strip()

        if not word:
            continue

        try:
            confidence = float(data["conf"][index])
        except (ValueError, TypeError):
            continue

        if confidence < 0:
            continue

        line_key = (
            data["block_num"][index],
            data["par_num"][index],
            data["line_num"][index],
        )

        grouped_lines[line_key].append(word)
        word_confidences.append(confidence)

    lines = []

    for words in grouped_lines.values():
        line_text = " ".join(words).strip()

        if line_text:
            lines.append(line_text)

    average_confidence = (
        sum(word_confidences) / len(word_confidences)
        if word_confidences
        else 0
    )

    return {
        "text": "\n".join(lines),
        "lines": lines,
        "average_confidence": average_confidence,
        "word_count": len(word_confidences),
    }


def extract_text(image_bytes: bytes) -> dict:
    """Extract readable text from an uploaded medicine image."""

    try:
        configure_tesseract()

        # Check that the Tesseract executable is available.
        pytesseract.get_tesseract_version()

        if not image_bytes:
            return {
                "text": "",
                "lines": [],
                "engine": "Tesseract",
                "warning": "The uploaded image is empty.",
            }

        image = Image.open(io.BytesIO(image_bytes))
        image.load()

        processed_image = preprocess_image(image)

        # Try two layouts because medicine packaging can have
        # paragraphs, columns, and separately positioned text.
        results = [
            read_with_tesseract(processed_image, 6),
            read_with_tesseract(processed_image, 11),
        ]

        best_result = max(
            results,
            key=lambda result: (
                result["average_confidence"],
                result["word_count"],
            ),
        )

        extracted_text = best_result["text"]

        if not extracted_text.strip():
            return {
                "text": "",
                "lines": [],
                "engine": "Tesseract",
                "warning": (
                    "No readable text was found. Try uploading a clearer, "
                    "well-lit image with the medicine label facing the camera."
                ),
            }

        lines = [
            {
                "text": line,
                "confidence": round(
                    best_result["average_confidence"] / 100, 3
                ),
            }
            for line in best_result["lines"]
        ]

        return {
            "text": extracted_text,
            "lines": lines,
            "engine": "Tesseract",
            "warning": (
                "OCR text may contain mistakes. Review the extracted "
                "medicine name, ingredients, and strengths before analysis."
            ),
        }

    except pytesseract.pytesseract.TesseractNotFoundError:
        return {
            "text": "",
            "lines": [],
            "engine": "unavailable",
            "warning": (
                "Tesseract OCR is not installed or its executable "
                "could not be found. Install Tesseract and configure its path."
            ),
        }

    except Exception as exc:
        return {
            "text": "",
            "lines": [],
            "engine": "Tesseract",
            "warning": f"OCR could not read this image: {exc}",
        }