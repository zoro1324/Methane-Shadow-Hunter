"""
Autonomous Compliance Audit Reporting Agent.

Uses LangChain + Featherless AI (OpenAI-compatible) to generate formal
compliance audit reports for identified methane-emitting facilities.
"""

import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from src.agent.prompts import SYSTEM_PROMPT, REPORT_TEMPLATE
from src.agent.tools import facility_lookup, get_emission_data, search_regulations


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

    Uses LangChain with Featherless AI (OpenAI-compatible API) for analysis
    and report generation.  Falls back to template-based reports if the LLM
    is unavailable.
    """

    def __init__(
        self,
        model: str = "meta-llama/Llama-3.1-8B-Instruct",
        api_key: str = "",
        base_url: str = "https://api.featherless.ai/v1",
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._llm = None

    def _init_llm(self):
        """Initialize the Featherless AI LLM via LangChain (OpenAI-compatible)."""
        if self._llm is not None:
            return True

        if not self.api_key:
            print("[Agent] FEATHERLESS_API_KEY not set — skipping LLM init.")
            print("[Agent] Will use template-based reports instead.")
            return False

        try:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=self.model,
                openai_api_key=self.api_key,
                openai_api_base=self.base_url,
                temperature=0.3,
            )
            # Quick connectivity test
            self._llm.invoke("test")
            print(f"[Agent] Connected to Featherless AI ({self.model})")
            return True
        except Exception as e:
            print(f"[Agent] Featherless AI not available: {e}")
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

        # Try LLM-based analysis
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
            # ChatOpenAI returns an AIMessage; extract text content
            return response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            print(f"[Agent] LLM analysis failed: {e}")
            return None

    def _build_report(
        self,
        report_id, timestamp, attributed, emission_class, risk_level,
        annual_tonnes, co2e_tonnes, reg_info, llm_analysis, plume_data,
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
        )

        # Append full LLM analysis if available
        if llm_analysis:
            report += f"\n\n---\n## 🤖 Detailed LLM Analysis\n\n{llm_analysis}\n"

        return report

    def generate_batch_reports(
        self, attributed_emissions: list, plume_data_map: dict = None
    ) -> list[AuditReport]:
        """Generate reports for multiple emissions."""
        reports = []
        for attr in attributed_emissions:
            plume = plume_data_map.get(attr.plume_id) if plume_data_map else None
            report = self.generate_report(attr, plume)
            reports.append(report)
            print(f"[Agent] Generated report: {report.report_id} | {report.risk_level}")
        return reports
