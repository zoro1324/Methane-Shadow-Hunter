"""
Autonomous Compliance Audit Reporting Agent.

Uses LangChain + Ollama (local) to generate formal
compliance audit reports for identified methane-emitting facilities.
"""

import json
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass

from src.agent.prompts import SYSTEM_PROMPT, REPORT_TEMPLATE, SEARCH_INTEL_TEMPLATE
from src.agent.tools import facility_lookup, get_emission_data, search_regulations
from src.agent.gemini_service import GeminiSearchService


@dataclass
class AuditReport:
    """A generated compliance audit report."""
    report_id: str
    facility_id: str
    facility_name: str
    operator: str
    emission_rate_kg_hr: float
    report_markdown: str
    risk_level: str
    timestamp: str
    llm_analysis: Optional[str] = None


class ComplianceAuditAgent:
    """
    LLM-based agent that generates compliance audit reports.

    Uses two LLM backends:
      - Ollama (local)  → analysing emission data and drafting report text
      - Gemini (cloud)  → live Google Search for facility owner / compliance intel
                          (activated when emission_rate >= gemini_search_threshold_kg_hr)

    The primary report-drafting LLM is selected via ``llm_provider``:
      - ``"ollama"`` (default) → uses ChatOllama (local, private)
      - ``"gemini"``           → uses ChatGoogleGenerativeAI (cloud, no search tools
                                 bound – search is handled separately by GeminiSearchService)

    Falls back to template-based reports if the chosen LLM is unavailable.
    Gemini search enrichment is silently skipped if no API key is provided.
    """

    def __init__(
        self,
        model: str = "llama3:8b",
        base_url: str = "http://localhost:11434",
        api_key: str = "",  # unused, kept for signature compatibility
        gemini_api_key: str = "",
        gemini_model: str = "gemini-2.0-flash",
        gemini_search_threshold_kg_hr: float = 25.0,
        llm_provider: str = "ollama",
    ):
        self.model = model
        self.base_url = base_url
        self.llm_provider = llm_provider  # "ollama" | "gemini"
        self._llm: Optional[Any] = None
        # Web-search enrichment service for owner/compliance intelligence.
        self._gemini = GeminiSearchService(
            api_key=gemini_api_key,
            model=gemini_model,
            provider=llm_provider,
            ollama_model=model,
            ollama_base_url=base_url,
        )
        self.gemini_search_threshold_kg_hr = gemini_search_threshold_kg_hr

    def _init_llm(self) -> bool:
        """Initialise the chosen LLM backend (Ollama or Gemini) via LangChain."""
        if self._llm is not None:
            return True
        if self.llm_provider == "gemini":
            return self._init_gemini_llm()
        return self._init_ollama_llm()

    def _init_ollama_llm(self) -> bool:
        """Connect to local Ollama via LangChain ChatOllama."""
        try:
            from langchain_ollama import ChatOllama  # noqa: PLC0415

            # Invoke through Any to avoid strict signature drift across
            # langchain-ollama versions while keeping runtime kwargs intact.
            chat_ollama_cls: Any = ChatOllama
            llm = chat_ollama_cls(
                model=self.model,
                base_url=self.base_url,
                temperature=0.3,
            )
            # Quick connectivity test
            llm.invoke("test")
            self._llm = llm
            print(f"[Agent] Connected to Ollama ({self.model} @ {self.base_url})")
            return True
        except Exception as e:
            print(f"[Agent] Ollama not available: {e}")
            print("[Agent] Will use template-based reports instead.")
            self._llm = None
            return False

    def _init_gemini_llm(self) -> bool:
        """Connect to Gemini via LangChain ChatGoogleGenerativeAI (no search tools bound)."""
        if not self._gemini.api_key:
            print("[Agent] LLM_PROVIDER=gemini but GEMINI_API_KEY is not set.")
            print("[Agent] Will use template-based reports instead.")
            return False
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI  # noqa: PLC0415
            # NOTE: No search tools bound here – this instance is for report
            # analysis only.  Search grounding is handled by GeminiSearchService.
            self._llm = ChatGoogleGenerativeAI(
                model=self._gemini.model,
                google_api_key=self._gemini.api_key,
                temperature=0.3,
            )
            print(f"[Agent] Connected to Gemini ({self._gemini.model}) as primary LLM.")
            return True
        except ImportError:
            print("[Agent] langchain-google-genai not installed.")
            print("[Agent] Will use template-based reports instead.")
            self._llm = None
            return False
        except Exception as e:
            print(f"[Agent] Gemini LLM init failed: {e}")
            print("[Agent] Will use template-based reports instead.")
            self._llm = None
            return False

    def generate_report(
        self,
        attributed_emission,  # AttributedEmission object
        plume_data=None,      # PlumeObservation object
    ) -> AuditReport:
        """
        Generate a compliance audit report for an attributed emission.
        
        Tries LLM-based generation first, falls back to template.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_id = f"MSH-{datetime.now().strftime('%Y%m%d')}-{attributed_emission.facility_id}"

        # Gather context via tools
        facility_info = facility_lookup(
            attributed_emission.facility_lat,
            attributed_emission.facility_lon,
            radius_km=2.0,
        )

        emission_info = get_emission_data(
            plume_id=attributed_emission.plume_id,
            emission_rate=attributed_emission.emission_rate_kg_hr,
            uncertainty=attributed_emission.emission_uncertainty,
            distance_m=attributed_emission.pinpoint_accuracy_m,
            facility_name=attributed_emission.facility_name,
        )

        reg_info = search_regulations(country="India", sector="oil_gas")

        # --- Web-search enrichment (confirmed suspicious facility) ---
        search_owner_details = None
        search_compliance_history = None
        rate_for_threshold = attributed_emission.emission_rate_kg_hr
        if rate_for_threshold >= self.gemini_search_threshold_kg_hr:
            print(
                f"[Search] Emission {rate_for_threshold:.1f} kg/hr ≥ threshold "
                f"{self.gemini_search_threshold_kg_hr} kg/hr – searching for facility owner..."
            )
            search_owner_details = self._gemini.search_facility_owner(
                facility_name=attributed_emission.facility_name,
                operator=attributed_emission.operator,
                state=attributed_emission.state,
                lat=attributed_emission.facility_lat,
                lon=attributed_emission.facility_lon,
                facility_type=attributed_emission.facility_type,
            )
            search_compliance_history = self._gemini.search_industry_compliance(
                operator=attributed_emission.operator,
                state=attributed_emission.state,
            )

        # Classify risk
        rate = attributed_emission.emission_rate_kg_hr
        if rate > 500:
            risk_level = "🔴 CRITICAL"
            emission_class = "SUPER-EMITTER"
        elif rate > 100:
            risk_level = "🟠 HIGH"
            emission_class = "Major Emitter"
        elif rate > 25:
            risk_level = "🟡 MEDIUM"
            emission_class = "Significant Emitter"
        else:
            risk_level = "🟢 LOW"
            emission_class = "Minor Emitter"

        # Annual estimates
        annual_tonnes = round(rate * 8760 / 1000, 1)
        co2e_tonnes = round(annual_tonnes * 80, 0)

        # Try LLM-based analysis (Ollama)
        llm_analysis = None
        if self._init_llm():
            llm_analysis = self._get_llm_analysis(
                facility_info, emission_info, reg_info, attributed_emission
            )

        # Build the report
        report_md = self._build_report(
            report_id=report_id,
            timestamp=timestamp,
            attributed=attributed_emission,
            emission_class=emission_class,
            risk_level=risk_level,
            annual_tonnes=annual_tonnes,
            co2e_tonnes=co2e_tonnes,
            reg_info=reg_info,
            llm_analysis=llm_analysis,
            plume_data=plume_data,
            search_owner_details=search_owner_details,
            search_compliance_history=search_compliance_history,
        )

        return AuditReport(
            report_id=report_id,
            facility_id=attributed_emission.facility_id,
            facility_name=attributed_emission.facility_name,
            operator=attributed_emission.operator,
            emission_rate_kg_hr=rate,
            report_markdown=report_md,
            risk_level=risk_level,
            timestamp=timestamp,
            llm_analysis=llm_analysis,
        )

    def _get_llm_analysis(self, facility_info, emission_info, reg_info, attributed) -> Optional[str]:
        """Get LLM-powered analysis."""
        if self._llm is None:
            return None
        try:
            prompt = f"""{SYSTEM_PROMPT}

