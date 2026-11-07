import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_ocr_rejects_non_image_upload():
    response = client.post('/api/ocr', files={'file': ('notes.txt', b'not an image', 'text/plain')})
    assert response.status_code == 400


def test_analyse_endpoint_returns_safe_unknown_status():
    response = client.post('/api/analyse', json={
        'ocr_text': 'AMOXICILLIN 500 mg',
        'conditions': ['diabetes'],
        'medications': ['allopurinol'],
        'allergies': []
    })
    assert response.status_code == 200
    data = response.json()
    assert data['medicine_name'] == 'Suggested match — not confirmed'
    assert data['match_confirmed'] is False
    assert data['ingredients'] == []
    assert data['agent']['mode'] == 'local_fallback'


def test_analyse_runs_checks_only_after_explicit_match_confirmation():
    response = client.post('/api/analyse', json={
        'ocr_text': 'AMOXICILLIN 500 mg', 'conditions': [],
        'medications': ['allopurinol'], 'allergies': [],
        'confirmed_medicine': 'Amoxicillin'
    })
    assert response.status_code == 200
    data = response.json()
    assert data['match_confirmed'] is True
    assert data['ingredients'] == ['amoxicillin']
    assert data['interactions']['status'] == 'finding_available'


def test_ocr_endpoint_accepts_image_and_reports_engine_status():
    from pathlib import Path
    image_path = Path(__file__).resolve().parents[1] / 'sample_images' / 'demo_medicine_label.png'
    response = client.post('/api/ocr', files={'file': ('demo.png', image_path.read_bytes(), 'image/png')})
    assert response.status_code == 200
    data = response.json()
    assert 'engine' in data and 'warning' in data


def test_pdf_export_returns_pdf_bytes():
    response = client.post('/api/report.pdf', json={'medicine_name': 'Demo', 'ocr_text': 'label text', 'ingredients': [], 'precautions': [], 'interactions': {}, 'evidence': [], 'uncertainties': []})
    assert response.status_code == 200
    assert response.content.startswith(b'%PDF')


def test_agent_has_local_fallback_without_api_key(monkeypatch):
    from backend.agent.coordinator import run_agent
    monkeypatch.setenv('OPENAI_API_KEY', '')
    result = run_agent('Do not make a medical conclusion.')
    assert result['mode'] == 'local_fallback'
