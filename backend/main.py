"""FastAPI entry point for MedLens AI."""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from pathlib import Path
import json
from backend.config import MAX_UPLOAD_MB
from backend.services.ocr_service import extract_text
from backend.services.medicine_service import identify_medicine, extract_medicine_information, check_condition_precautions, check_supported_interactions
from backend.rag.retriever import retrieve_medical_evidence
from backend.agent.coordinator import run_agent
from backend.services.report_service import make_pdf

app = FastAPI(title="MedLens AI API", version="1.0.0", description="Educational medicine label information prototype")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class AnalysisRequest(BaseModel):
    ocr_text: str = Field(min_length=2, max_length=12000)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    confirmed_medicine: str | None = None

@app.get("/api/health")
def health(): return {"status": "ok", "service": "MedLens AI"}

@app.post("/api/ocr")
async def ocr(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(400, "Upload a JPG, JPEG or PNG image.")
    content = await file.read()
    if not content or len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(400, f"Image must be non-empty and no larger than {MAX_UPLOAD_MB} MB.")
    result = extract_text(content)
    return result

@app.post("/api/identify")
def identify(request: AnalysisRequest):
    return identify_medicine(request.ocr_text)

@app.post("/api/analyse")
def analyse(request: AnalysisRequest):
    extracted = extract_medicine_information(request.ocr_text)
    match = extracted["match"]
    suggested_medicine = match.get("medicine") if match.get("matched") else None
    confirmed = bool(suggested_medicine and request.confirmed_medicine == suggested_medicine["name"])
    medicine = suggested_medicine if confirmed else None
    ingredients = medicine["ingredients"] if medicine else []
    precautions = check_condition_precautions(ingredients, request.conditions)
    interactions = check_supported_interactions(ingredients, request.medications)
    query = " ".join([request.ocr_text, *request.conditions, *request.medications, *ingredients])
    evidence = retrieve_medical_evidence(query)
    if confirmed:
        agent = run_agent(f"The user explicitly confirmed the local catalogue match {medicine['name']}. Review this user-reviewed label text: {request.ocr_text}. Conditions: {request.conditions}. Current medicines: {request.medications}. Allergies: {request.allergies}. Confirmed ingredients: {ingredients}. Summarise only sourced evidence.")
    else:
        agent = {"mode": "local_fallback", "answer": "Agent analysis was withheld because no medicine match was explicitly confirmed by the user."}
    return {"medicine_name": medicine["name"] if medicine else ("Suggested match — not confirmed" if suggested_medicine else "Not confidently identified"),
            "suggested_medicine": suggested_medicine["name"] if suggested_medicine else None, "match_confirmed": confirmed, "medicine_source": medicine["source"] if medicine else None, "medicine_verification": medicine["verification"] if medicine else None, "match": match, "extracted_fields": extracted, "ingredients": ingredients, "precautions": precautions,
            "interactions": interactions, "evidence": evidence, "agent": agent,
            "conditions": request.conditions, "medications": request.medications,
            "allergies": request.allergies,
            "ocr_text": request.ocr_text,
            "uncertainties": ([] if medicine else ["Medicine identity is not confirmed. Ingredient-level checks were not run until a catalogue match is explicitly confirmed."]),
            "disclaimer": "Educational information only. Not a diagnosis or clinical decision-support tool. Consult a qualified doctor or pharmacist."}

@app.post("/api/report.pdf")
def pdf(report: dict):
    return Response(make_pdf(report), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=medlens-report.pdf"})
