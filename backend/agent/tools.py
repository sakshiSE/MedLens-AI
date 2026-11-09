"""Callable tools used by the MedLens AI coordinator."""

from langchain_core.tools import tool

from backend.services.medicine_service import (
    extract_medicine_information,
    lookup_ingredient,
    check_condition_precautions,
    check_supported_interactions,
)
from backend.services.api_retriever import retrieve_ingredient_information
from backend.rag.retriever import retrieve_medical_evidence


@tool(
    "extract_medicine_information",
    description="Extract candidate medicine name, ingredients, strength and manufacturer from reviewed OCR text."
)
def extract_medicine_information_tool(label_text: str) -> str:
    return str(extract_medicine_information(label_text))


@tool(
    "lookup_ingredient",
    description="Look up an ingredient in the local Indian medicine catalogue."
)
def lookup_ingredient_tool(ingredient: str) -> str:
    return str(
        lookup_ingredient(ingredient)
        or {"status": "not found in local catalogue"}
    )


@tool(
    "retrieve_ingredient_information",
    description=(
        "Retrieve dynamic compound descriptions from PubChem and available "
        "drug-label sections from openFDA for a supplied active ingredient. "
        "These sources do not establish patient-specific safety."
    )
)
def retrieve_ingredient_information_tool(ingredient: str) -> str:
    return str(retrieve_ingredient_information(ingredient))


@tool(
    "check_condition_precautions",
    description="Find documented local precautions matching supplied ingredients and health conditions."
)
def condition_precaution_tool(
    ingredients: list[str],
    conditions: list[str],
) -> str:
    return str(check_condition_precautions(ingredients, conditions))


@tool(
    "check_supported_interactions",
    description="Check only documented medication interaction pairs in the local dataset."
)
def interaction_screening_tool(
    ingredients: list[str],
    medications: list[str],
) -> str:
    return str(check_supported_interactions(ingredients, medications))


@tool(
    "retrieve_medical_evidence",
    description="Retrieve supporting passages from local medical reference documents."
)
def medical_evidence_tool(query: str) -> str:
    return str(retrieve_medical_evidence(query))


AGENT_TOOLS = [
    extract_medicine_information_tool,
    lookup_ingredient_tool,
    retrieve_ingredient_information_tool,
    condition_precaution_tool,
    interaction_screening_tool,
    medical_evidence_tool,
]