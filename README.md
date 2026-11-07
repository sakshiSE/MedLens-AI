# MedLens AI

**Smart Medicine Label Scanner and Precaution Analyser** — a viva-friendly academic prototype built with SvelteKit, FastAPI, EasyOCR, local medicine data, RAG and a LangChain `create_agent` coordinator.

> **Medical safety:** This is an educational demonstration, not a medical diagnosis or clinical decision-support product. It must not be used to decide whether to take a medicine. It does not prescribe, diagnose, or recommend starting, stopping, or changing medicines. Always consult a qualified doctor or pharmacist.

## 1. What is implemented

- Responsive healthcare landing page inspired by the supplied mint/teal hospital-site reference.
- JPG/PNG upload, drag-and-drop, preview, remove and 8 MB validation.
- EasyOCR extraction with a reviewable/editable OCR text area. OCR is explicitly treated as uncertain.
- Local medicine catalogue (10 generic medicine examples), normalisation and fuzzy matching with a confidence threshold and explicit user confirmation before ingredient-level checks.
- Deterministic condition-precaution and interaction checks against small CSV datasets.
- RAG over local reference text: paragraph chunking, Sentence Transformers embeddings and FAISS. If those optional libraries/model downloads are unavailable, a local lexical retrieval fallback is used.
- A real LangChain `create_agent` workflow with callable tools when `OPENAI_API_KEY` is configured. Without the key, the backend uses deterministic local checks and reports that the LLM was not used.
- PDF report download (including the uploaded image), source links, health context, uncertainties and safety disclaimer.
- FastAPI endpoints and automated tests for important local functions.

## 2. Important scope and evidence notes

The local catalogue has 10 examples. Metformin and amoxicillin have limited label-derived precaution/interaction notes linked to DailyMed. The other eight catalogue examples are **identity-only demonstrations**: no clinical precaution or interaction is asserted for them. The interaction dataset intentionally contains only two label-supported pairs:

- Metformin + insulin: the referenced metformin label warns of increased hypoglycemia risk with concomitant insulin/insulin-secretagogue use.
- Amoxicillin + allopurinol: the referenced amoxicillin label says concomitant use increases rash risk.

The metformin renal-impairment note is a label-derived precaution. The app cannot determine a user's kidney function. These notes are US product-label references and may not match the exact brand, formulation or current Indian pack. Allergy entries are shown in the report but are not checked against an allergy dataset. The app does not query ABDM or RxNorm live. The openFDA documentation is included as a source note; FDA states that submitted label content is not verified by FDA and advises against relying on the API for medical-care decisions. See `reference_documents/` and each record's source URL.

No result from the small local interaction list means only **not established in this local dataset** — never “no interaction” or “safe”. OCR output and fuzzy matches must be reviewed by the user. The app currently asks for user confirmation but does not treat OCR alone as clinical verification.

## 3. Project structure

```text
MedLens_AI/
├── backend/
│   ├── main.py                 # FastAPI endpoints
│   ├── config.py               # Environment configuration
│   ├── services/
│   │   ├── ocr_service.py      # EasyOCR adapter
│   │   ├── medicine_service.py # Matching + deterministic checks
│   │   └── report_service.py   # PDF export
│   ├── rag/retriever.py        # Chunking, embeddings, FAISS, fallback
│   ├── agent/
│   │   ├── tools.py            # LangChain callable tools
│   │   └── coordinator.py      # create_agent + no-key fallback
│   ├── data/                   # Local JSON/CSV catalogue
│   └── requirements.txt
├── frontend/                   # SvelteKit website and scanner UI
├── reference_documents/        # Local RAG source text and URLs
├── sample_images/              # Synthetic sample label image
├── tests/                      # Pytest unit tests
├── .env.example
└── README.md
```

## 4. Run in VS Code on Windows 10/11

Open the `MedLens_AI` folder in VS Code. Use two separate PowerShell terminals.

### A. Backend

Python 3.12 is recommended.

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..
Copy-Item .env.example .env
```

If PowerShell blocks activation, run this once in the terminal and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Start FastAPI from the project root (so the `backend` package imports resolve):

```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Check `http://127.0.0.1:8000/api/health` and interactive API docs at `http://127.0.0.1:8000/docs`.

### B. Frontend

Open a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://127.0.0.1:5173`). Keep both terminals running.

### C. Optional LLM agent

Edit the root `.env` file and add your key:

```env
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
```

`OPENAI_BASE_URL` is optional and allows an OpenAI-compatible endpoint if your provider supports the Chat Completions API. Keep provider keys private.

