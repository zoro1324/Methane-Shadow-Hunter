"""
Gemini LLM Service with Google Search Tools  (LangChain implementation).

Uses Google Gemini 2.0 Flash via **langchain-google-genai** with Gemini's
native Google Search grounding bound as a tool.  The grounding is activated
only for the two facility-intelligence searches triggered during report
generation for confirmed suspicious methane emitters.

This service is separate from the primary report-drafting LLM:
  - Primary LLM (Ollama or Gemini, no search)  → drafts the audit text
  - GeminiSearchService (Gemini + Google Search) → looks up facility owner
    and compliance history using live web results
"""

from typing import Any, Optional


class GeminiSearchService:
    """
    LangChain-based Gemini search service for facility intelligence.

    Uses ``ChatGoogleGenerativeAI`` from ``langchain-google-genai`` with
    Gemini's built-in ``google_search_retrieval`` tool bound via
    ``bind_tools()``.  Activated when emission_rate >= threshold.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        # ChatGoogleGenerativeAI instance with search grounding bound
        self._llm: Optional[Any] = None

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_llm(self) -> bool:
        """Lazily initialise the LangChain Gemini client with search grounding."""
        if self._llm is not None:
            return True
        if not self.api_key:
            print("[Gemini] No API key set – skipping web-search enrichment.")
            return False
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: PLC0415

            base_llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=self.api_key,
                temperature=0.1,
            )
            # Bind Gemini's native Google Search grounding tool.
            # This tells the model it can retrieve live web results.
            self._llm = base_llm.bind_tools([{"google_search_retrieval": {}}])
            print(
                f"[Gemini] LangChain ChatGoogleGenerativeAI ({self.model}) "
                "with Google Search grounding ready."
            )
            return True
        except ImportError:
            print(
                "[Gemini] langchain-google-genai not installed. "
                "Run: pip install langchain-google-genai"
            )
            return False
        except Exception as exc:
            print(f"[Gemini] Initialisation failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Public search methods
    # ------------------------------------------------------------------

    def search_facility_owner(
        self,
        facility_name: str,
        operator: str,
        state: str,
        lat: float,
        lon: float,
        facility_type: str = "",
    ) -> Optional[str]:
        """
        Search the web for the owner and registration details of a confirmed
        suspicious-emission facility.

        Returns a formatted Markdown section, or None if Gemini is unavailable.
        """
        if not self._init_llm():
            return None

        query = (
            f"Find detailed public information about this industrial facility in India:\n\n"
            f"Facility Name: {facility_name}\n"
            f"Known Operator: {operator}\n"
            f"State / UT: {state}\n"
            f"Facility Type: {facility_type}\n"
            f"Coordinates: {lat:.4f}°N, {lon:.4f}°E\n\n"
            "Please search and provide:\n"
            "1. **Owner / Parent Company** – Full legal entity name, CIN, holding structure\n"
            "2. **Registered Office** – Address, phone, email (publicly available only)\n"
            "3. **Licences & Clearances** – Environmental clearance (EC) number, consent-to-operate status\n"
            "4. **Production Profile** – Capacity, output, number of employees\n"
            "5. **Regulatory Filings** – CPCB / MoEFCC filings, annual environment statements\n"
            "6. **Environmental Track Record** – Prior notices, penalties, closure orders (if any)\n\n"
            "Format as a structured intelligence brief with specific values. "
            "Mark 'Not Found' for any field where public data is unavailable."
        )

        return self._run_search(query, context="facility owner intelligence")

    def search_industry_compliance(
        self,
        operator: str,
        state: str,
        sector: str = "oil and gas",
    ) -> Optional[str]:
        """
        Search for the operator's company-level environmental compliance and
        enforcement history.

        Returns a formatted Markdown section, or None if Gemini is unavailable.
        """
        if not self._init_llm():
            return None

        query = (
            f"Search for environmental compliance and enforcement history for:\n\n"
            f"Company: {operator}\n"
            f"State: {state}, India\n"
            f"Sector: {sector}\n\n"
            "Find and report:\n"
            "1. CPCB (Central Pollution Control Board) enforcement actions or show-cause notices\n"
            "2. State Pollution Control Board (SPCB) closure/directions/penalties\n"
            "3. MoEFCC environmental clearance status and any violations\n"
            "4. Recent news about pollution incidents or leaks (last 3 years)\n"
            "5. Company ESG commitments or published sustainability reports\n\n"
            "Provide specific dates, case numbers, and penalty amounts where available."
        )

        return self._run_search(query, context="compliance history")

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _run_search(self, query: str, context: str = "") -> Optional[str]:
        """
        Invoke the LangChain Gemini model (with Google Search grounding bound)
        and return the text response, annotated with web sources when available.
        """
        if self._llm is None:
            return None
        try:
            from langchain_core.messages import HumanMessage  # noqa: PLC0415

            response = self._llm.invoke([HumanMessage(content=query)])
            result_text = (
                response.content
                if hasattr(response, "content") and response.content
                else "(No response)"
            )

            # Extract grounding sources from the LangChain AIMessage metadata
            sources = _extract_sources_from_message(response)
            if sources:
                result_text += "\n\n**Web Sources Used:**\n" + "\n".join(
                    f"- [{s['title']}]({s['uri']})" for s in sources
                )

            return result_text

        except Exception as exc:
            print(f"[Gemini] Search failed ({context}): {exc}")
            return None


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _extract_sources_from_message(ai_message) -> list[dict]:
    """
    Pull grounding-chunk web sources from a LangChain AIMessage returned by
    ChatGoogleGenerativeAI.  Gemini places them in either
    ``response_metadata['grounding_metadata']`` or ``additional_kwargs``.
    """
    sources: list[dict] = []
    try:
        # Try response_metadata first (langchain-google-genai >= 1.x)
        metadata = (
            getattr(ai_message, "response_metadata", None)
            or getattr(ai_message, "additional_kwargs", None)
            or {}
        )
        grounding = metadata.get("grounding_metadata", {})
        chunks = grounding.get("grounding_chunks", [])
        for chunk in chunks[:5]:
            web = chunk.get("web", {})
            if web:
                sources.append({
                    "title": web.get("title") or "Source",
                    "uri": web.get("uri") or "#",
                })
    except Exception:
        pass
    return sources