Based on the following satellite detection data, provide:
1. A 2-3 sentence executive summary of the findings
2. A regulatory compliance assessment (2-3 sentences)
3. Three specific recommended actions
4. A monitoring plan

=== FACILITY DATA ===
{facility_info}

=== EMISSION DATA ===
{emission_info}

=== REGULATORY CONTEXT ===
{reg_info}

Provide your analysis in a structured format."""

            response = self._llm.invoke(prompt)
            # Both ChatOllama and ChatGoogleGenerativeAI return AIMessage
            content = response.content if hasattr(response, "content") else str(response)
            return str(content) if not isinstance(content, str) else content
        except Exception as e:
            print(f"[Agent] LLM analysis failed: {e}")
            return None

    def _build_report(
        self,
        report_id, timestamp, attributed, emission_class, risk_level,
        annual_tonnes, co2e_tonnes, reg_info, llm_analysis, plume_data,
        search_owner_details=None, search_compliance_history=None,
    ) -> str:
        """Build the final Markdown report."""

        # Executive summary
        if llm_analysis:
            # Extract summary from LLM output (first paragraph)
            exec_summary = llm_analysis.split("\n\n")[0] if llm_analysis else ""
        else:
            exec_summary = (
                f"Satellite monitoring has detected methane emissions of "
                f"**{attributed.emission_rate_kg_hr:.1f} kg/hr** originating from "
                f"**{attributed.facility_name}** operated by **{attributed.operator}** "
                f"in {attributed.state}, India. "
                f"The emission has been classified as **{emission_class}** "
                f"with a pinpoint accuracy of {attributed.pinpoint_accuracy_m:.0f} meters."
            )

        # Regulatory assessment
        if llm_analysis and "regulatory" in llm_analysis.lower():
            # Try to extract regulatory section from LLM
            reg_assessment = "See LLM analysis below for detailed regulatory assessment."
        else:
            reg_assessment = (
                "Under the **Environment Protection Act, 1986** and the "
                "**Air (Prevention and Control of Pollution) Act, 1981**, "
                f"this facility is required to maintain emissions within prescribed limits. "
                f"An emission rate of {attributed.emission_rate_kg_hr:.1f} kg/hr "
                f"({'exceeds' if attributed.emission_rate_kg_hr > 100 else 'may require review under'} "
                f"current regulatory thresholds for fugitive methane emissions."
            )

        # Risk details
        risk_details = (
            f"- **Environmental Impact:** {annual_tonnes} tonnes CH4/year "
            f"= {co2e_tonnes:.0f} tonnes CO2e/year\n"
            f"- **Detection Confidence:** {attributed.confidence}\n"
            f"- **Attribution Distance:** {attributed.pinpoint_accuracy_m:.0f}m from facility"
        )

        # Recommendations
        if llm_analysis and "recommend" in llm_analysis.lower():
            recommendations = llm_analysis
        else:
            recommendations = (
                "1. **Immediate Leak Inspection:** Deploy ground-based LDAR (Leak Detection "
                "and Repair) team to the identified facility within 48 hours\n"
                "2. **Valve/Fitting Check:** Inspect all high-pressure valves, flanges, and "
                "connectors within 500m of the plume origin point\n"
                "3. **Operator Notification:** Issue formal notice to the facility operator "
                f"({attributed.operator}) requiring emission source identification and repair plan\n"
                "4. **Component Replacement:** Replace identified leaking components "
                "(estimated cost recovery within 3 months from captured gas value)\n"
                "5. **CPCB Notification:** Report to Central Pollution Control Board if emission "
                "exceeds prescribed limits"
            )

        # Monitoring plan
        monitoring = (
            f"| Schedule | Action |\n"
            f"|----------|--------|\n"
            f"| Week 1 | Ground-based LDAR verification |\n"
            f"| Week 2 | Repair implementation |\n"
            f"| Week 4 | Follow-up satellite pass (Sentinel-5P) |\n"
            f"| Month 2 | High-res verification tasking (GHGSat/CarbonMapper) |\n"
            f"| Month 6 | Compliance verification report |\n"
        )

        # Detection source
        detection_source = "Sentinel-5P TROPOMI + CarbonMapper"
        acquisition_date = "2024-06-15"
        if plume_data:
            detection_source = f"Sentinel-5P + {plume_data.source}"
            acquisition_date = plume_data.acquisition_date

        # --- Build search intel section ---
        if search_owner_details or search_compliance_history:
            gemini_intel_section = SEARCH_INTEL_TEMPLATE.format(
                search_provider=self._gemini.search_provider_label,
                owner_details=search_owner_details or "*Search did not return results.*",
                compliance_history=search_compliance_history or "*Search did not return results.*",
            )
        else:
            gemini_intel_section = ""

        report = REPORT_TEMPLATE.format(
            report_id=report_id,
            timestamp=timestamp,
            classification=emission_class,
            executive_summary=exec_summary,
            facility_name=attributed.facility_name,
            facility_id=attributed.facility_id,
            facility_type=attributed.facility_type,
            operator=attributed.operator,
            state=attributed.state,
            latitude=f"{attributed.facility_lat:.4f}",
            longitude=f"{attributed.facility_lon:.4f}",
            status="Active",
            emission_rate_kg_hr=f"{attributed.emission_rate_kg_hr:.2f}",
            uncertainty=f"{attributed.emission_uncertainty:.2f}",
            annual_tonnes=annual_tonnes,
            co2e_tonnes=co2e_tonnes,
            emission_class=emission_class,
            detection_source=detection_source,
            plume_id=attributed.plume_id,
            pinpoint_m=f"{attributed.pinpoint_accuracy_m:.0f}",
            confidence=attributed.confidence,
            acquisition_date=acquisition_date,
            regulatory_assessment=reg_assessment,
            risk_level=risk_level,
            risk_details=risk_details,
            recommendations=recommendations,
            monitoring_plan=monitoring,
            gemini_intel_section=gemini_intel_section,
        )

        # Append full LLM analysis if available
        provider_label = (
            f"Gemini/{self._gemini.model}"
            if self.llm_provider == "gemini"
            else f"Ollama/{self.model}"
        )
        if llm_analysis:
            report += f"\n\n---\n## 🤖 Detailed LLM Analysis *({provider_label})*\n\n{llm_analysis}\n"

        return report

    def generate_batch_reports(
        self, attributed_emissions: list, plume_data_map: Optional[dict] = None
    ) -> list[AuditReport]:
        """Generate reports for multiple emissions."""
        reports = []
        for attr in attributed_emissions:
            plume = plume_data_map.get(attr.plume_id) if plume_data_map else None
            report = self.generate_report(attr, plume)
            reports.append(report)
            print(f"[Agent] Generated report: {report.report_id} | {report.risk_level}")
        return reports