Restart FastAPI after editing `.env`. The key is never stored in source code. If no key is supplied or the agent call fails, local OCR/catalogue/precaution/interaction/RAG functionality remains available and the response identifies the fallback mode. An LLM key is not needed for local checks.

### D. OCR and first RAG run

Two synthetic label examples are included in `sample_images/`; they are not real medicines. EasyOCR may download its English recognition model on first use. Sentence Transformers may download `all-MiniLM-L6-v2` on first RAG embedding use. Those model files are cached by their libraries. If embedding setup fails, the retriever automatically attempts lexical fallback. EasyOCR must be installed and its model available for image-to-text OCR; otherwise the OCR endpoint returns a clear warning and the text box can still be edited manually.

## 5. Testing

From the project root, with the backend virtual environment active:

```powershell
pip install pytest
python -m pytest -q
```

The tests cover API health, upload validation, report PDF output, medicine matching, unknown medicine text, strength/manufacturer text extraction, a source-linked precaution, a supported interaction, an unsupported interaction, local RAG retrieval and the no-key agent fallback. Syntax check:

```powershell
python -m compileall backend
```

## 6. API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | API health check |
| POST | `/api/ocr` | Upload an image and extract OCR text |
| POST | `/api/identify` | Fuzzy-match reviewed label text |
| POST | `/api/analyse` | Run local checks, RAG and optional agent |
| POST | `/api/report.pdf` | Download a report as PDF |

## 7. Viva explanation (simple architecture)

1. **Frontend:** SvelteKit collects the image and health-context text and communicates with FastAPI using `fetch`.
2. **OCR:** Pillow opens and improves image contrast; EasyOCR returns text lines and confidence values. OCR is editable because it can make mistakes.
3. **Identification:** `medicine_service.py` normalises text and uses `SequenceMatcher` for fuzzy matching. A match is only a suggestion and requires confirmation.
4. **Precaution and interaction checks:** Pandas reads small CSV tables. Python compares normalised ingredient/condition or ingredient/medicine pairs. Only listed records can produce a finding.
5. **RAG:** `retriever.py` splits local reference documents into paragraphs, embeds them using Sentence Transformers and searches a FAISS index. A lexical fallback keeps retrieval available if embedding dependencies are unavailable.
6. **Agentic AI:** `coordinator.py` creates a LangChain agent using `create_agent`. Its tools call the same reusable lookup, check and retrieval functions. The agent is optional; without an API key, deterministic functions still work.
7. **Report:** FastAPI combines the structured findings and `report_service.py` creates a PDF using ReportLab.

### Why both RAG and deterministic checks?

Deterministic checks are used for exact matching against the small curated CSV data. RAG helps retrieve relevant paragraphs from longer reference notes. The LLM can explain retrieved information, but it is not the source of medical truth. This separation makes the project easier to test and explain.

## 8. Limitations / future work

- The data coverage is intentionally small and not suitable for real medication decisions.
- The local catalogue does not identify every brand, formulation, salt or combination product.
- The fuzzy score is a text similarity indicator, not a probability of correct identification.
- No live ABDM, NRCeS, RxNorm or openFDA synchronisation is implemented.
- No comprehensive interaction database is included; unknown pairs remain unknown.
- The reference notes are US label excerpts. Add pharmacist-reviewed India-specific sources before any real-world deployment.
- OCR quality depends on image clarity, lighting, orientation and print size.
- RAG embedding models require a first-time model download; the local lexical fallback is less semantically capable.
- The LLM agent needs an API key and internet access. Local checks do not.

## 9. Data provenance

- DailyMed metformin label: https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=55b25f66-a0a3-4e2e-9c4a-6354f41072fa
- DailyMed amoxicillin label: https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=110ba6b1-f175-48a1-8e30-616c02212538
- openFDA drug-label API overview and its data caveats: https://open.fda.gov/apis/drug/label/
- openFDA endpoint usage: https://open.fda.gov/apis/drug/label/how-to-use-the-endpoint/

These records are a student demonstration subset, not a validated clinical database. Verify the exact current product label and consult a healthcare professional.


## 10. Build verification note

Backend syntax checks and all included pytest tests were run successfully in the packaging environment. A full SvelteKit `npm install` / production build could not be executed there because the npm registry was unreachable; the frontend package manifest and source are included. On your Windows machine, run the documented `npm install` and `npm run dev` commands. The OCR engine and embedding model also require their first-time package/model installation on your machine.
