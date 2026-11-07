"""PDF export for a completed analysis."""
from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape


def make_pdf(report: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet(); story = [Paragraph("MedLens AI — Medicine Information Report", styles["Title"]), Spacer(1, 14)]
    image_data = report.get("image_data", "")
    if image_data.startswith("data:image/") and "," in image_data:
        try:
            raw_image = base64.b64decode(image_data.split(",", 1)[1])
            story += [Image(BytesIO(raw_image), width=150, height=105, kind="proportional"), Spacer(1, 10)]
        except Exception:
            story.append(Paragraph("Uploaded image could not be embedded in this PDF.", styles["Italic"]))
    for heading, value in [("Medicine match", report.get("medicine_name", "Not identified")),
                           ("Extracted fields", report.get("extracted_fields", {})),
                           ("Extracted text", report.get("ocr_text", "")),
                           ("Health conditions", report.get("conditions", [])),
                           ("Current medications", report.get("medications", [])),
                           ("Known allergies (not screened against a local allergy dataset)", report.get("allergies", [])),
                           ("Ingredients", ", ".join(report.get("ingredients", []))),
                           ("Precautions", str(report.get("precautions", []))),
                           ("Interaction screen", str(report.get("interactions", {}))),
                           ("Evidence", str(report.get("evidence", []))),
                           ("Uncertainty", str(report.get("uncertainties", [])))]:
        story += [Paragraph(heading, styles["Heading2"]), Paragraph(escape(str(value)), styles["BodyText"]), Spacer(1, 8)]
    story += [Spacer(1, 12), Paragraph("Educational prototype only. Not a diagnosis or clinical decision-support tool. Consult a qualified doctor or pharmacist. Do not start, stop, or change medicines based on this report.", styles["Italic"])]
    doc.build(story); return buffer.getvalue()
