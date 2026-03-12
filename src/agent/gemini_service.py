"""
Web-search enrichment service for facility intelligence.

Supports two search backends:
    - Gemini + Google Search grounding (cloud)
    - Ollama + DuckDuckGo search results (local LLM + web retrieval)

The service is separate from the primary report-drafting LLM. It is used only
for facility owner and compliance-history enrichment sections.
"""

from typing import Any, Optional


class GeminiSearchService:
    """
    Web-search enrichment service for facility intelligence.

    ``provider='gemini'``:
      Uses ``ChatGoogleGenerativeAI`` with Gemini's
      ``google_search_retrieval`` tool.

    ``provider='ollama'``:
      Uses ``duckduckgo-search`` for retrieval and ``ChatOllama`` for
      synthesis.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        provider: str = "gemini",
        ollama_model: str = "llama3:8b",
        ollama_base_url: str = "http://localhost:11434",
    ):
        self.api_key = api_key
        self.model = model
        self.provider = (provider or "gemini").lower()
        self.ollama_model = ollama_model
        self.ollama_base_url = ollama_base_url
        self._llm: Optional[Any] = None
        self._search_provider_label = "Gemini + Google Search"

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_llm(self) -> bool:
        """Lazily initialise the selected search backend."""
        if self._llm is not None:
            return True
        if self.provider == "ollama":
            return self._init_ollama_llm()
        return self._init_gemini_llm()

    def _init_gemini_llm(self) -> bool:
        """Initialise Gemini with native Google Search grounding."""
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
            self._search_provider_label = "Gemini + Google Search"
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

    def _init_ollama_llm(self) -> bool:
        """Initialise local Ollama for synthesis of retrieved web results."""
        try:
            from langchain_ollama import ChatOllama  # noqa: PLC0415

            self._llm = ChatOllama(
                model=self.ollama_model,
                base_url=self.ollama_base_url,
                temperature=0.1,
            )
            self._search_provider_label = "Ollama + DuckDuckGo"
            print(
                f"[Ollama Search] Connected ({self.ollama_model} @ {self.ollama_base_url})"
            )
            return True
        except Exception as exc:
            print(f"[Ollama Search] Initialisation failed: {exc}")
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
        Run a search query using the selected provider and return formatted text
        with source links when available.
        """
        if self._llm is None:
            return None
        if self.provider == "ollama":
            return self._run_ollama_search(query=query, context=context)

        return self._run_gemini_search(query=query, context=context)

    def _run_gemini_search(self, query: str, context: str = "") -> Optional[str]:
        """Run grounded Gemini search and append extracted web sources."""
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

    def _run_ollama_search(self, query: str, context: str = "") -> Optional[str]:
        """Retrieve web snippets via DuckDuckGo and synthesize with Ollama."""
        try:
            web_results = _duckduckgo_search(query=query, max_results=5)
            if not web_results:
                print(f"[Ollama Search] No web results for: {context}")
                return None

            evidence_block = "\n\n".join(
                (
                    f"[{idx}] {item['title']}\n"
                    f"URL: {item['url']}\n"
                    f"Snippet: {item['snippet']}"
                )
                for idx, item in enumerate(web_results, start=1)
            )

            prompt = (
                "You are preparing a compliance-intelligence brief for methane emissions. "
                "Use only the web evidence below.\n\n"
                f"Original request:\n{query}\n\n"
                "Instructions:\n"
                "1. Provide a structured answer with specific fields and values.\n"
                "2. If data is unavailable, write 'Not Found'.\n"
                "3. Do not invent facts outside the provided evidence.\n"
                "4. Keep it concise and audit-ready.\n\n"
                f"Web evidence:\n{evidence_block}"
            )
            response = self._llm.invoke(prompt)
            result_text = (
                response.content
                if hasattr(response, "content") and response.content
                else "(No response)"
            )
            result_text += "\n\n**Web Sources Used:**\n" + "\n".join(
                f"- [{item['title']}]({item['url']})" for item in web_results
            )
            return result_text
        except Exception as exc:
            print(f"[Ollama Search] Search failed ({context}): {exc}")
            return None

    @property
    def search_provider_label(self) -> str:
        """Human-readable label for the currently active search backend."""
        return self._search_provider_label


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


def _duckduckgo_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Fetch lightweight web results via DDGS (preferred) or legacy fallback."""
    ddgs_cls = None
    try:
        from ddgs import DDGS as _DDGS  # noqa: PLC0415

        ddgs_cls = _DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS as _DDGS  # noqa: PLC0415

            ddgs_cls = _DDGS
        except ImportError:
            print(
                "[Ollama Search] ddgs not installed. "
                "Run: pip install ddgs"
            )
            return []

    results: list[dict[str, str]] = []
    try:
        with ddgs_cls() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": str(item.get("title") or "Source"),
                        "url": str(item.get("href") or "#"),
                        "snippet": str(item.get("body") or ""),
                    }
                )
    except Exception as exc:
        print(f"[Ollama Search] DDGS query failed: {exc}")

    return results
