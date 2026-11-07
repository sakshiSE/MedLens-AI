# MedLens AI — Architecture at a glance

```text
SvelteKit UI
   |  image upload / reviewed OCR text / user-entered context
   v
FastAPI REST API
   |-- OCR service (Pillow -> EasyOCR)
   |-- Medicine service (normalisation -> fuzzy match -> local JSON/CSV)
   |-- Precaution checker (CSV exact match)
   |-- Interaction checker (CSV exact pair)
   |-- RAG retriever (paragraph chunks -> Sentence Transformers -> FAISS)
   |-- Coordinator agent (LangChain create_agent -> reusable tools)
   v
Structured report -> PDF export (ReportLab)
```

## Agent decision flow

The coordinator receives a structured prompt with the user-reviewed label text, conditions and medications. It has five callable tools: `extract_medicine_information`, ingredient lookup, condition precaution lookup, interaction screening and evidence retrieval. The model chooses tools as needed. The tool outputs contain only local reference records. The system prompt instructs the model not to invent facts and to state when evidence is missing. The final report still includes deterministic checks independently of the LLM. If the key is missing or the agent errors, the API reports `local_fallback` and returns the deterministic result.

## Viva-friendly design choices

- Keep OCR, data matching, retrieval, agent orchestration and PDF generation in separate modules.
- Use CSV/JSON instead of a database for a small academic prototype.
- Use deterministic code for exact comparisons; do not ask an LLM to calculate or decide exact catalogue matches.
- Require human review because OCR and fuzzy matching can be wrong.
- Show source links and uncertainty next to findings.
