"""Dynamic medicine and ingredient information retrieval.

openFDA provides product-label information.
PubChem provides compound descriptions.
Neither source independently establishes patient-specific safety.
"""

import json
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


OPENFDA_URL = "https://api.fda.gov/drug/label.json"
PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"


def _get_json(url: str, timeout: int = 10) -> dict | None:
    """GET JSON safely. Return None when the API is unavailable."""
    try:
        request = Request(
            url,
            headers={"User-Agent": "MedLensAI/1.0", "Accept": "application/json"}
        )
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        return None


def retrieve_pubchem_information(ingredient: str) -> dict:
    """Retrieve a compound description from PubChem."""
    name = ingredient.strip()
    if not name:
        return {"status": "not_searched", "source": "PubChem"}

    url = (
        f"{PUBCHEM_URL}/{quote(name, safe='')}"
        "/description/JSON"
    )
    data = _get_json(url)

    if not data:
        return {
            "status": "unavailable_or_not_found",
            "ingredient": name,
            "source": "PubChem",
        }

    records = (
        data.get("InformationList", {}).get("Information", [])
    )
    descriptions = [
        item.get("Description")
        for item in records
        if item.get("Description")
    ]

    return {
        "status": "found" if descriptions else "description_not_available",
        "ingredient": name,
        "descriptions": descriptions[:3],
        "source": "PubChem",
        "source_url": "https://pubchem.ncbi.nlm.nih.gov/",
    }


def retrieve_openfda_label(ingredient: str) -> dict:
    """Retrieve label sections matching an ingredient's generic name.

    These are US drug-label records and may not describe the exact
    Indian brand, strength, or formulation entered by the user.
    """
    name = ingredient.strip()
    if not name:
        return {"status": "not_searched", "source": "openFDA"}

    search_expression = f'generic_name:"{name}"'
    params = urlencode({
        "search": search_expression,
        "limit": 3,
    })
    data = _get_json(f"{OPENFDA_URL}?{params}")

    if not data or not data.get("results"):
        return {
            "status": "not_found_or_unavailable",
            "ingredient": name,
            "source": "openFDA",
        }

    useful_fields = [
        "indications_and_usage",
        "warnings",
        "warnings_and_cautions",
        "contraindications",
        "precautions",
        "drug_interactions",
        "active_ingredient",
        "purpose",
    ]

    labels = []
    for result in data.get("results", []):
        sections = {}
        for field in useful_fields:
            value = result.get(field)
            if value:
                sections[field] = value[:3] if isinstance(value, list) else value

        labels.append({
            "effective_time": result.get("effective_time"),
            "brand_name": result.get("openfda", {}).get("brand_name", []),
            "generic_name": result.get("openfda", {}).get("generic_name", []),
            "manufacturer": result.get("openfda", {}).get("manufacturer_name", []),
            "sections": sections,
        })

    return {
        "status": "found",
        "ingredient": name,
        "labels": labels,
        "source": "openFDA",
        "source_url": "https://open.fda.gov/apis/drug/label/",
        "scope_note": (
            "US drug-label information. Confirm the exact Indian product "
            "and current package insert before applying it."
        ),
    }


def retrieve_ingredient_information(ingredient: str) -> dict:
    """Combine independent compound and product-label lookups."""
    return {
        "ingredient": ingredient,
        "pubchem": retrieve_pubchem_information(ingredient),
        "openfda": retrieve_openfda_label(ingredient),
    }