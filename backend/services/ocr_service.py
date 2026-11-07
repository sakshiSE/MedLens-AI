"""OCR adapter. EasyOCR is optional at import time to keep the API startable."""
from PIL import Image, ImageEnhance, ImageFilter
import io

_reader = None


def extract_text(image_bytes: bytes) -> dict:
    global _reader
    try:
        import easyocr
        if _reader is None:
            _reader = easyocr.Reader(["en"], gpu=False)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image = ImageEnhance.Contrast(image).enhance(1.35).filter(ImageFilter.SHARPEN)
        results = _reader.readtext(__import__("numpy").array(image), detail=1)
        lines = [{"text": str(row[1]), "confidence": round(float(row[2]), 3)} for row in results]
        return {"text": "\n".join(x["text"] for x in lines), "lines": lines,
                "engine": "EasyOCR", "warning": "OCR text can be inaccurate. Review and correct it before analysis."}
    except ImportError:
        return {"text": "", "lines": [], "engine": "unavailable",
                "warning": "EasyOCR is not installed. Install backend requirements, then retry."}
    except Exception as exc:
        return {"text": "", "lines": [], "engine": "EasyOCR", "warning": f"OCR could not read this image: {exc}"}
