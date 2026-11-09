"""Local medicine catalogue, transparent matching and deterministic checks."""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def load_medicines() -> list[dict]:
    path = DATA_DIR / "medicines.json"
    return json.loads(path.read_text(encoding="utf-8"))


def search_medicine_by_name(name: str, threshold: float = 0.90) -> dict:
    """Search the local Indian medicine catalogue by entered name."""
    source = normalise(name)

    if len(source) < 2:
        return {
            "matched": False,
            "confidence": 0.0,
            "medicine": None,
            "message": "Enter a medicine name containing at least two characters.",
        }

    candidates = []

    for item in load_medicines():
        terms = [
            item.get("name", ""),
            item.get("generic_name", ""),
        ]

        scores = [
            SequenceMatcher(None, source, normalise(term)).ratio()
            for term in terms if term
        ]

        exact = any(source == normalise(term) for term in terms if term)
        score = 1.0 if exact else max(scores, default=0.0)

        if score >= threshold:
            candidates.append((score, item))

    if not candidates:
        return {
            "matched": False,
            "confidence": 0.0,
            "medicine": None,
            "message": (
                "No sufficiently close match was found in the local "
                "medicine catalogue. Check the spelling or exact product label."
            ),
        }

    score, medicine = max(candidates, key=lambda row: row[0])

    return {
        "matched": True,
        "confidence": round(score, 2),
        "medicine": medicine,
        "needs_user_confirmation": True,
    }


def identify_medicine(text: str, threshold: float = 0.78) -> dict:
    """Match label text against known names/ingredients."""
    source = normalise(text)
    candidates = []

    for item in load_medicines():
        terms = [
            item.get("name", ""),
            item.get("generic_name", ""),
            *item.get("ingredients", []),
        ]
        scores = [
            SequenceMatcher(None, normalise(term), source).ratio()
            for term in terms if term
        ]
        contains = any(
            normalise(term) and normalise(term) in source
            for term in terms
        )
        score = max(scores + ([0.94] if contains else []), default=0.0)
        candidates.append((score, item))

    if not candidates:
        return {"matched": False, "confidence": 0.0, "medicine": None}

    score, item = max(candidates, key=lambda row: row[0])

    if score < threshold:
        return {
            "matched": False,
            "confidence": round(score, 2),
            "medicine": None,
            "message": "No sufficiently confident local catalogue match.",
        }

    return {
        "matched": True,
        "confidence": round(score, 2),
        "medicine": item,
        "needs_user_confirmation": True,
    }


def lookup_ingredient(name: str) -> dict | None:
    key = normalise(name)

    for item in load_medicines():
        for ingredient in item.get("ingredients", []):
            if key == normalise(ingredient):
                return {
                    "ingredient": ingredient,
                    "medicine_examples": [item["name"]],
                    "source": item.get("source", ""),
                    "verification": item.get("verification", ""),
                }

    return None


def check_condition_precautions(
    ingredients: list[str],
    conditions: list[str]
) -> list[dict]:
    """Return only explicit local evidence records."""
    path = DATA_DIR / "precautions.csv"
    data = pd.read_csv(path).fillna("")

    known_ingredients = {normalise(x) for x in ingredients}
    found = []

    for _, row in data.iterrows():
        ingredient = normalise(row["ingredient"])
        condition = normalise(row["condition"])

        ingredient_match = ingredient in known_ingredients
        condition_match = any(
            condition == normalise(user_condition)
            for user_condition in conditions
            if user_condition.strip()
        )

        if ingredient_match and condition_match:
            found.append({
                "ingredient": row["ingredient"],
                "condition": row["condition"],
                "finding": row["finding"],
                "source": row["source"],
                "verification": row["verification"],
            })

    return found


def check_supported_interactions(
    ingredients: list[str],
    medications: list[str]
) -> dict:
    """Check only documented ingredient/medication pairs."""
    path = DATA_DIR / "interactions.csv"
    data = pd.read_csv(path).fillna("")

    known = {normalise(x) for x in ingredients}
    user_meds = {normalise(x) for x in medications}
    matches = []

    for _, row in data.iterrows():
        pair = {
            normalise(row["ingredient_a"]),
            normalise(row["ingredient_b"]),
        }

        if (pair & known) and (pair & user_meds):
            matches.append({
                "ingredient_a": row["ingredient_a"],
                "ingredient_b": row["ingredient_b"],
                "finding": row["finding"],
                "category": row["category"],
                "source": row["source"],
                "verification": row["verification"],
            })

    return {
        "status": "finding_available" if matches
                  else "not_established_in_local_dataset",
        "findings": matches,
        "message": (
            "A documented interaction pair matched. Ask a pharmacist "
            "to interpret it for your situation."
            if matches else
            "No supported pair was found in this small dataset. "
            "This is not proof that no interaction exists."
        ),
    }


def extract_medicine_information(label_text: str) -> dict:
    """Extract simple label fields from reviewed OCR text."""
    match = identify_medicine(label_text)

    strengths = re.findall(
        r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|%|iu)\b",
        label_text,
        flags=re.I,
    )

    manufacturer = ""
    for line in label_text.splitlines():
        if re.search(
            r"\b(mfg|mfd|manufactured by|marketed by|manufacturer)\b",
            line,
            re.I,
        ):
            manufacturer = line.strip()
            break

    other_ingredients = []
    for line in label_text.splitlines():
        if re.search(
            r"\b(excipients|inactive ingredients|other ingredients)\b",
            line,
            re.I,
        ):
            other_ingredients.append(line.strip())

    medicine = match.get("medicine") if match.get("matched") else None

    return {
        "medicine_name": medicine["name"] if medicine else None,
        "active_ingredients": medicine.get("ingredients", []) if medicine else [],
        "other_ingredient_lines": other_ingredients,
        "strengths": list(dict.fromkeys(strengths)),
        "manufacturer_line": manufacturer or None,
        "confidence": match.get("confidence", 0.0),
        "requires_review": True,
        "match": match,
    }