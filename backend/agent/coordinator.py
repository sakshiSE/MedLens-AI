"""Coordinator agent with deterministic local fallback."""

import os

from backend.agent.tools import AGENT_TOOLS


SYSTEM_PROMPT = """
You are MedLens AI, an educational medicine-label information assistant.

SAFETY RULES:
- Use the available tools for medicine and ingredient facts.
- Never diagnose, prescribe, recommend a dose, or advise starting,
  stopping, or changing medication.
- Do not claim a medicine is safe for a person.
- Do not infer that absence of a warning means absence of risk.
- Distinguish Indian catalogue information from US openFDA label information.
- PubChem compound descriptions are not clinical recommendations.
- Do not claim that openFDA data confirms Indian regulatory approval.
- Do not invent an ingredient, indication, precaution, or interaction.
- If a source does not provide information, say that it was not found.
- Explain technical terms in simple language.
- Mention the source names used for each factual explanation.
- A condition warning must be supported by retrieved evidence.
- Allergy screening is not implemented. Never claim allergy compatibility.
- If the exact product formulation is uncertain, clearly say so.
"""


def run_agent(question: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "")

    if not api_key:
        return {
            "mode": "local_fallback",
            "answer": (
                "The LLM is not configured. Deterministic local checks "
                "and retrieved reference information remain available. "
                "No generated medical conclusion was added."
            ),
        }

    try:
        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0,
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )

        agent = create_agent(
            model=model,
            tools=AGENT_TOOLS,
            system_prompt=SYSTEM_PROMPT,
        )

        result = agent.invoke({
            "messages": [
                {"role": "user", "content": question}
            ]
        })

        messages = result.get("messages", [])
        answer = (
            messages[-1].content
            if messages else "No agent response was returned."
        )

        return {
            "mode": "langchain_create_agent",
            "answer": answer,
        }

    except Exception as exc:
        return {
            "mode": "local_fallback",
            "answer": (
                "Agent unavailable; deterministic local checks remain "
                f"available. ({type(exc).__name__})"
            ),
        }