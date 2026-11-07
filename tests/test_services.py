import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services.medicine_service import identify_medicine, check_condition_precautions, check_supported_interactions
from backend.rag.retriever import retrieve_medical_evidence


def test_metformin_identification_requires_confirmation():
    result = identify_medicine("METFORMIN HYDROCHLORIDE 500 mg")
    assert result["matched"] is True
    assert result["medicine"]["generic_name"] == "metformin hydrochloride"
    assert result["needs_user_confirmation"] is True


def test_unknown_text_not_forced_to_match():
    result = identify_medicine("mystery compound xyz 123")
    assert result["matched"] is False


def test_renal_precaution_is_source_linked():
    result = check_condition_precautions(["metformin"], ["renal impairment"])
    assert len(result) == 1
    assert result[0]["source"].startswith("https://dailymed")


def test_supported_interaction_is_found():
    result = check_supported_interactions(["amoxicillin"], ["allopurinol"])
    assert result["status"] == "finding_available"
    assert "rash" in result["findings"][0]["finding"].lower()


def test_unsupported_interaction_is_not_called_safe():
    result = check_supported_interactions(["amoxicillin"], ["cetirizine"])
    assert result["status"] == "not_established_in_local_dataset"
    assert "not proof" in result["message"]


def test_rag_returns_source_passages():
    result = retrieve_medical_evidence("metformin renal impairment")
    assert result
    assert any("metformin" in item["text"].lower() for item in result)


def test_extracts_strength_and_marks_fields_for_review():
    from backend.services.medicine_service import extract_medicine_information
    result = extract_medicine_information("METFORMIN HYDROCHLORIDE 500 mg\nMfd by Demo Labs")
    assert result["strengths"] == ["500 mg"]
    assert result["manufacturer_line"] == "Mfd by Demo Labs"
    assert result["requires_review"] is True
