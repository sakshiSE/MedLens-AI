"""Local medicine catalogue, transparent matching and deterministic checks."""
import json, re
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def load_medicines() -> list[dict]:
    path = DATA_DIR / "medicines.json"
    return json.loads(path.read_text(encoding="utf-8"))


def identify_medicine(text: str, threshold: float = 0.78) -> dict:
    """Match label text against known names/ingredients; never force a weak match."""
    source = normalise(text)
    candidates = []
    for item in load_medicines():
        terms = [item["name"], item["generic_name"], *item["ingredients"]]
        scores = [SequenceMatcher(None, normalise(term), source).ratio() for term in terms]
        contains = any(normalise(term) and normalise(term) in source for term in terms)
        score = max(scores + ([0.94] if contains else []))
        candidates.append((score, item))
    if not candidates:
        return {"matched": False, "confidence": 0.0, "medicine": None}
    score, item = max(candidates, key=lambda row: row[0])
    if score < threshold:
        return {"matched": False, "confidence": round(score, 2), "medicine": None,
                "message": "No sufficiently confident local catalogue match."}
    return {"matched": True, "confidence": round(score, 2), "medicine": item,
            "needs_user_confirmation": True}


def lookup_ingredient(name: str) -> dict | None:
    key = normalise(name)
    for item in load_medicines():
        for ingredient in item["ingredients"]:
            if key == normalise(ingredient):
                return {"ingredient": ingredient, "medicine_examples": [item["name"]],
                        "source": item["source"], "verification": item["verification"]}
    return None


def check_condition_precautions(ingredients: list[str], conditions: list[str]) -> list[dict]:
    """Return only explicit local evidence records; no inferred contraindications."""
    data = pd.read_csv(DATA_DIR / "precautions.csv").fillna("")
    found = []
    for _, row in data.iterrows():
        if normalise(row["ingredient"]) in {normalise(x) for x in ingredients} and any(
            normalise(row["condition"]) in normalise(c) or normalise(c) in normalise(row["condition"])
            for c in conditions if c.strip()
        ):
            found.append({"ingredient": row["ingredient"], "condition": row["condition"],
                          "finding": row["finding"], "source": row["source"],
                          "verification": row["verification"]})
    return found


def check_supported_interactions(ingredients: list[str], medications: list[str]) -> dict:
    """Only exact pairs in the small sourced interaction file are reported."""
    data = pd.read_csv(DATA_DIR / "interactions.csv").fillna("")
    known = {normalise(x) for x in ingredients}
    user_meds = {normalise(x) for x in medications}
    matches = []
    for _, row in data.iterrows():
        pair = {normalise(row["ingredient_a"]), normalise(row["ingredient_b"])}
        if (pair & known) and (pair & user_meds):
            matches.append({"ingredient_a": row["ingredient_a"], "ingredient_b": row["ingredient_b"],
                            "finding": row["finding"], "category": row["category"],
                            "source": row["source"], "verification": row["verification"]})
    return {"status": "finding_available" if matches else "not_established_in_local_dataset",
            "findings": matches,
            "message": "No supported pair in this small dataset is not proof that no interaction exists." if not matches else "A label-documented interaction pair matched. Ask a pharmacist to interpret it for your situation."}


def extract_medicine_information(label_text: str) -> dict:
    """Extract simple label fields from reviewed OCR text; values remain unverified."""
    match = identify_medicine(label_text)
    strengths = re.findall(r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|%|iu)\b", label_text, flags=re.I)
    manufacturer = ""
    for line in label_text.splitlines():
        if re.search(r"\b(mfg|mfd|manufactured by|marketed by|manufacturer)\b", line, re.I):
            manufacturer = line.strip()
            break
    other_ingredients = []
    for line in label_text.splitlines():
        if re.search(r"\b(excipients|inactive ingredients|other ingredients)\b", line, re.I):
            other_ingredients.append(line.strip())
    medicine = match.get("medicine") if match.get("matched") else None
    return {"medicine_name": medicine["name"] if medicine else None,
            "active_ingredients": medicine["ingredients"] if medicine else [],
            "other_ingredient_lines": other_ingredients,
            "strengths": list(dict.fromkeys(strengths)),
            "manufacturer_line": manufacturer or None,
            "confidence": match.get("confidence", 0.0),
            "requires_review": True, "match": match}
