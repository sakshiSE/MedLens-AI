"""FastAPI entry point for MedLens AI."""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
import os

from backend.config import MAX_UPLOAD_MB
from backend.services.ocr_service import extract_text
from backend.services.medicine_service import (
    identify_medicine,
    search_medicine_by_name,
    extract_medicine_information,
    check_condition_precautions,
    check_supported_interactions,
)
from backend.services.api_retriever import retrieve_ingredient_information
from backend.rag.retriever import retrieve_medical_evidence
from backend.agent.coordinator import run_agent
from backend.services.report_service import make_pdf


app = FastAPI(
    title="MedLens AI API",
    version="1.1.0",
    description="Educational medicine label information prototype",
)

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
if frontend_origin:
    allowed_origins.append(frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    ocr_text: str = Field(min_length=2, max_length=12000)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    confirmed_medicine: Optional[str] = None


class MedicineSearchRequest(BaseModel):
    medicine_name: str = Field(min_length=2, max_length=150)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    confirmed_medicine: Optional[str] = None


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "MedLens AI",
    }


@app.post("/api/ocr")
async def ocr(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(
            400,
            "Upload a JPG, JPEG or PNG image."
        )

    content = await file.read()

    if not content or len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            400,
            f"Image must be non-empty and no larger than {MAX_UPLOAD_MB} MB."
        )

    return extract_text(content)


@app.post("/api/identify")
def identify(request: AnalysisRequest):
    return identify_medicine(request.ocr_text)


def build_confirmed_analysis(
    medicine: dict,
    conditions: list[str],
    medications: list[str],
    allergies: list[str],
    ocr_text: str,
    match: dict,
):
    """Run existing deterministic checks and retrieve dynamic information."""

    ingredients = medicine.get("ingredients", [])

    precautions = check_condition_precautions(
        ingredients,
        conditions,
    )

    interactions = check_supported_interactions(
        ingredients,
        medications,
    )

    # Dynamic API information is retrieved for each confirmed ingredient.
    ingredient_information = [
        retrieve_ingredient_information(ingredient)
        for ingredient in ingredients
    ]

    query = " ".join(
        [ocr_text, *conditions, *medications, *ingredients]
    )

    evidence = retrieve_medical_evidence(query)

    question = f"""
    Review this user-confirmed medicine information.

    Medicine: {medicine.get('name')}
    Ingredients: {ingredients}
    User-entered conditions: {conditions}
    Current medicines: {medications}
    Allergies entered by user: {allergies}

    Deterministic condition findings:
    {precautions}

    Deterministic interaction findings:
    {interactions}

    Dynamic ingredient information:
    {ingredient_information}

    Retrieved local evidence:
    {evidence}

    Explain the retrieved information in simple language.
    Use only the supplied evidence and available tools.
    Do not invent warnings or claim that the medicine is safe.
    Clearly state when evidence is unavailable.
    """

    agent = run_agent(question)

    return {
        "medicine_name": medicine.get("name"),
        "match_confirmed": True,
        "medicine_source": medicine.get("source"),
        "medicine_verification": medicine.get("verification"),
        "match": match,
        "ingredients": ingredients,
        "ingredient_information": ingredient_information,
        "precautions": precautions,
        "interactions": interactions,
        "evidence": evidence,
        "agent": agent,
        "conditions": conditions,
        "medications": medications,
        "allergies": allergies,
        "ocr_text": ocr_text,
        "uncertainties": [
            "External reference results may not describe the exact Indian brand, strength or formulation.",
            "The local precaution and interaction datasets cover only a limited number of documented records.",
            "Allergy compatibility is not screened.",
        ],
        "disclaimer": (
            "Educational information only. Not a diagnosis or clinical "
            "decision-support tool. Consult a qualified doctor or pharmacist."
        ),
    }


@app.post("/api/medicine-search")
def medicine_search(request: MedicineSearchRequest):
    """Manual medicine-name lookup without requiring OCR."""

    match = search_medicine_by_name(request.medicine_name)

    if not match.get("matched"):
        return {
            "matched": False,
            "message": match.get("message"),
            "medicine": None,
            "match_confirmed": False,
        }

    medicine = match["medicine"]

    # Do not run ingredient-level checks until the user confirms the match.
    confirmed = (
        request.confirmed_medicine == medicine.get("name")
    )

    if not confirmed:
        return {
            "matched": True,
            "match_confirmed": False,
            "confidence": match["confidence"],
            "medicine": medicine,
            "ingredients": medicine.get("ingredients", []),
            "message": (
                "Please check the medicine name and composition against "
                "your actual package before confirming."
            ),
        }

    report = build_confirmed_analysis(
        medicine=medicine,
        conditions=request.conditions,
        medications=request.medications,
        allergies=request.allergies,
        ocr_text=request.medicine_name,
        match=match,
    )

    report["matched"] = True
    return report


@app.post("/api/analyse")
def analyse(request: AnalysisRequest):
    extracted = extract_medicine_information(request.ocr_text)
    match = extracted["match"]

    suggested_medicine = (
        match.get("medicine")
        if match.get("matched")
        else None
    )

    confirmed = bool(
        suggested_medicine
        and request.confirmed_medicine == suggested_medicine["name"]
    )

    if confirmed:
        return build_confirmed_analysis(
            medicine=suggested_medicine,
            conditions=request.conditions,
            medications=request.medications,
            allergies=request.allergies,
            ocr_text=request.ocr_text,
            match=match,
        )

    return {
        "medicine_name": (
            "Suggested match — not confirmed"
            if suggested_medicine
            else "Not confidently identified"
        ),
        "suggested_medicine": (
            suggested_medicine["name"]
            if suggested_medicine else None
        ),
        "match_confirmed": False,
        "medicine_source": None,
        "medicine_verification": None,
        "match": match,
        "extracted_fields": extracted,
        "ingredients": [],
        "ingredient_information": [],
        "precautions": [],
        "interactions": {
            "status": "not_checked",
            "findings": [],
            "message": "Confirm the medicine identity before ingredient-level checks.",
        },
        "evidence": [],
        "agent": {
            "mode": "local_fallback",
            "answer": (
                "Agent analysis was withheld because no medicine match "
                "was explicitly confirmed by the user."
            ),
        },
        "conditions": request.conditions,
        "medications": request.medications,
        "allergies": request.allergies,
        "ocr_text": request.ocr_text,
        "uncertainties": [
            "Medicine identity is not confirmed. Ingredient-level checks were not run."
        ],
        "disclaimer": (
            "Educational information only. Not a diagnosis or clinical "
            "decision-support tool. Consult a qualified doctor or pharmacist."
        ),
    }


@app.post("/api/report.pdf")
def pdf(report: dict):
    return Response(
        make_pdf(report),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=medlens-report.pdf"
        },
    )