
"""Callable tools used by the MedLens AI coordinator."""

from backend.services.medicine_service import (
    extract_medicine_information,
    lookup_ingredient,
    check_condition_precautions,
    check_supported_interactions,
)

from backend.rag.retriever import retrieve_medical_evidence

from langchain_core.tools import tool


@tool(
    "extract_medicine_information",
    description="Extract candidate medicine name, ingredients, strength and manufacturer from reviewed OCR text."
)
def extract_medicine_information_tool(label_text: str) -> str:
    return str(extract_medicine_information(label_text))


@tool(
    "lookup_ingredient",
    description="Look up an ingredient in the local medicine catalogue."
)
def lookup_ingredient_tool(ingredient: str) -> str:
    return str(
        lookup_ingredient(ingredient)
        or {"status": "not found in local catalogue"}
    )


@tool(
    "check_condition_precautions",
    description="Find documented precautions relevant to supplied health conditions."
)
def condition_precaution_tool(
    ingredients: list[str],
    conditions: list[str]
) -> str:
    return str(
        check_condition_precautions(ingredients, conditions)
    )


@tool(
    "check_supported_interactions",
    description="Check only documented medication interaction pairs."
)
def interaction_screening_tool(
    ingredients: list[str],
    medications: list[str]
) -> str:
    return str(
        check_supported_interactions(ingredients, medications)
    )


@tool(
    "retrieve_medical_evidence",
    description="Retrieve supporting passages from local medical reference documents."
)
def medical_evidence_tool(query: str) -> str:
    return str(retrieve_medical_evidence(query))


AGENT_TOOLS = [
    extract_medicine_information_tool,
    lookup_ingredient_tool,
    condition_precaution_tool,
    interaction_screening_tool,
    medical_evidence_tool,
]
