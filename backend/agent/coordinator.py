"""Coordinator agent. Deterministic local analysis remains available without an API key."""
import os
from backend.agent.tools import AGENT_TOOLS

SYSTEM_PROMPT = """You are a cautious medicine-label information assistant for an educational prototype.
Use tools for all medicine facts. Never diagnose, prescribe, or advise changing medication.
Do not infer that absence of a retrieved interaction means safety. If evidence is missing, say so. Allergy screening is not implemented; do not infer allergy compatibility.
Cite the source names returned by tools. Clearly separate label text from user-provided OCR text."""


def run_agent(question: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"mode": "local_fallback", "answer": "LLM is not configured. The application used deterministic local checks and retrieved local evidence. No generated medical conclusion was added."}
    try:
        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI(model=os.getenv("LLM_MODEL", "gpt-4o-mini"), temperature=0, api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL") or None)
        agent = create_agent(model=model, tools=AGENT_TOOLS, system_prompt=SYSTEM_PROMPT)
        result = agent.invoke({"messages": [{"role": "user", "content": question}]})
        messages = result.get("messages", [])
        answer = messages[-1].content if messages else "No agent response was returned."
        return {"mode": "langchain_create_agent", "answer": answer}
    except Exception as exc:
        return {"mode": "local_fallback", "answer": f"Agent unavailable; local checks were retained. ({type(exc).__name__})"}
